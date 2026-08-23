# DevBuddy Plugin-first Migration Plan

**Status:** Draft — the database ownership baseline was completed in 0.4.6;
the Claude Code Plugin migration remains planned.  
**Decision requested:** make Plugin the only user-facing installation and update channel for every supported host, while retaining the portable DevBuddy core skill as a bundled implementation dependency.

## 1. Goal

Move DevBuddy to a Plugin-first distribution model:

```text
User installs one DevBuddy Plugin/profile
        |
        +-- selects a host adapter
        |     +-- Codex      -> $devbuddy
        |     +-- Claude Code -> /devbuddy
        |     +-- OpenCode   -> host adapter entry point
        |
        +-- bundles devbuddy-core policy skill
        +-- installs only approved optional capabilities
```

The goal is **not** to remove the core skill.  It is to remove the separate
standalone *distribution* of that skill.  `devbuddy-core` remains the single,
platform-neutral source of policy, scope, approvals, evidence, and closure.

## 2. Baseline and Constraints

### Current baseline

- All current `devbuddy.package.json` manifests declare `codex` and `opencode`
  compatibility only.
- The package-manifest schema allows only `codex` and `opencode` platform IDs.
- Codex has a package/plugin implementation under `plugin/devbuddy-core/`.
- Claude Code has a separate adapter under `devbuddy-claude/`.  Its installer
  currently copies a `devbuddy` skill and 54 role/effort agent definitions to
  the user configuration root.
- Project runtime tools are manifest-bound beneath `.devbuddy/tools/`; source
  maintenance scripts must not become delivery runtime tools.
- Database capability is Plugin-owned: `devbuddy-database-core` and the
  selected engine-adapter package own the executable, manifest, and runtime
  validation.  The portable database skill is policy-only and fails closed
  when the approved Plugin capability is unavailable.

### Implemented baseline — 0.4.6

The following bounded part of Phase 3 is complete and is the baseline for the
remaining migration work:

- `devbuddy-core` and `devbuddy-database` now describe database access as an
  abstract Tier 2 capability.  They do not ship, select, configure, or invoke
  a database executable, driver, or workspace custom tool.
- Database execution is permitted only through the installed
  `devbuddy-database-core` package plus a profile-selected
  `devbuddy-database-<engine>` adapter, with a manifest, read-only principal,
  and target-specific approval.  Missing prerequisites end in `waiting_user`;
  direct-driver, shell, and custom-tool fallbacks are prohibited.
- The package catalog carries the database runtime (database core package
  `1.0.2`); common policy and both adapters are synchronized at source-spec
  version `0.4.6`.
- The English and Thai manuals, adapter implementation checklists, generated
  package metadata, source-preservation allowlist, and architecture tests were
  updated.  The targeted policy test and source/adaptor conformance,
  skill-contract, package, preservation, and secret-exclusion validators pass.

This does **not** add Claude Code Plugin support.  The present Claude adapter
is still a standalone compatibility path until Phases 0–2 are completed.

### Non-negotiable constraints

- Preserve the portable core policy and platform-specific approval semantics.
- Keep existing Codex, Claude Code, and OpenCode installations working until
  an explicit migration succeeds.
- Use dry-run first for installation, migration, update, and removal.
- Never overwrite unknown host files or silently broaden permissions.
- Keep secrets, project state, task ledgers, and canonical knowledge outside
  package artifacts.
- Treat database access as Tier 2: manifest, read-only policy, and
  target-specific approval remain mandatory.

## 3. Target Architecture

| Layer | Ownership | Responsibilities | Must not contain |
|---|---|---|---|
| Portable core | `skills/devbuddy-core` | Lifecycle policy, scope, approvals, evidence, closure contract | Host commands, host paths, runtime binaries |
| Package catalog | `plugin/*/devbuddy.package.json` | Dependency graph, permission tier, compatibility, composition metadata | Credentials, project state |
| Host adapter | Host-specific package payload | Invocation, agent transport, model/effort mapping, host installation layout | Independent policy forks |
| Runtime capability | Core/optional package payload | Versioned scripts, tool manifests, database runtime and safety validation | Implicit permission or raw secrets |
| Workspace | `.devbuddy/` | Task state, local settings, project-local tools, knowledge references | Package source or build output |

### Distribution rule

