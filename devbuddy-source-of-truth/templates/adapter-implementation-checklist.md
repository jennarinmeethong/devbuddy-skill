# Adapter Implementation Checklist

Common specification version: `0.2.0`

## Status legend

- `done`: implemented and verified.
- `not_started`: not implemented.
- `in_progress`: partially implemented or blocked.

## Checklist

- [ ] `DBY-CORE-001` | `SKILL.md` | Core orchestration, approvals, risk, slicing, batch, and loop policies | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map common workflow to platform mechanics.
- [ ] `DBY-SET-001` | `settings.yaml` | Settings schema, validation, budgets, model, environment, and cost controls | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map settings to platform configuration.
- [ ] `DBY-MODEL-002` | `settings.yaml`, `roles/orchestrator.md` | Required per-dispatch approved model and effort-level selection with task-ledger evidence | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map and verify model/effort selection in platform dispatch.
- [ ] `DBY-MODEL-003` | `settings.yaml`, `references/policies.md` | Minimum-sufficient model/effort selection and recorded escalation reason | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: enforce minimum-sufficient selection and escalation evidence.
- [ ] `DBY-ROLE-001` | `roles/` | Orchestrator and IT role workflows with structured handoffs | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: translate role dispatch and handoff transport.
- [ ] `DBY-KNOW-001` | `references/knowledge-model.md` | Project memory, keys, impact approval, health, and migration controls | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: implement memory resolution and validation flow.
- [ ] `DBY-MEM-002` | `references/task-memory.md`, `templates/` | Task-scoped shared memory, owner-only canonical writes, compact handoffs, and analysis entrypoint | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: implement task-memory transport and validation.
- [ ] `DBY-SAFE-001` | `references/policies.md` | Git, tool, cost, secret, endpoint, prompt-injection, and policy-compliance controls | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: map controls to platform permissions and prompts.
- [ ] `DBY-TOOLS-001` | `scripts/` | Python memory initialization, bootstrap, validation, checklist, knowledge, and manual conformance tools | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: validate Python/tool invocation support.
- [ ] `DBY-TOOLS-002` | `references/custom-tools.md` | Custom-tool contract, workspace registry, approved runtimes, manifest schema, secret boundary, and untrusted-output handling | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: carry the contract into the adapter and validate the workspace registry.
- [ ] `DBY-MANUAL-001` | `manual/` | Thai/English HTML manual and platform installation pages | Status: `not_started` | Location: `<adapter path>` | Evidence: `<evidence>`
  - Remark: Reason/blocker: Adapter not implemented; Owner: adapter maintainer; Next action: publish adapter-specific manual guidance.
