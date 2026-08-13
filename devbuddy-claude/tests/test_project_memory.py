#!/usr/bin/env python3
"""Regression tests for the common multi-project workspace."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_project_memory.py"
BOOTSTRAP = ROOT / "scripts" / "bootstrap_knowledge.py"
TASK = ROOT / "scripts" / "task_memory.py"
KNOWLEDGE_VALIDATOR = ROOT / "scripts" / "validate_knowledge.py"
VALIDATOR = ROOT / "scripts" / "validate_project_settings.py"
METADATA_VALIDATOR = ROOT / "scripts" / "validate_skill_metadata.py"
SETTINGS = ROOT / "tests" / "fixtures" / "valid-settings.yaml"
MISSING_BUDGET = ROOT / "tests" / "fixtures" / "missing-budget.yaml"
MANIFEST = ROOT / "tests" / "fixtures" / "custom-tool-manifest.json"
INSTALLER = ROOT / "scripts" / "install_claude_adapter.py"
SCENARIOS = ROOT / "tests" / "scenarios.json"
RUN_SCENARIOS = ROOT / "scripts" / "run_scenarios.py"
# Directories a build or an editor restore creates. They must never be seeded
# into a workspace or installed into a configuration root.
SKIP_DIRS = ("bin", "obj", "releases", ".venv", "__pycache__")

# An entity that satisfies every required field, so a negative test fails for
# the one reason it is testing rather than for a missing field.
ENTITY = (
    "---\nid: {id}\ntype: requirement\nstatus: active\nowner: ba-pm\n"
    "source: test\nproject_ids: [fe]\nlast_verified: 2026-08-03\nconfidence: verified\n---\n{body}"
)


def run(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *(str(arg) for arg in args)], capture_output=True, text=True, check=False)


class WorkspaceTests(unittest.TestCase):
    def make_workspace(self, temporary: str) -> tuple[Path, Path, Path]:
        base = Path(temporary)
        frontend, backend = base / "frontend", base / "backend"
        frontend.mkdir(); backend.mkdir()
        root = base / "knowledge" / ".devbuddy"
        result = run(INIT, "--devbuddy-root", root, "--project", "fe=../frontend", "--project", "be=../backend")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return root, frontend, backend

    def test_initializer_creates_shared_layout_registry_and_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            self.assertTrue((root / "knowledge-base" / "Context.md").is_file())
            self.assertTrue((root / "tasks").is_dir())
            self.assertTrue((root / "tools" / "task_memory.py").is_file())
            manifest = json.loads((root / "tools" / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("task_memory.py", manifest["files"])
            settings = (root / "settings.yaml").read_text(encoding="utf-8")
            self.assertIn("fe:", settings); self.assertIn("be:", settings)
            self.assertIn("memory_root: knowledge-base", settings)
            self.assertIn("is_rtk: false", settings)
            self.assertIn("max_concurrency: 2", settings)
            self.assertIn("task_timeout_seconds: 900", settings)
            self.assertIn("retry_limit: 1", settings)

    def test_settings_upgrade_fills_defaults_without_overwriting_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            frontend = base / "frontend"; frontend.mkdir()
            root = base / "knowledge" / ".devbuddy"; root.mkdir(parents=True)
            settings = root / "settings.yaml"
            settings.write_text(
                "schema_version: 1\nsettings_version: 0.4.4\nworkspace:\n  projects:\n    fe:\n      path: ../frontend\n"
                "memory_root: knowledge-base\norchestration:\n  max_concurrency: 7\n  task_timeout_seconds: 900\n  retry_limit: 1\n"
                "tools:\n  is_rtk: true\n",
                encoding="utf-8",
            )
            preview = run(INIT, "--devbuddy-root", root, "--upgrade-settings", "--dry-run")
            self.assertEqual(preview.returncode, 0, preview.stdout)
            self.assertIn("UPGRADE SETTINGS", preview.stdout)
            self.assertIn("settings_version: 0.4.4", settings.read_text(encoding="utf-8"))
            applied = run(INIT, "--devbuddy-root", root, "--upgrade-settings")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            content = settings.read_text(encoding="utf-8")
            self.assertIn("settings_version: 0.4.5", content)
            self.assertIn("max_concurrency: 7", content)
            self.assertIn("is_rtk: true", content)
            self.assertIn("gpt-5.6-sol", content)
            self.assertIn("claude-fable", content)
            self.assertEqual(run(VALIDATOR, settings).returncode, 0)

    def test_dry_run_writes_nothing_and_rejects_duplicate_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / "source"; source.mkdir(); root = base / ".devbuddy"
            dry = run(INIT, "--devbuddy-root", root, "--project", f"app={source}", "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stdout); self.assertFalse(root.exists())
            duplicate = run(INIT, "--devbuddy-root", root, "--project", f"one={source}", "--project", f"two={source}")
            self.assertNotEqual(duplicate.returncode, 0); self.assertIn("duplicate resolved", duplicate.stdout)

    def test_add_missing_is_idempotent_and_preserves_core(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            context = root / "knowledge-base" / "Context.md"
            context.write_text("custom\n", encoding="utf-8")
            second = run(INIT, "--devbuddy-root", root)
            self.assertEqual(second.returncode, 0, second.stdout)
            self.assertEqual(context.read_text(encoding="utf-8"), "custom\n")

    def test_safe_layout_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".devbuddy"; root.mkdir()
            (root / "Context.md").write_text("legacy\n", encoding="utf-8")
            preview = run(INIT, "--devbuddy-root", root, "--migrate-layout", "--dry-run")
            self.assertIn("MOVE:", preview.stdout); self.assertTrue((root / "Context.md").exists())
            applied = run(INIT, "--devbuddy-root", root, "--migrate-layout")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            self.assertEqual((root / "knowledge-base" / "Context.md").read_text(encoding="utf-8"), "legacy\n")

    def test_modified_tool_blocks_explicit_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            tool = root / "tools" / "task_memory.py"; tool.write_text("modified\n", encoding="utf-8")
            result = run(INIT, "--devbuddy-root", root, "--upgrade-tools")
            self.assertNotEqual(result.returncode, 0); self.assertIn("modified or unrecognized", result.stdout)

    def test_bootstrap_uses_registered_project_and_appends_shared_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, frontend, backend = self.make_workspace(temporary)
            (frontend / "package.json").write_text("{}", encoding="utf-8")
            (backend / "pyproject.toml").write_text("[project]\nname='api'\n", encoding="utf-8")
            for project_id in ("fe", "be"):
                result = run(BOOTSTRAP, "--devbuddy-root", root, "--project-id", project_id, "--apply")
                self.assertEqual(result.returncode, 0, result.stdout)
            context = (root / "knowledge-base" / "Context.md").read_text(encoding="utf-8")
            self.assertIn("Bootstrap inventory: fe", context); self.assertIn("Bootstrap inventory: be", context)

    def test_workspace_task_and_project_qualified_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            created = run(TASK, "init", "--devbuddy-root", root, "--project-id", "fe", "--project-id", "be", "--task-id", "001")
            self.assertEqual(created.returncode, 0, created.stdout)
            ledger = root / "tasks" / "task-001.md"
            self.assertIn("Project IDs: [fe, be]", ledger.read_text(encoding="utf-8"))
            allowed = run(TASK, "check-scope", "--devbuddy-root", root, "--task-id", "001", "--write-scope", "fe:src,be:apps/api", "--changed", "fe:src/main.ts")
            self.assertEqual(allowed.returncode, 0, allowed.stdout)
            denied = run(TASK, "check-scope", "--devbuddy-root", root, "--task-id", "001", "--write-scope", "fe:src", "--changed", "be:src/main.py")
            self.assertNotEqual(denied.returncode, 0)

    def test_knowledge_entity_requires_project_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            entity = root / "knowledge-base" / "requirements" / "req.md"
            entity.write_text("---\nid: REQ-001\ntype: requirement\nstatus: active\nowner: ba-pm\nsource: test\nlast_verified: 2026-08-02\nconfidence: verified\n---\n", encoding="utf-8")
            result = run(KNOWLEDGE_VALIDATOR, "--devbuddy-root", root)
            self.assertNotEqual(result.returncode, 0); self.assertIn("project_ids", result.stdout)

    def test_knowledge_validator_accepts_an_initialised_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            result = run(KNOWLEDGE_VALIDATOR, "--devbuddy-root", root)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_knowledge_validator_rejects_invalid_entity_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            entity = root / "knowledge-base" / "requirements" / "invalid.md"
            entity.write_text(ENTITY.format(id="BAD-001", body=""), encoding="utf-8")
            result = run(KNOWLEDGE_VALIDATOR, "--devbuddy-root", root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid knowledge id", result.stdout)

    def test_knowledge_validator_rejects_unresolved_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            entity = root / "knowledge-base" / "requirements" / "requirement.md"
            entity.write_text(
                ENTITY.format(id="REQ-001", body="<!-- devbuddy-ref: FEAT-missing -->\nSee [[API-missing]].\n"),
                encoding="utf-8",
            )
            result = run(KNOWLEDGE_VALIDATOR, "--devbuddy-root", root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unresolved devbuddy-ref FEAT-missing", result.stdout)
            self.assertIn("unresolved wiki-link API-missing", result.stdout)

    def test_bootstrap_dry_run_scans_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, frontend, _backend = self.make_workspace(temporary)
            (frontend / "package.json").write_text('{"scripts":{"test":"jest","build":"vite"}}', encoding="utf-8")
            before = (root / "knowledge-base" / "Context.md").read_text(encoding="utf-8")
            result = run(BOOTSTRAP, "--devbuddy-root", root, "--project-id", "fe")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("FACT manifests: package.json", result.stdout)
            self.assertIn("DRY RUN", result.stdout)
            self.assertEqual((root / "knowledge-base" / "Context.md").read_text(encoding="utf-8"), before)

    def test_bootstrap_records_observations_as_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, frontend, _backend = self.make_workspace(temporary)
            (frontend / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
            result = run(BOOTSTRAP, "--devbuddy-root", root, "--project-id", "fe", "--apply")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            context = (root / "knowledge-base" / "Context.md").read_text(encoding="utf-8")
            self.assertIn("pyproject.toml", context)
            # Bootstrap output is an inventory, never an approved fact. If this
            # marker disappears, observations start reading as canonical memory.
            self.assertIn("pending user/role review", context)

    def test_bootstrap_requires_a_devbuddy_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project, external = base / "project", base / "vault"
            project.mkdir()
            (project / "package.json").write_text("{}", encoding="utf-8")
            result = run(INIT, "--devbuddy-root", external, "--project", f"app={project}")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be named .devbuddy", result.stdout)


class TaskMemoryTests(unittest.TestCase):
    """Task Memory Protocol v1 at its file boundary.

    task_memory.py is the only thing standing between two concurrent specialists
    and a corrupted canonical memory, so each guarantee it advertises — resume,
    JSON slice-record durability, revision freshness, owner-only commits, reservation
    exclusivity, scope containment, read-only analysis — is asserted here rather
    than trusted.
    """

    def make_task(self, temporary: str) -> Path:
        base = Path(temporary)
        frontend = base / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
        root = base / "knowledge" / ".devbuddy"
        created = run(INIT, "--devbuddy-root", root, "--project", f"fe={frontend}")
        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        started = run(TASK, "init", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001", "--session-id", "s1")
        self.assertEqual(started.returncode, 0, started.stdout)
        return root

    def test_resume_reuses_the_task_id_and_rejects_a_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_task(temporary)
            resumed = run(TASK, "init", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001", "--session-id", "s2")
            self.assertEqual(resumed.returncode, 0, resumed.stdout)
            self.assertIn("RESUME:", resumed.stdout)
            ledger = (root / "tasks" / "task-001.md").read_text(encoding="utf-8")
            self.assertIn("- s2", ledger)
            escaped = run(TASK, "init", "--devbuddy-root", root, "--project-id", "../bad", "--task-id", "002")
            self.assertNotEqual(escaped.returncode, 0)
            self.assertIn("invalid project ID", escaped.stdout)

    def test_json_slice_record_persists_for_the_next_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_task(temporary)
            inbox = root / "tasks" / "task-001" / "inbox"; inbox.mkdir()
            source = inbox / "developer-1.json"
            payload = {"schema_version": 1, "task_id": "001", "slice_id": "developer", "attempt": 1, "parent_revision": 0, "role": "developer", "model": "haiku", "effort": "low", "status": "completed", "result": "Implemented focused change.", "evidence": [], "next_slice": {"summary": "Run focused tests.", "read_paths": [], "read_keys": []}, "knowledge_keys": [], "knowledge_proposal": None, "blockers": [], "required_approval": None}
            source.write_text(json.dumps(payload), encoding="utf-8")
            result = run(TASK, "record", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                         "--slice-id", "developer", "--attempt", "1", "--parent-revision", "0", "--input", source)
            self.assertEqual(result.returncode, 0, result.stdout)
            target = root / "tasks" / "task-001" / "records" / "developer-1.json"
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), payload)

    def test_large_valid_slice_record_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_task(temporary)
            inbox = root / "tasks" / "task-001" / "inbox"; inbox.mkdir()
            source = inbox / "developer-1.json"
            payload = {"schema_version": 1, "task_id": "001", "slice_id": "developer", "attempt": 1, "parent_revision": 0, "role": "developer", "model": "haiku", "effort": "low", "status": "completed", "result": "x" * 1_501, "evidence": [{"ref": f"tests/case-{index}", "outcome": "x" * 500} for index in range(16)], "next_slice": {"summary": "Run focused tests.", "read_paths": [], "read_keys": []}, "knowledge_keys": [], "knowledge_proposal": None, "blockers": [], "required_approval": None}
            source.write_text(json.dumps(payload), encoding="utf-8")
            self.assertGreater(len(source.read_bytes()), 4_000)
            result = run(TASK, "record", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                         "--slice-id", "developer", "--attempt", "1", "--parent-revision", "0", "--input", source)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads((root / "tasks" / "task-001" / "records" / "developer-1.json").read_text(encoding="utf-8")), payload)

    def test_stale_revision_is_blocked_and_only_owner_commits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_task(temporary)
            committed = run(TASK, "commit", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                            "--actor", "owner", "--expected-revision", "0", "--summary", "approved canonical update")
            self.assertEqual(committed.returncode, 0, committed.stdout)
            stale = run(TASK, "reserve", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                        "--actor", "developer", "--scope", "fe:src", "--expected-revision", "0")
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("stale expected revision", stale.stdout)
            non_owner = run(TASK, "commit", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                            "--actor", "developer", "--expected-revision", "1", "--summary", "must fail")
            self.assertNotEqual(non_owner.returncode, 0)
            self.assertIn("only --actor owner", non_owner.stdout)
            self.assertIn("- Memory revision: 1", (root / "tasks" / "task-001.md").read_text(encoding="utf-8"))

    def test_reservation_is_exclusive_and_scope_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_task(temporary)
            reserved = run(TASK, "reserve", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                           "--actor", "developer", "--scope", "fe:src", "--expected-revision", "0")
            self.assertEqual(reserved.returncode, 0, reserved.stdout)
            conflict = run(TASK, "reserve", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                           "--actor", "qa", "--scope", "fe:src", "--expected-revision", "0")
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn("reservation already exists", conflict.stdout)
            outside = run(TASK, "check-scope", "--devbuddy-root", root, "--task-id", "001",
                          "--write-scope", "fe:src", "--changed", "fe:knowledge-base/Context.md")
            self.assertNotEqual(outside.returncode, 0)
            self.assertIn("outside write_scope", outside.stdout)

    def test_analysis_is_read_only_and_lands_in_the_task_area(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_task(temporary)
            before = (root / "knowledge-base" / "Context.md").read_text(encoding="utf-8")
            result = run(TASK, "analyze", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001")
            self.assertEqual(result.returncode, 0, result.stdout)
            report = root / "tasks" / "task-001" / "analysis.md"
            self.assertIn("package.json", report.read_text(encoding="utf-8"))
            # analyze must never promote observations to canonical memory; only
            # an owner commit may do that.
            self.assertEqual((root / "knowledge-base" / "Context.md").read_text(encoding="utf-8"), before)


class SettingsValidatorTests(unittest.TestCase):
    def test_shipped_settings_validate(self) -> None:
        result = run(VALIDATOR, SETTINGS)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_rtk_setting_must_be_boolean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "settings.yaml"
            content = SETTINGS.read_text(encoding="utf-8").replace(
                "orchestration:", "tools:\n  is_rtk: enabled\norchestration:"
            )
            invalid.write_text(content, encoding="utf-8")
            result = run(VALIDATOR, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tools.is_rtk", result.stdout)

    def test_rtk_setting_accepts_true(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            enabled = Path(temporary) / "settings.yaml"
            content = SETTINGS.read_text(encoding="utf-8").replace(
                "orchestration:", "tools:\n  is_rtk: true\norchestration:"
            )
            enabled.write_text(content, encoding="utf-8")
            result = run(VALIDATOR, enabled)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_budget_fixture_is_rejected(self) -> None:
        result = run(VALIDATOR, MISSING_BUDGET)
        self.assertNotEqual(result.returncode, 0)
        # A dispatch without a timeout or retry limit can run unbounded, so both
        # budgets are required rather than defaulted.
        self.assertIn("task_timeout_seconds", result.stdout)
        self.assertIn("retry_limit", result.stdout)

    def test_empty_memory_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "settings.yaml"
            content = SETTINGS.read_text(encoding="utf-8").replace("memory_root: knowledge-base", "memory_root:")
            invalid.write_text(content, encoding="utf-8")
            result = run(VALIDATOR, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("memory_root", result.stdout)

    def test_duplicate_model_rank_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "settings.yaml"
            content = SETTINGS.read_text(encoding="utf-8").replace("      rank: 2", "      rank: 1", 1)
            invalid.write_text(content, encoding="utf-8")
            result = run(VALIDATOR, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate rank", result.stdout)


class CustomToolRegistryTests(unittest.TestCase):
    """The workspace custom-tool registry in `.devbuddy/settings.yaml`.

    The manifest fixture mirrors a real read-only database tool, so these tests
    check the contract against the shape projects actually produce rather than
    an invented one.
    """

    BASE = """schema_version: 1
