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
VALIDATOR = ROOT / "scripts" / "validate_settings.py"
PROJECT_SETTINGS_VALIDATOR = ROOT / "scripts" / "validate_project_settings.py"
SETTINGS = ROOT / "settings.yaml"


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
            self.assertIn("max_concurrency: 2", settings)
            self.assertIn("task_timeout_seconds: 900", settings)
            self.assertIn("retry_limit: 1", settings)

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

    def test_json_slice_record_is_validated_without_a_file_size_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            created = run(TASK, "init", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001")
            self.assertEqual(created.returncode, 0, created.stdout)
            inbox = root / "tasks" / "task-001" / "inbox"; inbox.mkdir()
            record = inbox / "developer-1.json"
            payload = {"schema_version": 1, "task_id": "001", "slice_id": "developer", "attempt": 1, "parent_revision": 0,
                       "role": "developer", "model": "test-model", "effort": "low", "status": "completed", "result": "x" * 1_501,
                       "evidence": [{"ref": "tests/unit", "outcome": "passed"}], "next_slice": {"summary": "Run focused unit test.", "read_paths": ["fe:tests/unit"], "read_keys": []},
                       "knowledge_keys": [], "knowledge_proposal": None, "blockers": [], "required_approval": None}
            record.write_text(json.dumps(payload), encoding="utf-8")
            accepted = run(TASK, "record", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                           "--slice-id", "developer", "--attempt", "1", "--parent-revision", "0", "--input", record)
            self.assertEqual(accepted.returncode, 0, accepted.stdout)
            target = root / "tasks" / "task-001" / "records" / "developer-1.json"
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), payload)
            payload["task_id"] = "wrong-task"
            record.write_text(json.dumps(payload), encoding="utf-8")
            mismatched = run(TASK, "record", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                             "--slice-id", "developer", "--attempt", "1", "--parent-revision", "0", "--input", record)
            self.assertNotEqual(mismatched.returncode, 0)
            self.assertIn("record identity must match", mismatched.stdout)
            payload["task_id"] = "001"
            payload["evidence"] = [{"ref": f"tests/case-{index}", "outcome": "x" * 500} for index in range(16)]
            record.write_text(json.dumps(payload), encoding="utf-8")
            self.assertGreater(len(record.read_bytes()), 4_000)
            accepted_large = run(TASK, "record", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                                 "--slice-id", "developer", "--attempt", "1", "--parent-revision", "0", "--input", record)
            self.assertEqual(accepted_large.returncode, 0, accepted_large.stdout)

    def test_record_input_outside_devbuddy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _frontend, _backend = self.make_workspace(temporary)
            created = run(TASK, "init", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001")
            self.assertEqual(created.returncode, 0, created.stdout)
            record = Path(temporary) / "record.json"
            record.write_text("{}", encoding="utf-8")
            result = run(TASK, "record", "--devbuddy-root", root, "--project-id", "fe", "--task-id", "001",
                         "--slice-id", "developer", "--attempt", "1", "--parent-revision", "0", "--input", record)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("record input must be below", result.stdout)


class SettingsValidatorTests(unittest.TestCase):
    def test_shipped_settings_validate(self) -> None:
        result = run(VALIDATOR, SETTINGS)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_shared_adapter_profiles_validate_without_a_toggle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = base / "project"; project.mkdir()
            settings = base / ".devbuddy" / "settings.yaml"; settings.parent.mkdir()
            settings.write_text(
                "schema_version: 1\nsettings_version: 0.4.6\nworkspace:\n  projects:\n    app:\n      path: project\n"
                "memory_root: knowledge-base\norchestration:\n  max_concurrency: 1\n  task_timeout_seconds: 60\n"
                "  retry_limit: 0\n  adapter_profiles: [claude, codex]\n  approved_models:\n"
                "    - id: claude-fast\n      adapters: [claude]\n      rank: 1\n      allowed_roles: [developer]\n      allowed_risks: [low]\n"
                "    - id: codex-fast\n      adapters: [codex]\n      rank: 1\n      allowed_roles: [developer]\n      allowed_risks: [low]\n"
                "  approved_effort_levels:\n    - id: low\n      adapters: [claude, codex]\n      rank: 1\n"
                "      allowed_roles: [developer]\n      allowed_risks: [low]\n",
                encoding="utf-8",
            )
            result = run(PROJECT_SETTINGS_VALIDATOR, settings)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
