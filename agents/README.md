# agents

Python. The 8 V1 agents, contracted/specced in the tech-design doc but
not yet coded:

- Admin Agent
- Intelligence Agent
- Design Agent
- Channels Agent
- FinOps Agent
- Retrieval Agent
- Proactive Agent
- Migration Agent

Do not start agent code until the End-of-Week-1 smoke test (Phase 8 of
the DevOps brief) passes against deployed dev infrastructure —
specifically steps 9 and 10 (tenant context token validation and
cross-tenant access rejection). Agent code built on an unverified
tenant-isolation boundary wastes days.
