# DevBuddy Codex adapter

DevBuddy is an explicitly invoked Codex skill for policy-driven software delivery. The Orchestrator selects a role, an approved model, and an approved `reasoning_effort` independently for each specialist slice.

## Install

New installations use the DevBuddy Plugin/profile workflow. The standalone
copier is retained only as a 1.x compatibility shim; inspect its migration
report first:

```text
python3 scripts/install_codex_adapter.py --migration-report
```

The historical apply command retains the legacy skill during the compatibility window:

```text
python3 scripts/install_codex_adapter.py --apply
```

Resolve `profiles/codex.yaml --platform codex` with the DevBuddy Plugin manager for new work. The shim's default target is `~/.codex/skills/devbuddy`; it never removes that legacy skill, and refuses to overwrite files that are not recognised as DevBuddy artefacts.

## Configure and validate

Select a `.devbuddy` workspace and register one or more repositories in `settings.yaml` with stable project IDs, plus user-approved model and effort allowlists, concurrency, timeout, and retry values. Shared canonical knowledge lives in `knowledge-base/`; task ledgers and runtime tools live in `tasks/` and `tools/`. Model IDs are intentionally not hardcoded in this adapter.

```text
python3 scripts/init_project_memory.py --project-root <project-root> --dry-run
python3 scripts/init_project_memory.py --devbuddy-root <workspace>/.devbuddy --project fe=../frontend --project be=../backend --dry-run
python3 <workspace>/.devbuddy/tools/bootstrap_knowledge.py --devbuddy-root <workspace>/.devbuddy --project-id fe --dry-run
python3 <workspace>/.devbuddy/tools/validate_project_settings.py <workspace>/.devbuddy/settings.yaml
python3 <workspace>/.devbuddy/tools/validate_knowledge.py --devbuddy-root <workspace>/.devbuddy
python3 scripts/validate_skill_metadata.py .
python3 scripts/check_adapter_conformance.py
python3 -m unittest discover tests -v
```

Run bootstrap in dry-run mode for one registered project ID, then use `--apply` only after review. It appends a labelled observation section without replacing another project's observations and never invents typed canonical entities. Use `--migrate-layout --dry-run` before explicitly moving a legacy layout into `knowledge-base/`.

Invoke with `$devbuddy <task>`. The Orchestrator selects the role graph; `owner` and explicit role forms are advanced routing overrides. If the Codex surface cannot express or verify both `model` and `reasoning_effort`, the task becomes `waiting_user`; the Orchestrator does not substitute itself for the specialist.
