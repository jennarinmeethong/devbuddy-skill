# Release notes — Plugin-first migration

## Added

- Claude Code marketplace Plugin `devbuddy-claude-code@devbuddy`, including the
  explicit namespaced entrypoint and generated role/effort agent payload.
- Three-host platform contract, host-selecting profiles, generated provenance,
  runtime-ownership inventory, and Plugin validation.
- Migration-safe compatibility reports for both legacy Claude and Codex
  installers.

## Changed

- New installations use a Plugin/profile workflow. The portable core remains a
  bundled implementation dependency, not a separately installed product.
- Legacy installers now report the migration path by default. Their historical
  `--apply` path remains available through the DevBuddy 1.x compatibility
  window; `--legacy-install` is an optional explicit spelling.

## Upgrade and rollback

1. Preview the legacy installer migration report.
2. Install the host Plugin/profile and verify discovery.
3. Refresh the host and invoke the native DevBuddy entrypoint.
4. To roll back, disable or uninstall the Plugin/profile; legacy files were
   retained and are not replaced by migration.

The 2.0 removal decision is gated on clean-install, conflict, rollback,
discovery, and release-validation evidence.
