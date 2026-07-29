# DevBuddy Skill

DevBuddy is a policy-driven software-delivery orchestrator with platform adapters for Claude Code and Codex.

## Repository layout

- `devbuddy-source-of-truth/` — common policies, roles, memory model, contracts, and checklist template
- `devbuddy-claude/` — Claude Code `/devbuddy` adapter with 27 role/effort agents
- `devbuddy-codex/` — Codex `$devbuddy` adapter with one role profile per role and per-call model/effort selection

## Validate

Run from the repository root:

```text
python3 devbuddy-source-of-truth/scripts/validate_settings.py devbuddy-source-of-truth/settings.yaml
python3 devbuddy-source-of-truth/scripts/check_adapter_checklists.py --template devbuddy-source-of-truth/templates/adapter-implementation-checklist.md devbuddy-claude/adapter-implementation-checklist.md devbuddy-codex/adapter-implementation-checklist.md
python3 devbuddy-source-of-truth/scripts/check_semantic_conformance.py
python3 -m unittest discover devbuddy-source-of-truth/tests -v
python3 -m unittest discover devbuddy-claude/tests -v
python3 -m unittest discover devbuddy-codex/tests -v
```

## Install

Claude uses a dry-run-first installer:

```text
python3 devbuddy-claude/scripts/install_claude_adapter.py
python3 devbuddy-claude/scripts/install_claude_adapter.py --apply
```

Codex uses the equivalent installer:

```text
python3 devbuddy-codex/scripts/install_codex_adapter.py
python3 devbuddy-codex/scripts/install_codex_adapter.py --apply
```

Both installers accept a platform configuration root and refuse non-DevBuddy file collisions. Create project settings under `<project-root>/.devbuddy/settings.yaml` before dispatch. The memory initializer keeps `KnowledgeBase.md`, the other core files, typed knowledge, and task ledgers together under `<project-root>/.devbuddy/`; an approved external `--root` is used directly without nesting.

Prepare a reviewable knowledge inventory from an existing repository with the read-only-by-default bootstrap:

```text
python3 devbuddy-source-of-truth/scripts/bootstrap_knowledge.py --project-root <project-root> --dry-run
python3 devbuddy-source-of-truth/scripts/bootstrap_knowledge.py --project-root <project-root> --apply
```

Bootstrap writes only `Context.md` and `KnowledgeBase.md` after explicit `--apply`, never overwrites non-empty existing files, and does not invent typed canonical entities or business policy. For an external memory root, add `--root <approved-external-memory-root> --source-root <project-root>`.
