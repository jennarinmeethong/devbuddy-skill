# Loop Engineering

Enter only after an explicit `loop` invocation or user approval for a loop-shaped task. State the role, bounded scope, maximum attempts from project settings, exit condition, verification method, allowed side effects, and escalation condition before the first iteration.

Each iteration is `observe -> dispatch specialist -> verify evidence -> record -> stop, retry, or escalate`. The Orchestrator owns the outer loop; the specialist owns only its own artefact and authority. A loop cannot expand a role's authority, and only one owner loop may change a canonical artefact at a time.

Prefer external evidence over self-declaration: tests, builds, scans, review findings, deployment signals, migration checks, and user approval. A role reporting its own success is not an exit condition.

Stop for approval, ambiguity, repeated failure, timeout, budget exhaustion, conflicting evidence, a destructive or external action, or a missing prerequisite. Never run an unbounded self-improvement loop, and never retry a destructive or external action without a new explicit user approval.

On Claude Code, `maxTurns` in an agent definition bounds a single specialist run; it is not a substitute for the loop's attempt budget, which the Orchestrator tracks in the ledger across dispatches. Record every attempt, its evidence, and its outcome.