The Plugin/profile is the only artifact an end user installs.  It may deploy a
host-native skill, command, and agent definitions because those are the
runtime format the host consumes, but users do not install `devbuddy-core` or
the Claude adapter separately.

## 4. Decisions Required Before Implementation

The following are explicit design gates, not assumptions:

1. Confirm the supported Claude Code package/distribution format and its
   lifecycle commands (install, update, uninstall, discovery) from current
   official host documentation.
2. Select one canonical package ID for the Claude adapter (recommended:
   `devbuddy-claude-code`) and one compatibility identifier (recommended:
   `claude-code`).
3. Define whether one profile may install multiple host adapters, or whether a
   profile must select exactly one host per installation.
4. Define the retained migration window and the removal version for legacy
   standalone installers.
5. Approve the user-visible migration prompts, including conflict and rollback
   handling.

No implementation phase may mark the Claude adapter supported until decision
1 is verified against the selected Claude Code host version.

## 5. Phased Implementation Plan

### Phase 0 — Architecture and compatibility contract

Create a canonical platform model that includes `codex`, `claude-code`, and
`opencode`.  Document the adapter capability contract so that the core remains
host-neutral while every host declares its invocation and dispatch transport.

**Exit evidence:** reviewed schema change, compatibility matrix, and a
documented Claude Code packaging decision.

### Phase 1 — Package model and generation

Extend package schemas, validators, source mapping, profile resolution, and
drift checks for a Claude Code adapter package.  Keep generated payloads
traceable to their portable source and prevent an overwrite without explicit
`--apply --overwrite`.

**Exit evidence:** package-schema tests, manifest validation, generation
dry-run, provenance record, and drift detection for all three hosts.

### Phase 2 — Claude Code adapter package

Create the Claude-specific package payload.  It must install the host-native
`/devbuddy` entry point and role/effort agents through the Plugin installer,
while preserving Claude's current explicit-invocation and effort transport
rules.  The package must depend on `devbuddy-core`; it must not copy or fork
the core policy.

**Exit evidence:** isolated install/update/uninstall dry runs, host discovery,
invocation-gate verification, and one read-only specialist dispatch with an
explicit approved model and effort.

### Phase 3 — Tool ownership and permissions

Move every tool from standalone installation ownership to package ownership.
The portable skill may name abstract capabilities and their gates, but it must
not depend on a standalone installer path or directly ship untracked runtime
tools.

**Progress:** database ownership is complete as the 0.4.6 baseline above.
The remaining Phase 3 work inventories and assigns provenance for every other
delivery runtime and host asset.

**Exit evidence:** each tool has a package owner, manifest/provenance,
permission tier, and installation target; secret-exclusion and Tier 2 database
safety tests pass.

### Phase 4 — Migration and deprecation

Turn the existing Codex and Claude standalone installers into migration-aware
compatibility shims.  They must first report the required Plugin install or
migration path, then remain functional only for the approved compatibility
window.  Do not delete them in the same release that introduces Plugin-first
distribution.

**Exit evidence:** clean-install, existing-install, conflict, rollback, and
uninstall scenarios demonstrate no unknown-file overwrite or data loss.

### Phase 5 — Documentation and release

Update Thai and English manuals, platform pages, README, plugin presentation,
release notes, and upgrade guidance.  State one user journey: install a
Plugin/profile, choose approved optional capabilities, then invoke the
host-native DevBuddy command.

**Exit evidence:** bilingual manual conformance, link checks, package
discovery evidence, release-validation report, and documented known limits.

## 6. Implementation Checklist

### A. Architecture gates

- [ ] Verify and record the Claude Code packaging/discovery mechanism.
- [ ] Approve the canonical Claude package ID and compatibility identifier.
- [ ] Publish the three-host compatibility matrix.
- [ ] Define adapter capability requirements: invocation, agent dispatch,
  model/effort transport, permission behavior, update, uninstall, and
  discovery.
- [ ] Define the standalone-installer deprecation and removal schedule.

### B. Package and schema work

- [ ] Extend `schemas/package-manifest.schema.json` with the approved Claude
  compatibility identifier.
- [ ] Update package validation for platform IDs, dependencies, and adapter
  payload requirements.
- [ ] Add the Claude adapter package manifest and dependency on
  `devbuddy-core`.
- [ ] Add source-map entries and provenance generation for the Claude payload.
- [ ] Add profile resolution rules for host selection and incompatible mixes.
- [ ] Extend source-preservation and drift checks to the Claude package.

