# Adapter Contract

## Common to all adapters

Adapters preserve policies, role authority, structured handoffs, settings precedence, memory model, approvals, safety controls, manual requirements, and checklist status. They may translate only platform mechanics: invocation, subagent dispatch, tool names, status transport, and file layout.

Each adapter must map per-dispatch model and effort selection to the platform capability and enforce the common `minimum_sufficient` policy. If the platform cannot represent or verify either selection, it must block dispatch and keep its checklist item incomplete.

## Targets

- Claude adapter target: Claude Code Skill.
- Codex adapter target: current Codex Skill structure with `SKILL.md` and `agents/openai.yaml`.

## Checklist synchronisation

For every common change, assign a stable change ID in the source template and synchronise the item to both adapter checklist files. Preserve their status and remarks. `done` requires evidence; `not_started` and `in_progress` require a remark with reason, owner, and next action.

## Conformance

Compare adapter checklists with the source template, validate adapter settings mapping, run scenario checks, and update both manuals. Do not call an adapter fully supported while any required item is incomplete without an explicit user exception.
