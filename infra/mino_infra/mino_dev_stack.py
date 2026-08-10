"""
Mino dev stack — us-east-1, no DR, Serverless Aurora.

Translated from the original TypeScript CDK reference in
mino-devops-tasks-2026-07-28.docx (Phase 10). Same resources,
same naming conventions, same locked architecture decisions —
just Python instead of TypeScript, per the language-fit decision
made 2026-08-10 (agents/Lambdas are already Python 3.12; only the
API layer is Node/TS, so infra-in-Python aligns with more of the
codebase, not less).

This is a starting point, not production-ready code. Review account
IDs, domain names, and capacity settings before deploying. Never
commit AWS account IDs or secrets to Git.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_cognito as cognito,
    aws_secretsmanager as secretsmanager,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_logs as logs,
    aws_sqs as sqs,
)
from constructs import Construct


class MinoDevStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ─────────────────────────────────────────────────────────
        # 1. VPC — private + public subnets, VPC endpoints (no NAT GW)
        # ─────────────────────────────────────────────────────────
        vpc = ec2.Vpc(
            self,
            "MinoVpc",
            vpc_name="mino-vpc-dev",
            max_azs=2,
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            # No NAT Gateway in dev — use VPC Endpoints instead
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
            ],
        )

        # VPC Endpoints — Lambda reaches AWS services without NAT Gateway
        vpc.add_gateway_endpoint(
            "S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3
        )
        vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True,
        )
        vpc.add_interface_endpoint(
            "BedrockEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
            private_dns_enabled=True,
        )
        vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            private_dns_enabled=True,
        )

        # Security Groups
        lambda_sg = ec2.SecurityGroup(
            self,
            "LambdaSg",
            vpc=vpc,
            security_group_name="mino-sg-lambda-dev",
            description="Lambda functions",
            allow_all_outbound=True,
        )
        aurora_sg = ec2.SecurityGroup(
            self,
            "AuroraSg",
            vpc=vpc,
            security_group_name="mino-sg-aurora-dev",
            description="Aurora PostgreSQL",
            allow_all_outbound=False,
        )
        aurora_sg.add_ingress_rule(lambda_sg, ec2.Port.tcp(5432), "Lambda access")

        # ─────────────────────────────────────────────────────────
        # 2. S3 Buckets
        # ─────────────────────────────────────────────────────────
        raw_bucket = s3.Bucket(
            self,
            "RawBucket",
            bucket_name=f"mino-raw-dev-{self.account}",
            versioned=True,
            # No Object Lock in dev (makes cleanup faster)
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Never auto-delete
        )
        kb_bucket = s3.Bucket(
            self,
            "KbBucket",
            bucket_name=f"mino-kb-dev-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
        )
        s3.Bucket(
            self,
            "ImportsBucket",
            bucket_name=f"mino-imports-dev-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # Auto-delete imports after 30 days
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(30))],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ─────────────────────────────────────────────────────────
        # 3. Aurora PostgreSQL Serverless v2 (scales to near-zero)
        # ─────────────────────────────────────────────────────────
        db_secret = rds.DatabaseSecret(
            self,
            "AuroraSecret",
            secret_name="mino/dev/aurora_master_password",
            username="mino_master",
        )
        aurora = rds.DatabaseCluster(
            self,
            "AuroraCluster",
            cluster_identifier="mino-dev-aurora",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_15_4
            ),
            # Serverless v2 — scales to near-zero when idle
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=4,
            writer=rds.ClusterInstance.serverless_v2("writer"),
            # No reader in dev — saves cost
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[aurora_sg],
            credentials=rds.Credentials.from_secret(db_secret),
            default_database_name="mino",
            backup=rds.BackupProps(retention=Duration.days(7)),
            removal_policy=RemovalPolicy.SNAPSHOT,  # Snapshot on destroy
            deletion_protection=False,  # Allow destroy in dev
        )

        # ─────────────────────────────────────────────────────────
        # 4. Cognito User Pool
        # ─────────────────────────────────────────────────────────
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name="mino-users-dev",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
        )
        user_pool_client = user_pool.add_client(
            "ApiClient",
            user_pool_client_name="mino-api-client-dev",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            access_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
        )

        # ─────────────────────────────────────────────────────────
        # 5. EventBridge Buses
        # ─────────────────────────────────────────────────────────
        event_bus = events.EventBus(self, "MinoEvents", event_bus_name="mino-events-dev")
        events.EventBus(self, "MinoTelemetry", event_bus_name="mino-telemetry-dev")

        # ─────────────────────────────────────────────────────────
        # 6. Secrets Manager + Parameter Store
        # ─────────────────────────────────────────────────────────
        signing_key = secretsmanager.Secret(
            self,
            "SigningKey",
            secret_name="mino/dev/tenant_signing_key",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=64, exclude_punctuation=True
            ),
        )

        params = {
            "/mino/config/bedrock_model_haiku": "anthropic.claude-3-haiku-20240307-v1:0",
            "/mino/config/bedrock_model_sonnet": "anthropic.claude-sonnet-4-20250514-v1:0",
            "/mino/config/max_transcript_mb": "50",
            "/mino/config/default_token_budget": "1000000",
            "/mino/config/summary_word_count": "250",
            "/mino/config/session_idle_timeout_min": "30",
        }
        for name, value in params.items():
            ssm.StringParameter(
                self,
                name.replace("/", "_"),
                parameter_name=name,
                string_value=value,
            )

        # ─────────────────────────────────────────────────────────
        # 7. Lambda shared config + Dead Letter Queues
        # ─────────────────────────────────────────────────────────
        common_env = {
            "AURORA_SECRET_ARN": db_secret.secret_arn,
            "RAW_BUCKET": raw_bucket.bucket_name,
            "KB_BUCKET": kb_bucket.bucket_name,
            "EVENT_BUS_NAME": event_bus.event_bus_name,
            "ENVIRONMENT": "dev",
        }

        def make_lambda(
            construct_id: str,
            handler: str,
            description: str,
            extra_env: dict | None = None,
        ) -> _lambda.Function:
            """Create a Lambda + DLQ pair with the shared grants every
            pipeline function needs (S3 rw, Aurora secret read, signing
            key read, EventBridge put, Bedrock invoke)."""
            dlq = sqs.Queue(
                self,
                f"{construct_id}Dlq",
                queue_name=f"mino-{handler}-dlq-dev",
                retention_period=Duration.days(14),
            )
            fn = _lambda.Function(
                self,
                construct_id,
                function_name=f"mino-{handler}-dev",
                runtime=_lambda.Runtime.PYTHON_3_12,
                code=_lambda.Code.from_asset(f"../lambdas/{handler}"),
                handler="index.handler",
                timeout=Duration.seconds(300),
                memory_size=512,
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                security_groups=[lambda_sg],
                environment={**common_env, **(extra_env or {})},
                dead_letter_queue=dlq,
                retry_attempts=2,
                log_retention=logs.RetentionDays.ONE_WEEK,
                description=description,
            )
            raw_bucket.grant_read_write(fn)
            kb_bucket.grant_read_write(fn)
            db_secret.grant_read(fn)
            signing_key.grant_read(fn)
            event_bus.grant_put_events_to(fn)
            fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["bedrock:InvokeModel", "bedrock:Retrieve"],
                    resources=["*"],
                )
            )
            return fn

        # ─────────────────────────────────────────────────────────
        # 8. Lambda Functions
        # ─────────────────────────────────────────────────────────
        fn_summarize = make_lambda(
            "FnSummarize", "fn-summarize",
            "Generate 250-word summary, index in Bedrock KB",
        )
        fn_extract_ai = make_lambda(
            "FnExtractAi", "fn-extract-ai",
            "Write-time AI extraction: sentiment, next_step, BANT signals",
        )
        fn_bant_extract = make_lambda(
            "FnBantExtract", "fn-bant-extract",
            "Deep BANT extraction from transcripts",
        )
        fn_finops_meter = make_lambda(
            "FnFinopsMeter", "fn-finops-meter",
            "Increment tenant token usage, enforce budget hard stop",
        )
        fn_notify = make_lambda(
            "FnNotify", "fn-notify",
            "Route notifications to Slack/in-app/email",
        )
        make_lambda(
            "FnRuleEvaluator", "fn-rule-evaluator",
            "Evaluate JSON rules against entities",
        )
        make_lambda(
            "FnPartitionManager", "fn-partition-manager",
            "Create next month Aurora partition for interactions",
        )
        fn_sequence_scheduler = make_lambda(
            "FnSequenceScheduler", "fn-sequence-scheduler",
            "Execute due sequence enrollment steps",
        )
        make_lambda(
            "FnSesEventProcessor", "fn-ses-event-processor",
            "Process SES open/click/bounce events",
        )

        # ─────────────────────────────────────────────────────────
        # 9. EventBridge Rules — content-based routing
        # ─────────────────────────────────────────────────────────
        events.Rule(
            self,
            "RuleSummarize",
            event_bus=event_bus,
            rule_name="mino-route-summarize-dev",
            event_pattern=events.EventPattern(detail_type=["interaction.created"]),
            targets=[targets.LambdaFunction(fn_summarize)],
        )
        events.Rule(
            self,
            "RuleExtractAi",
            event_bus=event_bus,
            rule_name="mino-route-extract-ai-dev",
            event_pattern=events.EventPattern(detail_type=["interaction.created"]),
            targets=[targets.LambdaFunction(fn_extract_ai)],
        )
        events.Rule(
            self,
            "RuleBantExtract",
            event_bus=event_bus,
            rule_name="mino-route-bant-extract-dev",
            event_pattern=events.EventPattern(
                detail_type=["interaction.created"],
                detail={"payload": {"has_transcript": [True]}},
            ),
            targets=[targets.LambdaFunction(fn_bant_extract)],
        )
        events.Rule(
            self,
            "RuleFinops",
            event_bus=event_bus,
            rule_name="mino-route-finops-dev",
            event_pattern=events.EventPattern(detail_type=["tokens.used"]),
            targets=[targets.LambdaFunction(fn_finops_meter)],
        )
        events.Rule(
            self,
            "RuleNotify",
            event_bus=event_bus,
            rule_name="mino-route-notify-dev",
            event_pattern=events.EventPattern(
                detail_type=[
                    "rule.triggered",
                    "engagement.conversion_proposed",
                    "tenant.token_threshold_reached",
                    "transcript.processing_started",
                    "transcript.processed",
                    "sequence.completed",
                ]
            ),
            targets=[targets.LambdaFunction(fn_notify)],
        )
        events.Rule(
            self,
            "RuleSequenceScheduler",
            rule_name="mino-sequence-scheduler-dev",
            schedule=events.Schedule.rate(Duration.minutes(15)),
            targets=[targets.LambdaFunction(fn_sequence_scheduler)],
        )

        # ─────────────────────────────────────────────────────────
        # 10. Outputs — printed after `cdk deploy`
        # ─────────────────────────────────────────────────────────
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id,
                  description="Cognito User Pool ID")
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id,
                  description="Cognito App Client ID")
        CfnOutput(self, "AuroraEndpoint", value=aurora.cluster_endpoint.hostname,
                  description="Aurora cluster endpoint")
        CfnOutput(self, "RawBucketName", value=raw_bucket.bucket_name,
                  description="S3 raw data bucket")
        CfnOutput(self, "EventBusArn", value=event_bus.event_bus_arn,
                  description="EventBridge bus ARN")
