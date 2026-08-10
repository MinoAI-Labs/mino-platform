"""
Mino prod stack — us-east-1, with Aurora Global Database + DR to us-west-2.

NOTE: the source DevOps brief (Phase 10) only fully specifies the dev
stack in code; prod is referenced in app.ts/app.py but not spelled out
line-by-line. Rather than invent detail that wasn't in the brief, this
file is a deliberate placeholder that mirrors MinoDevStack's shape and
flags the known prod-only deltas from the "Reference — Key Architecture
Decisions" table and Phase 3/6 tasks:

  - Aurora Global Database, secondary region us-west-2 (RPO <1s, RTO <1min)
  - Aurora Multi-AZ (writer + reader), not serverless-min-to-zero
  - S3 cross-region replication to us-west-2 equivalents (all 3 buckets)
  - Object Lock (COMPLIANCE mode, 90-day retention) enabled on mino-raw
  - deletion_protection=True, removal_policy=RETAIN throughout
  - One Bedrock KB per tenant (not a single demo KB)
  - Real domain / ACM cert for Cognito custom domain (auth.mino.ai)

Fill these in against the tech-design doc before this stack is ever
deployed — do not run `cdk deploy mino-prod-stack` against this file
as-is.
"""

from aws_cdk import Stack
from constructs import Construct


class MinoProdStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # TODO: build out prod resources here, following MinoDevStack's
        # structure but with the deltas listed above. Left intentionally
        # unimplemented — do not deploy until reviewed against the TDD.
        raise NotImplementedError(
            "MinoProdStack is a scaffold only. See module docstring for "
            "the known dev -> prod deltas before implementing."
        )
