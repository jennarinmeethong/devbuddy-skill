# Known Issues

Tracks defects found while implementing and live-testing the DevBuddy adapters. Not a knowledge entity — this is a plain engineering issue log, separate from the `.devbuddy/` project-memory model.

## ISSUE-001: `init_project_memory.py` crashes on Python < 3.10

- **Status:** [Codex] fixed 2026-07-27; [Claude] fixed 2026-07-27; [source-of-truth] fixed 2026-07-27
- **Found:** 2026-07-27, during the Claude adapter live smoke test (SMOKE-001)
- **Location:**
  - `devbuddy-codex/scripts/init_project_memory.py`
  - `devbuddy-source-of-truth/scripts/init_project_memory.py`
  - (already fixed) `devbuddy-claude/scripts/init_project_memory.py`
- **Symptom:** the script's `--dry-run` path succeeds, but actually creating the memory layout raises:
  ```
  TypeError: write_text() got an unexpected keyword argument 'newline'
  ```
- **Cause:** `Path.write_text(..., newline="\n")` — the `newline` parameter was added to `pathlib.Path.write_text` in Python 3.10. macOS ships Python 3.9.6 by default, so any user on stock macOS Python hits this the first time they actually initialise project memory, not during validation.
- **Fix:** drop the `newline="\n"` argument. The `CORE` dict content already uses `\n` literals, and `write_text` does not translate line endings on POSIX, so the argument was redundant even on 3.10+.
- **Tracking:** spawned as a background task (`task_451e5131`) on 2026-07-27; the remaining `devbuddy-source-of-truth` fix is still left for the user to action separately.
- **[Claude] fixed 2026-07-27** — `devbuddy-claude/scripts/init_project_memory.py` was already fixed before this issue log was written (see "Fix" above); confirmed here for the record.
- **[Codex] fixed 2026-07-27** — removed the Python 3.10-only `newline` argument from `devbuddy-codex/scripts/init_project_memory.py`; verified that the script creates the full memory layout successfully.
- **[Source-of-truth] fixed 2026-07-27** — removed the Python 3.10-only `newline` argument and added `--project-root` so the canonical `.devbuddy/` wrapper is created explicitly; `--root` remains available for approved external memory roots.

## ISSUE-002: agents write ad-hoc `devbuddy-ref` keys instead of real knowledge keys

- **Status:** [Claude] fixed 2026-07-27
- **Found:** 2026-07-27, during SMOKE-002 (developer -> qa live-test chain)
- **Location:** `devbuddy-claude/scripts/generate_agents.py`, specifically the `POLICY_DIGEST` block embedded in every generated agent under `agents/devbuddy-*.md`
- **Symptom:** `devbuddy-developer-low`, working unsupervised on a real fix, added `devbuddy-ref: SMOKE-002-fix-1` and `SMOKE-002-fix-2` comments next to its change. Both are the task ID, not a knowledge key — `references/knowledge-model.md` requires a type prefix (`BR`, `REQ`, `DB`, ...) naming an actual entity. `devbuddy-qa-low`, independently verifying the same file, caught this on its own and reported it as a finding without being told to look for it — so the reviewer-side instruction already works; the gap is on the writer side.
- **Cause:** the `POLICY_DIGEST` text in `generate_agents.py` says code carrying a `devbuddy-ref` should link to knowledge entities, but does not say a task ID is not a valid key, or that a reference to a not-yet-created entity should be a QA/knowledge-impact finding instead of an invented comment.
- **Fix applied:** added a line to `POLICY_DIGEST` in `devbuddy-claude/scripts/generate_agents.py`: *"A `devbuddy-ref` comment must name an existing knowledge key with a real type prefix (`BR`, `REQ`, `DB`, `API`, `ADR`, ...) — never a task ID, a slice name, or a placeholder you invented for this run. If your change should trace to a rule or requirement that has no entity yet, say so in your handoff as a knowledge-impact finding instead of writing a reference to something that doesn't exist."*
- **Verification:** regenerated all 27 agents (`python3 scripts/generate_agents.py`), confirmed with `--check`; full validation suite (`validate_skill_metadata.py`, `check_adapter_conformance.py`, `validate_manual.py`, `run_scenarios.py`, `validate_project_settings.py`) still passes; reinstalled to `~/.claude/skills/devbuddy/` and `~/.claude/agents/`, confirmed the fixed text is present in the installed copy and it still validates.
- **Not re-tested live:** the original failure mode (developer inventing a `devbuddy-ref`) has not been re-triggered against the fixed instruction text to confirm the model actually stops doing it — the fix addresses the instruction gap that caused it, but a live confirmation would need another developer dispatch on a task shaped to tempt the same mistake.

## ISSUE-003: a role wrote an artefact outside its authorized path without asking

