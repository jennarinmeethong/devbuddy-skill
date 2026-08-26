# Adapter Implementation Checklist

Common specification version: `0.4.6`

## Status legend

- `done`: implemented and verified.
- `not_started`: not implemented.
- `in_progress`: partially implemented or blocked.

## Checklist

- [ ] `DBY-CORE-001` | `SKILL.md` | Core orchestration, approvals, risk, slicing, batch, and loop policies | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map common workflow to platform mechanics.
- [ ] `DBY-SKILL-001` | `templates/adapter-skill-core.md.template`, `references/loading-matrix.md` | Generated adapter prompt core, progressive reference loading, and behavioral prompt-contract validation | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: render the shared core, preserve platform mechanics, and validate the prompt contract.
- [ ] `DBY-SET-001` | `settings.yaml` | Settings schema, validation, budgets, model, environment, and cost controls | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map settings to platform configuration.
- [ ] `DBY-MODEL-002` | `settings.yaml`, `roles/orchestrator.md` | Required per-dispatch approved model and effort-level selection with task-ledger evidence | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map and verify model/effort selection in platform dispatch.
- [ ] `DBY-MODEL-003` | `settings.yaml`, `references/policies.md` | Minimum-sufficient model/effort selection and recorded escalation reason | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: enforce minimum-sufficient selection and escalation evidence.
- [ ] `DBY-SET-002` | `settings.yaml`, `references/settings.md` | Shared Claude/Codex workspace profiles selected automatically from the invoking adapter | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: select only the invoking adapter's tagged allowlist entries without editing workspace settings.
- [ ] `DBY-SET-003` | `settings.yaml`, `scripts/init_project_memory.py`, `scripts/validate_project_settings.py` | Versioned defaults, explicit non-destructive settings upgrade, and current provider allowlists | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: ship, validate, and exercise the versioned default settings upgrade.
- [ ] `DBY-ROLE-001` | `roles/` | Orchestrator and IT role workflows with structured JSON slice records | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: translate role dispatch and slice-record transport.
- [ ] `DBY-KNOW-001` | `references/knowledge-model.md` | Project memory, keys, impact approval, health, and migration controls | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: implement memory resolution and validation flow.
- [ ] `DBY-MEM-002` | `references/task-memory.md`, `schemas/` | Task-scoped shared memory, owner-only canonical writes, compact JSON slice records, and analysis entrypoint | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: implement task-memory record transport and validation.
- [ ] `DBY-MEM-003` | `schemas/slice-record.schema.json`, `scripts/task_memory.py` | JSON-only slice-record schema, bounded validation, and record persistence without Markdown hand-off files | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: persist only validated JSON records under the task record directory.
- [ ] `DBY-SAFE-001` | `references/policies.md` | Git, tool, cost, secret, endpoint, prompt-injection, and policy-compliance controls | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map controls to platform permissions and prompts.
- [ ] `DBY-TOOLS-001` | `scripts/`, `tools/` | Manifest-bound project-local Python runtime tools and source-only development validation | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: enforce exact workspace-tool paths, manifest verification, and runtime/source separation.
- [ ] `DBY-TOOLS-002` | `references/custom-tools.md` | Custom-tool contract, workspace registry, approved runtimes, manifest schema, secret boundary, and untrusted-output handling | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: carry the custom-tool contract and its explicit workspace registry into the adapter.
- [ ] `DBY-TOOLS-003` | `skills/devbuddy-database`, `references/custom-tools.md` | Database execution is Plugin-owned; skills provide policy gates only and block without the selected package, manifest, database ID, read-only principal, and target-specific approval | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: carry the contract into the adapter and validate the workspace registry.
- [ ] `DBY-MANUAL-001` | `devbuddy-source-of-truth/manual/` | One central Thai/English HTML manual with Codex, Claude Code, and OpenCode installation pages | Status: `not_started` | Location: `devbuddy-source-of-truth/manual/` | Evidence: `check_manual_conformance.py`
  - Remark: Reason/blocker: Central manual not implemented; Owner: documentation maintainer; Next action: publish and validate shared platform guidance.
