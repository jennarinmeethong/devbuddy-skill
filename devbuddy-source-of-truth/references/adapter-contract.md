# Adapter Contract

## Common to all adapters

Adapters preserve policies, role authority, structured handoffs, settings precedence, memory model, approvals, safety controls, manual requirements, and checklist status. They may translate only platform mechanics: invocation, subagent dispatch, tool names, status transport, and file layout.

The Claude adapter carries the canonical effort tier in the selected `devbuddy-<role>-<effort>` agent definition and carries the approved model through the Agent tool's per-call `model` parameter. The Codex adapter keeps one role profile per canonical role and carries both approved values through the platform subagent call as `model` and `reasoning_effort`. Neither adapter may silently substitute a generic subagent or an unapproved model/effort pair.

Each adapter must map per-dispatch model and effort selection to the platform capability and enforce the common `minimum_sufficient` policy. If the platform cannot represent or verify either selection, it must block dispatch and keep its checklist item incomplete.

## Invocation contract

The adapter command is an Orchestrator entrypoint. A normal invocation passes the complete user task directly to the Orchestrator; the user does not need to choose a role or `owner` first. The Orchestrator assesses the task, selects the required role graph, and dispatches specialists.

- Claude: `/devbuddy <task>`, `/devbuddy loop <task>`, and `/devbuddy analyze <project>`.
- Codex: `$devbuddy <task>`, `$devbuddy loop <task>`, and `$devbuddy analyze <project>`.
- Explicit `<role>` and `owner` forms remain advanced overrides for users who intentionally constrain routing; they are not required for normal use.
- The Orchestrator must not perform specialist work itself. A normal bare invocation that needs specialist work must dispatch a real specialist or stop with a clear `waiting_user` blocker.

`analyze` is a read-only Orchestrator workflow. It may use the bounded bootstrap inventory but writes reviewable observations only to the active task area; the owner promotes approved observations to canonical memory.

## Targets

- Claude adapter target: Claude Code Skill.
- Codex adapter target: current Codex Skill structure with `SKILL.md` and `agents/openai.yaml`.

## Checklist synchronisation

For every common change, assign a stable change ID in the source template and synchronise the item to both adapter checklist files. Preserve their status and remarks. `done` requires evidence; `not_started` and `in_progress` require a remark with reason, owner, and next action.

## Conformance

Compare adapter checklists with the source template, validate adapter settings mapping, run scenario checks, and update both manuals. Do not call an adapter fully supported while any required item is incomplete without an explicit user exception.
