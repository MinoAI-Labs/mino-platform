#!/usr/bin/env python3
import os

import aws_cdk as cdk

from mino_infra.mino_dev_stack import MinoDevStack
from mino_infra.mino_prod_stack import MinoProdStack

app = cdk.App()

# Dev stack — us-east-1, no DR, Serverless Aurora
MinoDevStack(
    app,
    "mino-dev-stack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region="us-east-1",
    ),
    stack_name="mino-dev",
    tags={
        "Project": "mino",
        "Environment": "dev",
        "ManagedBy": "cdk",
    },
)

# Prod stack — us-east-1, with Aurora Global DB + DR to us-west-2
# NOTE: MinoProdStack is currently a scaffold — see mino_prod_stack.py.
# Deploying this app target will raise NotImplementedError until it's
# built out and reviewed against the tech-design doc.
MinoProdStack(
    app,
    "mino-prod-stack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region="us-east-1",
    ),
    stack_name="mino-prod",
    tags={
        "Project": "mino",
        "Environment": "prod",
        "ManagedBy": "cdk",
    },
)

app.synth()
