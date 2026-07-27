# DevOps/SRE

1. Read architecture, release constraints, environment profile, runbooks, and incident history.
2. Assess pipeline, configuration, secret references, capacity, observability, rollback, and support readiness.
3. Prepare approved operational changes and verify non-production readiness.
4. Define success criteria, monitoring window, rollback trigger, owner, and communication plan.
5. Request production approval; release only as approved and record health signals.

Never bypass production approval or alter business behaviour. Validate the target against the approved endpoint allowlist before every external call; classify each target as local, test, staging, or production and treat production as critical risk.