settings_version: 0.4.5
workspace:
  projects:
    app:
      path: repo
memory_root: knowledge-base
orchestration:
  max_concurrency: 2
  task_timeout_seconds: 900
  retry_limit: 1
  approved_models:
    - id: haiku
      rank: 1
      allowed_roles: [developer, qa]
      allowed_risks: [low]
  approved_effort_levels:
    - id: low
      rank: 1
      allowed_roles: [developer, qa]
      allowed_risks: [low]
"""

    def workspace(self, temporary: str, *, runtimes: str = "[python, dotnet]", runtime: str = "dotnet",
                  secret_file: bool = True, manifest: str | None = None) -> Path:
        """A validated workspace registering one custom tool."""
        root = Path(temporary) / ".devbuddy"
        (root.parent / "repo").mkdir(parents=True)
        tool = root / "tools" / "db-query-tool"
        tool.mkdir(parents=True)
        (tool / "tool.json").write_text(
            manifest if manifest is not None else MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
        entry = f"custom_tools:\n  - name: readonly_database_query\n    runtime: {runtime}\n    manifest: tools/db-query-tool/tool.json\n"
        if secret_file:
            entry += "    secret_file: tools/db-query-tool/appsettings.json\n"
            (tool / "appsettings.template.json").write_text(
                '{"ConnectionStrings":{"Connection":"Server=YOUR_SERVER;User ID=YOUR_USER;Password=YOUR_PASSWORD;"}}\n',
                encoding="utf-8")
        (root / "settings.yaml").write_text(f"{self.BASE}tools:\n  approved_custom_tool_runtimes: {runtimes}\n{entry}", encoding="utf-8")
        return root / "settings.yaml"

    def test_registered_tool_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run(VALIDATOR, self.workspace(temporary))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_settings_without_custom_tools_still_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".devbuddy"
            (root.parent / "repo").mkdir(parents=True)
            root.mkdir()
            (root / "settings.yaml").write_text(self.BASE, encoding="utf-8")
            result = run(VALIDATOR, root / "settings.yaml")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_unapproved_runtime_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run(VALIDATOR, self.workspace(temporary, runtimes="[python]"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approved_custom_tool_runtimes", result.stdout)

    def test_custom_tools_without_approved_runtimes_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            settings = self.workspace(temporary)
            text = "\n".join(line for line in settings.read_text(encoding="utf-8").splitlines()
                             if "approved_custom_tool_runtimes" not in line and line != "tools:")
            settings.write_text(text + "\n", encoding="utf-8")
            result = run(VALIDATOR, settings)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires tools.approved_custom_tool_runtimes", result.stdout)

    def test_missing_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            settings = self.workspace(temporary)
            (settings.parent / "tools" / "db-query-tool" / "tool.json").unlink()
            result = run(VALIDATOR, settings)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest not found", result.stdout)

    def test_unparseable_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run(VALIDATOR, self.workspace(temporary, manifest="{not json"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not valid JSON", result.stdout)

    def test_manifest_without_schemas_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            partial = json.dumps({"name": "readonly_database_query", "description": "d", "command": "./x"})
            result = run(VALIDATOR, self.workspace(temporary, manifest=partial))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest missing inputSchema", result.stdout)
            self.assertIn("manifest missing outputSchema", result.stdout)

    def test_credential_in_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            leaked = json.loads(MANIFEST.read_text(encoding="utf-8"))
            leaked["configuration"]["connectionString"] = "Server=db;User ID=sa;Password=hunter2;"
            result = run(VALIDATOR, self.workspace(temporary, manifest=json.dumps(leaked)))
            self.assertNotEqual(result.returncode, 0)
            # A manifest is committed by design, so a credential inside one has
            # already leaked; catching it at validation is the last cheap moment.
            self.assertIn("contains a credential", result.stdout)

    def test_secret_file_requires_a_committed_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            settings = self.workspace(temporary)
            (settings.parent / "tools" / "db-query-tool" / "appsettings.template.json").unlink()
            result = run(VALIDATOR, settings)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing committed template", result.stdout)


class BundledCustomToolTests(unittest.TestCase):
    """Custom tools bundled under `templates/project-tools/<name>/`.

    These ship inside the skill and install into `~/.claude`, so the thing worth
    asserting is what must never travel with them: a host's real configuration,
    and build output that a machine regenerates anyway.
    """

    TOOL = "db-query-tool"

    def source_files(self) -> list[Path]:
        """Source files of the bundled tool, excluding anything a build produces.

        An editor with C# support restores these projects as soon as it notices
        them, so `obj/` and `bin/` reappear in a developer's tree no matter how
        often they are deleted. That is why the guards that matter live on the
        install and seed paths, which decide what actually reaches a user; here
        we assert only that build output stays untracked and unshipped.
        """
        source = ROOT / "templates" / "project-tools" / self.TOOL
        self.assertTrue(source.is_dir(), f"missing bundled tool {self.TOOL}")
        return [p for p in sorted(source.rglob("*"))
                if p.is_file() and not set(p.relative_to(source).parts) & set(SKIP_DIRS)]

    def test_bundled_tool_carries_no_host_configuration(self) -> None:
        for path in self.source_files():
            self.assertNotIn(path.name, {"appsettings.json", "tool.json"}, f"host-owned file shipped: {path}")
        text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in self.source_files())
        # The committed template documents the shape; a real value would mean a
        # credential is now inside the skill and, once installed, inside ~/.claude.
        for placeholder in ("YOUR_SERVER", "YOUR_PASSWORD"):
            self.assertIn(placeholder, text)
        self.assertNotIn("BMS_DBDEV", text)

    def test_build_output_beside_a_bundled_tool_cannot_be_committed(self) -> None:
        source = ROOT / "templates" / "project-tools" / self.TOOL / self.TOOL
        for candidate in (source / "obj" / "project.assets.json", source / "bin" / "Debug" / "stale.dll"):
            checked = subprocess.run(["git", "check-ignore", "-q", str(candidate)],
                                     cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(checked.returncode, 0, f"build output is not git-ignored: {candidate}")

    def test_seeding_reproduces_the_buildable_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "repo").mkdir()
            root = base / ".devbuddy"
            result = run(INIT, "--devbuddy-root", root, "--project", f"app={base / 'repo'}",
                         "--seed-custom-tool", self.TOOL)
            self.assertEqual(result.returncode, 0, result.stdout)
            tool = root / "tools" / self.TOOL
            self.assertTrue((tool / "build-release.sh").is_file())
            self.assertTrue((tool / "appsettings.template.json").is_file())
            self.assertFalse((tool / "appsettings.json").exists())
            for path in tool.rglob("*"):
                self.assertFalse(set(path.relative_to(tool).parts) & set(SKIP_DIRS),
                                 f"build output seeded into the workspace: {path}")
            # The test project references ../db-query-tool/, so the two must stay
            # siblings under tools/ or the seeded copy will not build.
            reference = (root / "tools" / f"{self.TOOL}.tests").glob("*.csproj")
            csproj = next(reference)
            target = csproj.parent / next(
                part for part in csproj.read_text(encoding="utf-8").split('"') if part.endswith(".csproj")
            ).replace("\\", "/")
            self.assertTrue(target.resolve().is_file(), f"unresolved project reference: {target}")

    def test_seeding_is_dry_run_safe_and_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "repo").mkdir()
            root = base / ".devbuddy"
            dry = run(INIT, "--devbuddy-root", root, "--project", f"app={base / 'repo'}",
                      "--seed-custom-tool", self.TOOL, "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stdout)
            self.assertFalse(root.exists())
            self.assertEqual(run(INIT, "--devbuddy-root", root, "--project", f"app={base / 'repo'}",
                                 "--seed-custom-tool", self.TOOL).returncode, 0)
            again = run(INIT, "--devbuddy-root", root, "--seed-custom-tool", self.TOOL)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("refusing to overwrite existing custom tool", again.stdout)

    def test_unknown_bundled_tool_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "repo").mkdir()
            result = run(INIT, "--devbuddy-root", base / ".devbuddy", "--project", f"app={base / 'repo'}",
                         "--seed-custom-tool", "no-such-tool")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bundled custom tool not found", result.stdout)
            result = run(INIT, "--devbuddy-root", base / ".devbuddy", "--project", f"app={base / 'repo'}",
                         "--seed-custom-tool", "../escape")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid custom tool name", result.stdout)


class SkillMetadataTests(unittest.TestCase):
    """Guards on the frontmatter the whole dispatch contract depends on."""

    def skill_copy(self, temporary: str, frontmatter: str) -> Path:
        """A skill root whose SKILL.md carries the given frontmatter block."""
        root = Path(temporary) / "skill"
        root.mkdir()
        body = (ROOT / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[2]
        (root / "SKILL.md").write_text(f"---\n{frontmatter}---{body}", encoding="utf-8")
        return root

    def test_metadata_validator_exercises_task_memory(self) -> None:
        result = run(METADATA_VALIDATOR, ROOT, "--agents-dir", ROOT / "agents", "--exercise-task-memory")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_shipped_skill_disables_model_invocation(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", text.split("---", 2)[1])

    def test_validator_rejects_a_missing_invocation_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.skill_copy(temporary, "name: devbuddy\ndescription: run /devbuddy tasks\n")
            result = run(METADATA_VALIDATOR, root, "--agents-dir", ROOT / "agents")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("disable-model-invocation", result.stdout)

    def test_validator_rejects_a_disabled_invocation_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.skill_copy(
                temporary,
                "name: devbuddy\ndescription: run /devbuddy tasks\ndisable-model-invocation: false\n",
            )
            result = run(METADATA_VALIDATOR, root, "--agents-dir", ROOT / "agents")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be true", result.stdout)


class InstallerTests(unittest.TestCase):
    def install(self, temporary: str) -> Path:
        configured = Path(temporary) / "claude"
        result = run(INSTALLER, "--claude-root", configured, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout)
        return configured / "skills" / "devbuddy"

    def test_installed_payload_ships_only_self_contained_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            installed = self.install(temporary)
            # SKILL.md promises these run from an install, and only these. A
            # script that reaches for devbuddy-source-of-truth/ would hand the
            # user a command that cannot work once installed.
            self.assertEqual(
                sorted(path.name for path in (installed / "scripts").glob("*.py")),
                ["init_project_memory.py", "run_scenarios.py", "validate_skill_metadata.py"],
            )
            self.assertTrue((installed / "tests" / "scenarios.json").is_file())
            self.assertTrue((installed / "templates" / "project-tools" / "task_memory.py.template").is_file())
            bundled = installed / "templates" / "project-tools" / "db-query-tool"
            self.assertTrue((bundled / "db-query-tool" / "build-release.sh").is_file())
            self.assertFalse((bundled / "db-query-tool" / "appsettings.json").exists())
            source = Path(temporary) / "source"; source.mkdir()
            workspace = Path(temporary) / "workspace" / ".devbuddy"
            seeded = run(installed / "scripts" / "init_project_memory.py", "--devbuddy-root", workspace, "--project", f"app={source}")
            self.assertEqual(seeded.returncode, 0, seeded.stdout)
            self.assertTrue((workspace / "tools" / "task_memory.py").is_file())

    def test_documented_post_install_checks_run_from_the_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            installed = self.install(temporary)
            agents = installed.parents[1] / "agents"
            metadata = run(installed / "scripts" / "validate_skill_metadata.py", installed, "--agents-dir", agents)
            self.assertEqual(metadata.returncode, 0, metadata.stderr or metadata.stdout)
            scenarios = run(installed / "scripts" / "run_scenarios.py", installed / "tests" / "scenarios.json")
            self.assertEqual(scenarios.returncode, 0, scenarios.stderr or scenarios.stdout)

    def test_installer_skips_build_output_beside_a_bundled_tool(self) -> None:
        """A local build or an editor restore must not reach the user's config.

        Bundled custom tools are real projects, so `obj/` and `bin/` appear next
        to them as soon as anything touches them locally. The source tree is
        usually clean, so this plants the output rather than waiting for it.
        """
        bundled = ROOT / "templates" / "project-tools" / "db-query-tool" / "db-query-tool"
        planted = [bundled / "obj" / "project.assets.json", bundled / "bin" / "Debug" / "stale.dll"]
        created: list[Path] = []
        try:
            for path in planted:
                if not path.parent.exists():
                    created.append(path.parent)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("stale build output\n", encoding="utf-8")
            with tempfile.TemporaryDirectory() as temporary:
                installed = self.install(temporary)
                shipped = [p for p in installed.rglob("*") if p.is_file()]
                self.assertTrue(shipped)
                for path in shipped:
                    self.assertFalse({"obj", "bin"} & set(path.relative_to(installed).parts),
                                     f"build output installed: {path}")
        finally:
            for path in planted:
                path.unlink(missing_ok=True)
            for directory in sorted(created, key=lambda p: len(p.parts), reverse=True):
                for parent in (directory, *directory.parents):
                    if parent == bundled:
                        break
                    if parent.is_dir() and not any(parent.iterdir()):
                        parent.rmdir()

    def test_installer_is_dry_run_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            configured = Path(temporary) / "claude"
            result = run(INSTALLER, "--claude-root", configured)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertFalse((configured / "skills" / "devbuddy").exists())

    def test_installer_rejects_non_devbuddy_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "claude" / "skills" / "devbuddy"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("unrelated skill", encoding="utf-8")
            result = run(INSTALLER, "--claude-root", target.parents[1])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-DevBuddy", result.stdout)

    def test_installer_replaces_only_an_explicitly_recognized_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            configured = Path(temporary) / "claude"
            target = configured / "skills" / "devbuddy"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("---\nname: devbuddy\n---\nold DevBuddy skill\n", encoding="utf-8")
            (target / "roles").mkdir()
            (target / "roles" / "ba-pm.md").write_text("old custom content", encoding="utf-8")
            blocked = run(INSTALLER, "--claude-root", configured, "--apply")
            self.assertNotEqual(blocked.returncode, 0)
            replaced = run(INSTALLER, "--claude-root", configured, "--apply", "--replace-recognized-skill")
            self.assertEqual(replaced.returncode, 0, replaced.stderr or replaced.stdout)
            self.assertIn("BA/PM", (target / "roles" / "ba-pm.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