### C. Claude adapter package

- [ ] Package the `/devbuddy` entry point without changing the portable core.
- [ ] Package all current role/effort agent definitions with generated
  provenance.
- [ ] Preserve `disable-model-invocation: true` or the verified equivalent.
- [ ] Preserve explicit approved-model selection and Claude effort transport.
- [ ] Preserve `rtk_required` propagation and approval boundaries.
- [ ] Add package-level dry-run, apply, update, conflict, and uninstall flows.
- [ ] Add host discovery and refresh instructions.

### D. Tool and runtime ownership

- [x] DBY-TOOLS-003 — make database skills policy-only and require the
  Plugin-owned database core plus a selected engine adapter. Evidence:
  `tests/test_plugin_architecture.py`, package and conformance validation,
  released in common source-spec `0.4.6`.

- [ ] Inventory every currently installed script, runtime, manifest, and agent
  asset.
- [ ] Classify each item as portable policy, host adapter payload, package
  runtime, project-local runtime, source-maintenance utility, or deprecated
  compatibility shim.
- [ ] Move delivery runtimes under package ownership and retain manifest-hash
  verification when provisioning `.devbuddy/tools/`.
- [ ] Keep source-maintenance utilities out of installed delivery runtimes.
- [ ] Verify that no package artifact contains credentials, knowledge, task
  state, or user-specific configuration.
- [ ] Keep database runtimes and engine adapters optional, read-only, and Tier
  2 gated.

### E. Migration and backward compatibility

- [ ] Detect recognized legacy Codex and Claude standalone installations.
- [ ] Produce a dry-run migration report before any write.
- [ ] Refuse unknown-file conflicts and preserve user modifications.
- [ ] Back up or retain a reversible migration record before replacement.
- [ ] Provide rollback instructions and a tested rollback path.
- [ ] Deprecate legacy installers with actionable Plugin migration guidance.
- [ ] Remove legacy standalone installation only after the approved support
  window and telemetry/evidence criteria are met.

### F. Documentation and quality

- [ ] Update English and Thai manual pages for Codex, Claude Code, and shared
  installation guidance.
- [ ] Update README, plugin presentation, and release notes.
- [ ] Update package/profile reference documentation and examples.
- [ ] Add unit tests for schema, generator, resolver, and installer behavior.
- [ ] Add integration tests for Codex, Claude Code, and OpenCode discovery.
- [ ] Add regression tests for policy, approvals, task state, and tool
  manifests.
- [ ] Run manual conformance, semantic conformance, skill-contract, package,
  source-preservation, secret-exclusion, and release validation checks.

## 7. Verification Matrix

| Scenario | Expected result | Evidence |
|---|---|---|
| Fresh Codex installation | Plugin installs only recognized package artifacts; `$devbuddy` is available | Dry-run and host discovery output |
| Fresh Claude Code installation | Plugin installs host-native payload; `/devbuddy` and required agents are available | Dry-run and host discovery output |
| OpenCode installation | Existing adapter behavior remains available through the profile | Compatibility test report |
| Existing standalone installation | Migration is detected and previewed; no write without apply | Migration dry-run report |
| Unknown conflicting file | Installation stops without replacing it | Conflict test |
| Core-only profile | No optional package or database runtime is installed | Resolved profile report |
| Database profile | Target-specific approval and read-only adapter rules remain enforced | Tier 2 safety tests |
| Upgrade and rollback | Package version is traceable and restoration is possible | Upgrade/rollback test report |

## 8. Definition of Done

The migration is complete only when all conditions below are met:

- A user can install DevBuddy through one Plugin/profile workflow for each
  supported host.
- Codex, Claude Code, and OpenCode use the same portable core policy without
  policy forks.
- `devbuddy-core` is no longer a separately installed user-facing product, but
  remains bundled and versioned as the portable implementation source.
- All runtime tools have explicit package ownership, permission tiers, and
  provenance.
- Legacy standalone installations have a tested, reversible migration path.
- All required automated and host-level validation evidence passes.
- Thai and English documentation accurately describes the Plugin-first flow.

## 9. Out of Scope for This Migration

- Changing DevBuddy policy semantics, role authority, or database safety rules.
- Adding new external service integrations merely to demonstrate the packaging
  model.
- Migrating user task data, knowledge, credentials, or database configuration
  into package artifacts.
- Deleting existing standalone adapters before the approved deprecation window.
