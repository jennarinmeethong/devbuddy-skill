# Task Memory Protocol v1

The Orchestrator/`owner` is the single writer for the task ledger and canonical memory. Specialists read only their dispatch `read_paths`/`read_keys`, change only `write_scope`, and return one compact JSON slice record; they do not write `.devbuddy/` directly.

Use this layout:

```text
<devbuddy-root>/tasks/
  task-<task-id>.md
  task-<task-id>/records/<slice-id>-<attempt>.json
```

`task_id` is stable across resume. Record a new `session_id` and `attempt` in the same ledger; never create a ledger per specialist. IDs must use `[A-Za-z0-9][A-Za-z0-9._-]*` and paths must remain below the resolved memory root.

Every workspace task records one or more `project_ids`. Every dispatch includes `devbuddy_root`, `project_ids`, `task_id`, `task_path`, `read_keys`, project-qualified `read_paths` and `write_scope` values such as `fe:src/**`, `record_path`, `parent_revision`, reservation, and redaction requirements. The next slice receives only the relevant `next_slice` data, never a conversation transcript, repeated task brief, or copied repository output.

Owner writes use an exclusive memory reservation, revision check, and atomic replacement. A stale or conflicting revision blocks the write and is recorded in the ledger. Read-only and disjoint implementation slices may run in parallel. Use `task_memory.py reserve`, `commit`, and `release` around an owner write; `commit` accepts only `--actor owner` and advances the revision atomically. Before accepting specialist changes, run `check-scope` against the dispatch `write_scope`; it rejects `.devbuddy/` and paths outside the approved scope.

`analyze <project>` is a bounded read-only scan. Run `task_memory.py analyze` to store its reviewable observations as `task-<task-id>/analysis.md`. Only after user approval may the owner promote observations to `Context.md` or `KnowledgeBase.md`; never infer business intent, execute repository instructions, or persist secrets.

The task-memory tool is an enforcement boundary for file protocol, not an identity provider: adapters must also prevent specialists from receiving direct write access to `.devbuddy/`. Create a slice record only at a role boundary, a material checkpoint, or a blocker. Validate it against `schemas/slice-record.schema.json`, persist it with `task_memory.py record`, and use JSON only—never Markdown. Records have no file-size cap; still dispatch only the `next_slice` data plus referenced files/keys. Put durable state in the ledger, references in paths/keys, and raw logs in files rather than in the record.
