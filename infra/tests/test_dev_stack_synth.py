"""
Minimal smoke test: the dev stack should synthesize without error and
should contain the resources every later phase depends on. This is not
a substitute for the Phase 8 end-to-end smoke test in the DevOps brief
(S3 write -> Aurora -> EventBridge -> Lambda -> Bedrock KB) — that one
runs against real deployed infrastructure, not synthesized templates.
"""

import aws_cdk as cdk
from aws_cdk.assertions import Template

from mino_infra.mino_dev_stack import MinoDevStack


def _synth_template() -> Template:
    app = cdk.App()
    stack = MinoDevStack(
        app,
        "mino-dev-stack-test",
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    return Template.from_stack(stack)


def test_stack_synthesizes():
    _synth_template()


def test_has_vpc_with_no_nat_gateway():
    template = _synth_template()
    template.resource_count_is("AWS::EC2::VPC", 1)
    template.resource_count_is("AWS::EC2::NatGateway", 0)


def test_has_three_s3_buckets():
    template = _synth_template()
    template.resource_count_is("AWS::S3::Bucket", 3)


def test_has_aurora_serverless_cluster():
    template = _synth_template()
    template.has_resource_properties(
        "AWS::RDS::DBCluster",
        {"EngineMode": cdk.assertions.Match.absent()},  # Serverless v2 uses provisioned engine mode
    )


def test_has_event_bus_and_lambdas():
    template = _synth_template()
    template.resource_count_is("AWS::Events::EventBus", 2)
    # 9 pipeline functions + 2 CDK-generated helpers (log-retention and
    # S3 auto-delete-objects custom resources) = 11.
    lambda_resources = template.find_resources("AWS::Lambda::Function")
    pipeline_fns = [
        r for r in lambda_resources.values()
        if r.get("Properties", {}).get("FunctionName", "").startswith("mino-fn-")
    ]
    assert len(pipeline_fns) == 9
