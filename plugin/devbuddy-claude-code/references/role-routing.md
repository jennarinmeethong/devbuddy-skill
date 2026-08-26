# Role Routing

The Orchestrator chooses the smallest role graph that covers the task. Broad, existing roles remain supported for compatibility; prefer a specialised role when it clarifies ownership or evidence.

| Input | Canonical role or mode |
|---|---|
| `ba`, `requirements`, `analyst` | `requirements-analyst` |
| `pm`, `product` | `ba-pm` |
| `design`, `ui`, `ux` | `ux-ui` |
| `sa`, `architecture` | `architect` |
| `frontend`, `web-ui` | `frontend-engineer` |
| `backend`, `api`, `service` | `backend-engineer` |
| `dev` | `developer` |
| `tester`, `test` | `qa` |
| `code-review` | `code-reviewer` |
| `security-scan`, `vulnerability` | `vulnerability-scanner` |
| `compliance`, `policy`, `privacy` | `compliance-policy` |
| `security-incident` | `security-incident-response` |
| `cicd`, `devops` | `devops-engineer` |
| `cloud`, `iac` | `cloud-infrastructure` |
| `sre`, `reliability`, `incident` | `site-reliability` |
| `etl`, `pipeline` | `data-pipeline` |
| `analytics`, `sql-insight` | `data-analyst` |
| `model-eval`, `ml-eval` | `model-evaluator` |
| `support`, `helpdesk`, `l1` | `helpdesk-support` |
| `knowledge`, `kb`, `documentation` | `knowledge-base` |
| `data`, `database` | `dba-data` |
| `operations` | `devops-sre` |
| `review` | `reviewer` |
| `analyze` | read-only Orchestrator triage; dispatch a specialist only when needed |
| `docs` | `knowledge-base`; route `reviewer` when risk requires it |

`owner` builds and controls a multi-role graph. A direct canonical role creates a single-role graph, but all policy, settings, model/effort, lock, slice record, and closure gates still apply.