- **Status:** [Claude] fixed 2026-07-27
- **Found:** 2026-07-27, during SMOKE-004 (loop-engineering live-test, retest round)
- **Location:** `devbuddy-claude/scripts/generate_agents.py` — same `POLICY_DIGEST` block as ISSUE-002; the relevant line is "Stay inside your role's authority and the artefacts your task package reserved for you."
- **Symptom:** `devbuddy-qa-low`, told explicitly "you may only edit `tests/test_tax.py` if you find a genuine gap," instead wrote a second file, `RETEST-ROUND2-RESULTS.txt`, at the project root — outside both the locked test path and the scope statement. Harmless in this case (a scratch project, a plain-text evidence file), but it is a real instance of a role creating an artefact the task package did not authorize, without pausing to ask.
- **Cause:** the current policy digest says to stay inside authorized artefacts, but does not say what to do when a role wants to produce something (like a human-readable evidence summary) that isn't one of them — it has no "ask before creating an unlisted artefact" instruction, so the model defaulted to just creating it.
- **Fix applied:** same edit as ISSUE-002 (one `POLICY_DIGEST` block covers both), added to the "stay inside your role's authority" line in `devbuddy-claude/scripts/generate_agents.py`: *"If you want to produce something the task package didn't list — a summary file, a scratch report, extra evidence — put it in your handoff text instead of creating a new file. If you believe a new artefact is genuinely needed, say so in the handoff and let the Orchestrator decide; do not create it first and explain afterward."*
- **Verification:** same regeneration, `--check`, full validation suite, and reinstall as ISSUE-002 — one fix, one regenerate, both issues covered.
- **Not re-tested live:** same caveat as ISSUE-002 — the instruction gap is fixed, but no dispatch has re-tried the exact scenario (QA producing an unlisted evidence file) against the corrected text to confirm the behavior actually stops.

## Live-test coverage as of 2026-07-27

Confirmed live via real Agent dispatch (not just static `scenarios.json` structure checks). Ledgers for all six runs are under `<scratch-project>/.devbuddy/tasks/`.

- **SMOKE-001** — single-role read-only review (`devbuddy-reviewer-medium`). Included a real `waiting_user` block (agent not yet registered in the session's registry) and a successful resume after restart — this is the `missing_agent_definition` scenario happening for real, not simulated.
- **SMOKE-002** — two-role write chain (`devbuddy-developer-low` -> `devbuddy-qa-low`), with a real artefact lock recorded before dispatch, a real code change, and a real test file QA wrote and ran independently (23/23 passing, rerun and confirmed outside the subagent). Found ISSUE-002 in the process.
- **SMOKE-003** — `devbuddy-security-medium` and `devbuddy-architect-medium` dispatched in one message on the same file, no lock needed since both were read-only. Confirmed genuinely independent output: Security found 3 real defects (NaN/Infinity bypassing the SMOKE-002 input guard, `tier=None` raising an uncaught `AttributeError` instead of `ValueError`, `bool` silently accepted as numeric) that neither Developer nor QA had caught; Architect gave a separate design assessment and correctly deferred concrete recommendations pending BR-001. Both respected read-only/assessment-only scope — no file or knowledge entity written.
- **SMOKE-004** — genuine bounded Loop Engineering cycle (`devbuddy-developer-low` <-> `devbuddy-qa-low`, max 2 attempts). Attempt 1 used bare `round()` and failed the classic `round(2.675, 2) == 2.67` (not `2.68`) float-representation gotcha — confirmed real and deterministic by the Orchestrator *before* designing the test, not staged after the fact. Routed back with QA's actual failure evidence; attempt 2 (`Decimal` + `ROUND_HALF_UP`) fixed it. QA retested the unchanged suite (4/4 pass, no regressions), independently reconfirmed by the Orchestrator. Found ISSUE-003 in the process.
- **SMOKE-005** — model-coverage block proven *without* dispatching anything: `devops-sre` is absent from every `allowed_roles` entry in this project's own `.devbuddy/settings.yaml`, confirmed by direct read before any Agent call. Correctly recorded as `waiting_user` rather than substituting a role, widening the allowlist, or calling the Agent tool anyway.
- **SMOKE-006** — real `unavailable_tool` block: `devbuddy-qa-low` was asked for `pytest-cov` by name, genuinely absent from this machine (confirmed independently by the Orchestrator beforehand). QA checked four ways (`which`, `python3 -m pytest`, `pip list`, target-file existence), did not install anything, did not silently substitute a tool, did not fabricate a coverage number, and reported the real gap.
- Minimum-sufficient selection was observed forcing an escalation, not choosing one: `reviewer`/`security`/`architect` are absent from the rank-1 `haiku`+`low` entries in the project's own allowlist, so `sonnet`+`medium` was the *lowest permitted* pair for those roles, while `developer`/`qa` correctly stayed at `haiku`+`low` throughout SMOKE-002, 004, and 006.

Not yet exercised live: `migration` and `incident` role chains, and 21 of the 27 role/effort agent definitions that haven't been individually dispatched (only `reviewer-medium`, `developer-low`, `qa-low`, `security-medium`, `architect-medium` have run for real so far).

## Live dispatch verification

- **Codex smoke test passed 2026-07-27** — a real read-only subagent dispatch accepted explicit `model=gpt-5.6-luna` and `reasoning_effort=low`; the handoff reported both values and completed successfully.
- **Claude live dispatches passed 2026-07-27** — SMOKE-001 through SMOKE-006 above are real Agent-tool dispatches of `devbuddy-<role>-<effort>` subagents with explicit models, not simulations; they produced ISSUE-002 and ISSUE-003. Still unexercised live: the `migration` and `incident` role chains, and 21 of the 27 agent definitions.
