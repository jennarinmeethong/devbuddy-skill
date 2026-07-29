# Task Memory Protocol v1

The Orchestrator/`owner` is the single writer for the task ledger and canonical memory. Specialists read only their dispatch `read_paths`/`read_keys`, change only `write_scope`, and return a compact handoff; they do not write `.devbuddy/` directly.

Use `<memory-root>/tasks/<project-id>/task-<task-id>.md` with handoffs at `<memory-root>/tasks/<project-id>/task-<task-id>/handoffs/<slice-id>-<attempt>.md`. Reuse `task_id` on resume and add a `session_id`/`attempt` to the same ledger. IDs use `[A-Za-z0-9][A-Za-z0-9._-]*` and paths must remain below the resolved memory root.

Every dispatch includes `memory_root`, `task_id`, `task_path`, `read_keys`, `read_paths`, `write_scope`, `handoff_path`, `parent_revision`, reservation, and redaction requirements. The next slice receives only the relevant handoff delta. Owner writes use `task_memory.py reserve`, `commit --actor owner`, and `release`; the commit atomically advances the revision and stale revisions block safely. Run `check-scope` before accepting specialist output; it rejects direct `.devbuddy/` writes and paths outside the dispatch scope. The tool enforces the file protocol, while the adapter must keep direct `.devbuddy/` write access away from specialists.

`/devbuddy analyze <project>` is a bounded read-only scan. `task_memory.py analyze` stores reviewable observations in `task-<task-id>/analysis.md`; only the owner may promote approved observations to canonical memory. Handoffs have a hard 12,000 UTF-8 byte ceiling: send the next-slice delta, never a transcript.
