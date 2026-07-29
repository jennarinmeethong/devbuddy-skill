# Claude Dispatch Contract

The main Claude Code session is the Orchestrator. It dispatches specialists with the Agent tool and never performs their work itself.

## Transport

| Selection | Carried by | Source of truth |
|---|---|---|
| Role | `subagent_type: devbuddy-<role>-<effort>` | `references/role-routing.md` |
| Effort level | the selected subagent's `effort` frontmatter field | `agents/devbuddy-<role>-<effort>.md` |
| Model | the Agent tool's `model` parameter, set explicitly on every call | project `approved_models` |

Claude Code fixes effort per agent definition and allows the model to be overridden per call, so the adapter ships one agent per role and effort tier. Selecting the tier *is* selecting the effort level, and the Agent tool's `model` parameter takes precedence over any model in frontmatter. The agent definitions therefore leave `model` unset so minimum-sufficient model selection stays a live per-dispatch decision.

Do not add a model to an agent definition's frontmatter. A pinned model would silently override the Orchestrator's recorded selection and make the ledger entry false.

## Task package

For each slice the Orchestrator passes: resolved absolute `memory_root`, task ID, `task_path`, `read_keys`, `read_paths`, `write_scope`, `handoff_path`, `parent_revision`, role, objective, scope, allowed artefacts, lock/reservation, risk level, approved model, approved effort, timeout, retry limit, tool constraints, sensitive-data redaction requirement, a 12,000-byte maximum handoff, the required handoff shape from `templates/handoff.md`, and the exit condition. Read/write scope is deny-by-default; the specialist receives only the relevant handoff delta and never writes `.devbuddy/`.

Pass a compact delta, not the whole conversation. The specialist reads the role file and the memory entities it names; forwarding unrelated history wastes context that the specialist needs for its actual work.

## Selection rule

Choose the lowest-ranked approved model and the lowest-ranked approved effort level that both permit the role and the risk level and satisfy the task's capability, privacy, latency, and cost constraints. Escalating above the lowest permitted pair requires a ledger reason explaining why every lower pair is insufficient for this specific slice. Convenience, habit, and remaining budget are not reasons.

Record both selections, the sufficiency reason, and any escalation in the task ledger before the dispatch, not after.

## Parallel dispatch

Independent slices are dispatched in a single message with multiple Agent calls so they run concurrently. Acquire every artefact reservation first — two concurrent writers on one canonical artefact is the failure this rule exists to prevent. Respect the project's `max_concurrency`; Claude Code also enforces its own concurrent-subagent limit.

## Blocking conditions

Set the slice to `waiting_user` and do not dispatch when:

- The required `devbuddy-<role>-<effort>` subagent is not installed.
- Project settings lack a valid model allowlist, effort allowlist, `max_concurrency`, `task_timeout_seconds`, or `retry_limit`.
- No approved model/effort pair is sufficient for the slice.
- A cost, privacy, tool, environment, or knowledge-impact approval is missing.
- A required tool is unavailable, an artefact lock conflicts, or a material fact is uncertain.

Never resolve a block by running the work in the Orchestrator, by widening the allowlist, or by using a permission-bypass mode. Report the block to the user in Thai with the exact missing item.

## Verification of the pair

If the environment cannot report which effort level a subagent actually ran at — for example the named agent is missing and Claude falls back to a generic one — treat the selection as unverified, stop the slice, and report it. An unverifiable selection is a blocked dispatch, not a completed one.
