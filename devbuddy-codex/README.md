# DevBuddy Codex adapter

DevBuddy is an explicitly invoked Codex skill for policy-driven software delivery. The Orchestrator selects a role, an approved model, and an approved `reasoning_effort` independently for each specialist slice.

## Install

Preview the exact files first:

```text
python3 scripts/install_codex_adapter.py
```

Apply the installation only after reviewing the dry run:

```text
python3 scripts/install_codex_adapter.py --apply
```

The default target is `~/.codex/skills/devbuddy`. Use `--codex-root <path>` for another approved Codex configuration root. The installer is non-destructive by default and refuses to overwrite files that are not recognised as DevBuddy artefacts.

## Configure and validate

Create `<project-root>/.devbuddy/settings.yaml` with user-approved model and effort allowlists, concurrency, timeout, and retry values. The same `.devbuddy/` root contains `KnowledgeBase.md`, the other core files, typed knowledge, and task ledgers. Model IDs are intentionally not hardcoded in this adapter.

```text
python3 scripts/init_project_memory.py --project-root <project-root> --dry-run
python3 scripts/validate_project_settings.py <project-root>/.devbuddy/settings.yaml
python3 scripts/validate_knowledge.py --project-root <project-root>
python3 scripts/validate_skill_metadata.py .
python3 scripts/check_adapter_conformance.py
python3 -m unittest discover tests -v
```

For an approved external memory root, use `--root <approved-external-memory-root>` with both the initializer and `validate_knowledge.py`; the path is used directly and is never wrapped in another `.devbuddy/` directory.

Invoke with `$devbuddy <task>`. The Orchestrator selects the role graph; `owner` and explicit role forms are advanced routing overrides. If the Codex surface cannot express or verify both `model` and `reasoning_effort`, the task becomes `waiting_user`; the Orchestrator does not substitute itself for the specialist.
