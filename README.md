# mino-platform

Mino — born-in-AI CRM. Monorepo.

```
mino-platform/
├── infra/      AWS CDK (Python) — infrastructure as code
├── api/        Node.js/TypeScript — API layer
├── agents/     Python — the 8 V1 agents (Admin, Intelligence, Design,
│               Channels, FinOps, Retrieval, Proactive, Migration)
├── lambdas/    Python — event-pipeline Lambda functions (fn-summarize,
│               fn-extract-ai, fn-bant-extract, etc.)
└── .github/    CI workflows
```

Primary region: `us-east-1` (N. Virginia) · DR region: `us-west-2` (Oregon)

## Branch strategy

- `main` — production. Merges here deploy to prod.
- `staging` — merges here deploy to staging.
- `develop` — integration branch for day-to-day work.

CDK deploys are automated via GitHub Actions on merge — never deploy
manually from a laptop against staging or prod.

## Prerequisites

- Node.js 20+ (for `aws-cdk` CLI and the `/api` layer)
- Python 3.12 (for `/infra`, `/agents`, `/lambdas`)
- AWS CLI v2, configured (`aws configure`) with a profile that has
  access to the target account
- An AWS account with Bedrock model access requested for: Claude 3
  Haiku, Claude 3.5 Sonnet, Amazon Titan Text Embeddings V2

## Infra quick start

```bash
# Install the CDK CLI globally (one-time)
npm install -g aws-cdk

cd infra
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Bootstrap CDK in us-east-1 (one-time per account/region)
cdk bootstrap aws://ACCOUNT_ID/us-east-1

# Run tests
pytest

# Preview what will be created (dry run)
cdk diff mino-dev-stack

# Deploy the dev stack
cdk deploy mino-dev-stack

# Destroy the dev stack (S3 data retained, Aurora snapshot taken)
cdk destroy mino-dev-stack
```

After deploying, run the End-of-Week-1 smoke test (Phase 8 of the
DevOps task brief) before writing any agent code. Steps 9 and 10
(tenant context token validation, cross-tenant access rejection)
**must pass** — they're the actual security boundary, not a formality.

## Locked architecture decisions

Do not change these without consulting the platform architect. Full
reasoning lives in the tech-design doc; summary:

| Decision | Choice |
|---|---|
| Primary region | us-east-1 |
| DR region | us-west-2 |
| Database | Aurora PostgreSQL 15, schema-per-tenant |
| Write path | S3 first, then Aurora (S3 is source of truth) |
| Event bus | EventBridge (`mino-events`) |
| Vectorization | Summary-first (250-word Haiku), ~95% cost reduction |
| KB isolation | One Bedrock KB per tenant |
| Agent routing | All calls via AgentCore Gateway |
| Secrets | Secrets Manager (credentials), Parameter Store (config) |
| Infra language | Python (CDK) — agents/Lambdas are already Python 3.12 |

## Status

Infra-as-code: dev stack written, not yet deployed (`cdk bootstrap`
has not been run). Agent code: specced, not built. See
`mino-tech-status.md` in project docs for the current snapshot.
