# Codex Dispatch Contract

The main agent is the Orchestrator. It may create a subagent only when the active Codex surface exposes a subagent mechanism that accepts both an explicit `model` and `reasoning_effort` (or equivalent effort parameter).

For each slice, the Orchestrator sends: task ID, role, objective, scope, allowed artefacts, lock/reservation, risk, approved model, approved effort, timeout, retry limit, tool constraints, sensitive-data redaction requirement, required handoff, and exit condition.

Select a pair by ascending model rank and effort rank. A selected pair must allow the role and risk and meet task constraints. Escalation requires a ledger reason explaining why every lower permitted pair is insufficient. Never choose a model or effort merely because it is convenient, default, or budget remains.

If the surface cannot express, verify, or report the pair, set the slice to `waiting_user`. Do not use the main agent as a substitute specialist.
