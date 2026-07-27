# Codex Dispatch Contract

The main agent is the Orchestrator. It may create a subagent only when the active Codex surface exposes a subagent mechanism that accepts both an explicit `model` and `reasoning_effort` (or equivalent effort parameter).

## Transport

| Selection | Carried by | Source of truth |
|---|---|---|
| Role | the platform's role/task package | `references/role-routing.md` and the selected `roles/<role>.md` |
| Effort level | the per-call `reasoning_effort` (or equivalent) parameter | project `approved_effort_levels` |
| Model | the per-call `model` parameter | project `approved_models` |

Codex keeps role instructions independent from effort. Do not create a separate role file for each effort tier; select and verify the effort per dispatch. On the current Codex subagent surface (`multi_agent_v1__spawn_agent`), the Orchestrator passes `model=<approved_models.id>` and `reasoning_effort=<approved_effort_levels.id>` to the subagent call. The task package and structured handoff repeat both values so the ledger can reconcile the requested and reported selection.

For each slice, the Orchestrator sends: task ID, role, objective, scope, allowed artefacts, lock/reservation, risk, approved model, approved effort, timeout, retry limit, tool constraints, sensitive-data redaction requirement, required handoff, and exit condition.

## Selection rule

Choose the lowest-ranked approved model and the lowest-ranked approved effort level that both permit the role and risk level and satisfy the slice's capability, privacy, latency, and cost constraints. Select the model and effort independently; they are separate approval dimensions and do not need to have the same rank or identifier.

Escalating above the lowest permitted model or effort requires a ledger reason explaining why every lower permitted option is insufficient for this specific slice. Record both selections, the sufficiency reason, and any escalation in the task ledger before dispatch. Convenience, habit, a platform default, and remaining budget are not reasons.

The selected pair must be explicit in the dispatch and must be verifiable in the returned execution metadata or handoff. A generic subagent fallback, an omitted parameter, or a handoff that does not state `Model / effort used` is unverified and does not satisfy the contract.

If the surface cannot express, verify, or report either selection, set the slice to `waiting_user`. Do not widen the allowlist, substitute a generic subagent, or use the main agent as a specialist.
