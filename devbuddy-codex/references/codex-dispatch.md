# Codex Dispatch Contract

The main agent is the Orchestrator. It may create a subagent only when the active Codex surface exposes a subagent mechanism that accepts both an explicit `model` and `reasoning_effort` (or equivalent effort parameter).

## Transport

| Selection | Carried by | Source of truth |
|---|---|---|
| Role | the platform's role/task package | `references/role-routing.md` and the selected `roles/<role>.md` |
| Effort level | the per-call `reasoning_effort` (or equivalent) parameter | current `codex` entries in project `approved_effort_levels` |
| Model | the per-call `model` parameter | current `codex` entries in project `approved_models` |

Codex keeps role instructions independent from effort. Do not create a separate role file for each effort tier; select and verify the effort per dispatch. On any supported Codex subagent surface, the Orchestrator passes `model=<approved_models.id>` and `reasoning_effort=<approved_effort_levels.id>` (or the documented equivalent parameter names) to the subagent call. The task package and JSON slice record repeat both values so the ledger can reconcile the requested and reported selection.

In a workspace that defines `adapter_profiles`, select only entries tagged `adapters: [codex]` (or a list containing `codex`). The current invocation supplies that selection; never change shared settings to switch adapters.

For each slice, the Orchestrator sends: resolved absolute `memory_root`, task ID, `task_path`, `read_keys`, `read_paths`, `write_scope`, `record_path`, `parent_revision`, role, objective, scope, allowed artefacts, lock/reservation, risk, approved model, approved effort, timeout, retry limit, tool constraints, resolved `rtk_required` value, sensitive-data redaction requirement, `schemas/slice-record.schema.json`, and exit condition. Slice records have no file-size cap, but `next_slice` names only the references the next slice needs. Read/write scope is deny-by-default; the specialist returns only a JSON record and never writes `.devbuddy/`.

`rtk_required` is mandatory and is the resolved `tools.is_rtk` setting. When it is `true`, the task package instructs the specialist to use RTK's supported equivalent for every delivery shell command. If RTK is unavailable, the specialist returns `waiting_user` before executing a direct equivalent; unsupported commands may run directly. The Orchestrator must not dispatch a package without this field.

## Selection rule

Choose the lowest-ranked approved model and the lowest-ranked approved effort level that both permit the role and risk level and satisfy the slice's capability, privacy, latency, and cost constraints. Select the model and effort independently; they are separate approval dimensions and do not need to have the same rank or identifier.

Escalating above the lowest permitted model or effort requires a ledger reason explaining why every lower permitted option is insufficient for this specific slice. Record both selections, the sufficiency reason, and any escalation in the task ledger before dispatch. Convenience, habit, a platform default, and remaining budget are not reasons.

The selected pair must be explicit in the dispatch and must be verifiable in the returned execution metadata or slice record. A generic subagent fallback, an omitted parameter, or a record without `model` and `effort` is unverified and does not satisfy the contract.

If the surface cannot express, verify, or report either selection, set the slice to `waiting_user`. Do not widen the allowlist, substitute a generic subagent, or use the main agent as a specialist.
