# Role Routing

| Input | Canonical role or mode |
|---|---|
| `ba` | `ba-pm` |
| `sa` | `architect` |
| `dev` | `developer` |
| `tester` | `qa` |
| `operations` | `devops-sre` |
| `data` | `dba-data` |
| `analyze` | read-only orchestration triage; dispatch a specialist only when needed |
| `docs` | `developer` documentation scope; route `reviewer` when risk requires it |

`owner` builds and controls a multi-role graph. A direct canonical role creates a single-role graph, but all policy, settings, model/effort, lock, slice record, and closure gates still apply.

## Subagent names

Each canonical role has three installed subagents, one per effort tier:

```text
devbuddy-<role>-low
devbuddy-<role>-medium
devbuddy-<role>-high
```

for `ba-pm`, `ux-ui`, `architect`, `developer`, `qa`, `security`, `devops-sre`, `dba-data`, and `reviewer` — 27 definitions.

`analyze` is an Orchestrator mode, not a role, and has no subagent. `docs` resolves to a `developer` subagent.

Effort tiers are not interchangeable with roles: pick the role from the work, then pick the lowest tier whose `allowed_roles` and `allowed_risks` cover the slice. Some roles have no `low` tier available at a given risk level; consult the project's `approved_effort_levels` rather than assuming the tier exists for that combination.
