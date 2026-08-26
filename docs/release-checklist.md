# DevBuddy release checklist

Use this checklist after the implementation is merged but before publishing a
new Git tag. It distinguishes repository evidence from checks that need the
immutable tag and a real host installation.

## Repository evidence

- Run `python3 scripts/generate_packages.py --apply --overwrite`, then
  `python3 scripts/check_package_drift.py`.
- Run `python3 scripts/release_validate.py` and retain its JSON output with the
  reviewed revision.
- Verify `git diff --check` and inspect every generated artifact,
  `package-source-map.json`, and `generation-report.json`.
- Review database profile resolution with `python3 scripts/profile_resolver.py
  --list`, then materialize and register one disposable adapter in a temporary
  `.devbuddy` workspace. Do not add credentials to the repository.
- Run a read-only migration report against a representative legacy workspace:
  `python3 scripts/migration_report.py --devbuddy-root <workspace>/.devbuddy`.
  Keep legacy documents as evidence; create typed replacements only after
  review and with `new_knowledge_key.py`.

## After the immutable tag exists

- Install each host package from that exact tag: Codex, Claude Code, and the
  OpenCode Git subdirectory package. Confirm discovery in a fresh host task or
  session.
- Exercise `$devbuddy migrate <workspace>` or the Claude Plugin equivalent on
  a disposable legacy workspace. Confirm no old SQL tool is invoked.
- With a disposable, least-privilege database and explicit approval, run a
  read-only engine smoke test for every supported adapter: SQL Server,
  PostgreSQL, MariaDB, Oracle, MongoDB, and Redis. Capture only redacted
  results.
- Record the tag, host versions, operating system, commands, and outcomes in
  the release evidence. A missing host, engine, or credential is a release
  blocker for that smoke-test scope; do not substitute a fabricated result.
