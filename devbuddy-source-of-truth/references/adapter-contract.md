# Adapter Contract

## Common to all adapters

Adapters preserve policies, role authority, structured JSON slice records, settings precedence, memory model, approvals, safety controls, manual requirements, and checklist status. They may translate only platform mechanics: invocation, subagent dispatch, tool names, status transport, and file layout.

Where a platform can enforce the explicit-invocation rule itself, the adapter must use that mechanism rather than restate the rule in prose. Every approval gate assumes the user chose to open a delivery task, and a control the host enforces cannot be reasoned around the way an instruction can. The Claude adapter therefore sets `disable-model-invocation: true` in `SKILL.md`; the Codex adapter has no equivalent field and keeps the rule in its skill body.

The Claude adapter carries the canonical effort tier in the selected `devbuddy-<role>-<effort>` agent definition and carries the approved model through the Agent tool's per-call `model` parameter. The Codex adapter keeps one role profile per canonical role and carries both approved values through the platform subagent call as `model` and `reasoning_effort`. Neither adapter may silently substitute a generic subagent or an unapproved model/effort pair.

Each adapter must map per-dispatch model and effort selection to the platform capability and enforce the common `minimum_sufficient` policy. If the platform cannot represent or verify either selection, it must block dispatch and keep its checklist item incomplete.

Each adapter must resolve `tools.is_rtk` from the selected workspace settings before every delivery command or specialist dispatch. The dispatch package carries the resolved value as `rtk_required`. A specialist with `rtk_required: true` uses RTK for all supported delivery shell commands and returns `waiting_user` if `rtk` is unavailable; it must not silently run the direct equivalent. This constraint is inherited by every specialist, regardless of platform.

## Shared workspace settings

One `.devbuddy/settings.yaml` may serve both adapters. Its `orchestration.adapter_profiles` declares the installed profiles; entries in `approved_models` and `approved_effort_levels` may declare `adapters: [claude]`, `adapters: [codex]`, or both. At dispatch, select only entries for the active adapter. No mutable “active adapter” setting exists: the invoking adapter determines the profile. Legacy entries without `adapters` remain universal only when `adapter_profiles` is absent; a profile-aware workspace must tag every entry.

## Settings defaults and upgrades

Every generated project settings file carries `settings_version`, which must match the adapter's shipped defaults. A version mismatch is resolved only through the explicitly requested `init_project_memory.py --upgrade-settings` flow (first with `--dry-run`). It updates `settings_version` and adds missing scalar settings, adapter profiles, models, and effort entries; it never replaces, narrows, or deletes existing workspace values.

The shipped ordered defaults are intentionally only an approval boundary: `claude-haiku-4.5`, `claude-sonnet-5`, `claude-opus-5`, and `claude-fable`; plus `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`. Claude effort defaults are `low`, `medium`, `high`, `extra`, `max`, and `ultracode`; Codex defaults are `light`, `medium`, `high`, `extra-high`, and `ultra`. The Orchestrator still selects the lowest-ranked sufficient pair and obtains a Cost Approval before any chargeable dispatch.

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
