# Adapter Implementation Checklist

Target: Codex Skill
Common specification version: `0.1.1`

## Checklist

- [x] `DBY-CORE-001` | `SKILL.md` | Core orchestration, approvals, risk, slicing, batch, and loop policies | Status: `done` | Location: `SKILL.md`, `references/policy.md`, `references/loop.md` | Evidence: bare `$devbuddy <task>` entrypoint routes through the Orchestrator; `scripts/check_adapter_conformance.py` and `bare_entrypoint` scenario
- [x] `DBY-SET-001` | `settings.yaml` | Settings schema, validation, budgets, model, environment, and cost controls | Status: `done` | Location: `settings.yaml`, `schemas/project-settings.schema.json`, `scripts/validate_project_settings.py` | Evidence: valid and missing-budget fixtures
- [x] `DBY-MODEL-002` | `settings.yaml`, `roles/orchestrator.md` | Required per-dispatch approved model and effort-level selection with task-ledger evidence | Status: `done` | Location: `SKILL.md`, `roles/orchestrator.md`, `templates/task-ledger.md` | Evidence: model_effort_independent_selection and unverified_model_effort scenarios
- [x] `DBY-MODEL-003` | `settings.yaml`, `references/policy.md` | Minimum-sufficient model/effort selection and recorded escalation reason | Status: `done` | Location: `references/codex-dispatch.md`, `references/settings.md` | Evidence: ranked allowlist validation, independent selection, and escalation scenarios
- [x] `DBY-ROLE-001` | `roles/` | Orchestrator and IT role workflows with structured handoffs | Status: `done` | Location: `roles/`, `references/role-routing.md`, `templates/handoff.md` | Evidence: role-routing and scenario coverage
- [x] `DBY-KNOW-001` | `references/knowledge-model.md` | Project memory, keys, impact approval, health, and migration controls | Status: `done` | Location: `SKILL.md`, `references/knowledge-model.md`, `templates/knowledge-entity.md`, `references/policy.md`, `scripts/init_project_memory.py`, `scripts/validate_knowledge.py` | Evidence: `--project-root` resolves `<project-root>/.devbuddy/`, `KnowledgeBase.md` stays at that root, external `--root` is direct, and invalid entity keys are rejected by permanent tests
- [x] `DBY-SAFE-001` | `references/policy.md` | Git, tool, cost, secret, endpoint, prompt-injection, and policy-compliance controls | Status: `done` | Location: `SKILL.md`, `references/policy.md` | Evidence: static policy and scenarios
- [x] `DBY-TOOLS-001` | `scripts/`, `tests/` | Python memory initialization, validation, checklist, knowledge, installer, and manual conformance tools | Status: `done` | Location: `scripts/`, `tests/test_project_memory.py` | Evidence: standard-library regression tests cover `.devbuddy`, external roots, validator failures, installer dry-run/apply/conflicts, and metadata validation
- [x] `DBY-MANUAL-001` | `manual/` | Thai/English HTML manual and platform installation pages | Status: `done` | Location: `manual/` and `devbuddy-source-of-truth/manual/*/codex.html` | Evidence: `scripts/validate_manual.py`
