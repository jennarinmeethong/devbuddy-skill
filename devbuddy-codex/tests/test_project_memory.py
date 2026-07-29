#!/usr/bin/env python3
"""Regression tests for the Codex memory layout and settings validator."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_project_memory.py"
BOOTSTRAP = ROOT / "scripts" / "bootstrap_knowledge.py"
TASK_MEMORY = ROOT / "scripts" / "task_memory.py"
KNOWLEDGE_VALIDATOR = ROOT / "scripts" / "validate_knowledge.py"
INSTALLER = ROOT / "scripts" / "install_codex_adapter.py"
VALIDATOR = ROOT / "scripts" / "validate_project_settings.py"
METADATA_VALIDATOR = ROOT / "scripts" / "validate_skill_metadata.py"
VALID_SETTINGS = ROOT / "tests" / "fixtures" / "valid-settings.yaml"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(str(arg) for arg in args)],
        capture_output=True,
        text=True,
        check=False,
    )


class ProjectMemoryTests(unittest.TestCase):
    def test_project_root_is_wrapped_in_devbuddy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            result = run(INIT, "--project-root", project)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            memory = project / ".devbuddy"
            self.assertTrue((memory / "Context.md").is_file())
            self.assertTrue((memory / "tasks").is_dir())
            self.assertFalse((project / "Context.md").exists())

    def test_external_root_is_used_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            external = Path(temporary) / "vault"
            result = run(INIT, "--root", external)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue((external / "KnowledgeBase.md").is_file())
            self.assertFalse((external / ".devbuddy").exists())
            validated = run(KNOWLEDGE_VALIDATOR, "--root", external)
            self.assertEqual(validated.returncode, 0, validated.stderr or validated.stdout)

    def test_knowledge_validator_resolves_project_devbuddy_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            self.assertEqual(run(INIT, "--project-root", project).returncode, 0)
            result = run(KNOWLEDGE_VALIDATOR, "--project-root", project)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_knowledge_validator_rejects_invalid_entity_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            self.assertEqual(run(INIT, "--project-root", project).returncode, 0)
            entity = project / ".devbuddy" / "requirements" / "invalid.md"
            entity.write_text(
                "---\nid: BAD-001\ntype: requirement\nstatus: active\nowner: qa\n"
                "source: test\nlast_verified: 2026-07-27\nconfidence: verified\n---\n",
                encoding="utf-8",
            )
            result = run(KNOWLEDGE_VALIDATOR, "--project-root", project)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid knowledge id", result.stdout)

    def test_knowledge_validator_rejects_unresolved_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            self.assertEqual(run(INIT, "--project-root", project).returncode, 0)
            entity = project / ".devbuddy" / "requirements" / "requirement.md"
            entity.write_text(
                "---\nid: REQ-001\ntype: requirement\nstatus: active\nowner: owner\n"
                "source: test\nlast_verified: 2026-07-29\nconfidence: verified\n---\n"
                "<!-- devbuddy-ref: FEAT-missing -->\nSee [[API-missing]].\n",
                encoding="utf-8",
            )
            result = run(KNOWLEDGE_VALIDATOR, "--project-root", project)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unresolved devbuddy-ref FEAT-missing", result.stdout)
            self.assertIn("unresolved wiki-link API-missing", result.stdout)

    def test_bootstrap_dry_run_scans_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            (project / "package.json").write_text('{"scripts":{"test":"jest","build":"vite"}}', encoding="utf-8")
            result = run(BOOTSTRAP, "--project-root", project)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("FACT manifests: package.json", result.stdout)
            self.assertIn("DRY RUN", result.stdout)
            self.assertFalse((project / ".devbuddy").exists())

    def test_bootstrap_apply_writes_reviewable_core_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            (project / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
            result = run(BOOTSTRAP, "--project-root", project, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            context = project / ".devbuddy" / "Context.md"
            knowledge = project / ".devbuddy" / "KnowledgeBase.md"
            self.assertTrue(context.is_file())
            self.assertTrue(knowledge.is_file())
            self.assertIn("pyproject.toml", context.read_text(encoding="utf-8"))
            self.assertIn("pending user/role review", context.read_text(encoding="utf-8"))
            self.assertTrue((project / ".devbuddy" / "requirements").is_dir())
            self.assertTrue((project / ".devbuddy" / "tasks").is_dir())
            second = run(BOOTSTRAP, "--project-root", project, "--apply")
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stdout)

    def test_bootstrap_external_root_uses_source_root_without_nesting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            external = Path(temporary) / "vault"
            project.mkdir()
            (project / "package.json").write_text("{}", encoding="utf-8")
            result = run(BOOTSTRAP, "--root", external, "--source-root", project, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue((external / "Context.md").is_file())
            self.assertIn("package.json", (external / "Context.md").read_text(encoding="utf-8"))
            self.assertFalse((external / ".devbuddy").exists())

    def test_initializer_refuses_to_overwrite_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            first = run(INIT, "--project-root", project)
            second = run(INIT, "--project-root", project)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stdout)

    def test_task_memory_reuses_task_id_and_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            self.assertEqual(run(INIT, "--project-root", project).returncode, 0)
            first = run(TASK_MEMORY, "init", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--session-id", "s1")
            second = run(TASK_MEMORY, "init", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--session-id", "s2")
            self.assertEqual(first.returncode, 0, first.stdout)
            self.assertEqual(second.returncode, 0, second.stdout)
            ledger = project / ".devbuddy" / "tasks" / "demo" / "task-001.md"
            self.assertIn("- s2", ledger.read_text(encoding="utf-8"))
            escaped = run(TASK_MEMORY, "init", "--project-root", project, "--project-id", "../bad", "--task-id", "001")
            self.assertNotEqual(escaped.returncode, 0)

    def test_task_memory_persists_handoff_for_next_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            self.assertEqual(run(INIT, "--project-root", project).returncode, 0)
            self.assertEqual(run(TASK_MEMORY, "init", "--project-root", project, "--project-id", "demo", "--task-id", "001").returncode, 0)
            source = Path(temporary) / "handoff.md"
            source.write_text(
                "# Handoff\n\n- Task ID: 001\n- Slice ID / attempt: developer / 1\n"
                "- Parent handoff / revision: none / 0\n- Status: `completed`\n",
                encoding="utf-8",
            )
            result = run(TASK_MEMORY, "handoff", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--slice-id", "developer", "--attempt", "1", "--parent-revision", "0", "--input", source)
            self.assertEqual(result.returncode, 0, result.stdout)
            target = project / ".devbuddy" / "tasks" / "demo" / "task-001" / "handoffs" / "developer-1.md"
            self.assertEqual(target.read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))

    def test_task_memory_blocks_stale_revision_and_enforces_owner_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            self.assertEqual(run(INIT, "--project-root", project).returncode, 0)
            self.assertEqual(run(TASK_MEMORY, "init", "--project-root", project, "--project-id", "demo", "--task-id", "001").returncode, 0)
            committed = run(TASK_MEMORY, "commit", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--actor", "owner", "--expected-revision", "0", "--summary", "approved canonical update")
            self.assertEqual(committed.returncode, 0, committed.stdout)
            stale = run(TASK_MEMORY, "reserve", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--actor", "developer", "--scope", "src", "--expected-revision", "0")
            self.assertNotEqual(stale.returncode, 0)
            non_owner = run(TASK_MEMORY, "commit", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--actor", "developer", "--expected-revision", "1", "--summary", "must fail")
            self.assertNotEqual(non_owner.returncode, 0)
            ledger = project / ".devbuddy" / "tasks" / "demo" / "task-001.md"
            self.assertIn("- Memory revision: 1", ledger.read_text(encoding="utf-8"))

    def test_task_memory_reservation_scope_and_readonly_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            (project / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
            self.assertEqual(run(INIT, "--project-root", project).returncode, 0)
            self.assertEqual(run(TASK_MEMORY, "init", "--project-root", project, "--project-id", "demo", "--task-id", "001").returncode, 0)
            reserved = run(TASK_MEMORY, "reserve", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--actor", "developer", "--scope", "src", "--expected-revision", "0")
            self.assertEqual(reserved.returncode, 0, reserved.stdout)
            conflict = run(TASK_MEMORY, "reserve", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--actor", "qa", "--scope", "src", "--expected-revision", "0")
            self.assertNotEqual(conflict.returncode, 0)
            scope = run(TASK_MEMORY, "check-scope", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--write-scope", "src", "--changed", ".devbuddy/Context.md")
            self.assertNotEqual(scope.returncode, 0)
            analysis = run(TASK_MEMORY, "analyze", "--project-root", project, "--project-id", "demo", "--task-id", "001", "--source-root", project)
            self.assertEqual(analysis.returncode, 0, analysis.stdout)
            report = project / ".devbuddy" / "tasks" / "demo" / "task-001" / "analysis.md"
            self.assertIn("package.json", report.read_text(encoding="utf-8"))


class SettingsValidatorTests(unittest.TestCase):
    def test_metadata_validator_exercises_task_memory(self) -> None:
        result = run(METADATA_VALIDATOR, ROOT, "--exercise-task-memory")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_valid_project_settings_pass(self) -> None:
        result = run(VALIDATOR, VALID_SETTINGS)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_empty_memory_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "settings.yaml"
            content = VALID_SETTINGS.read_text(encoding="utf-8").replace("memory_root: .devbuddy", "memory_root:")
            invalid.write_text(content, encoding="utf-8")
            result = run(VALIDATOR, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("memory_root", result.stdout)

    def test_duplicate_model_rank_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "settings.yaml"
            content = VALID_SETTINGS.read_text(encoding="utf-8").replace("      rank: 2", "      rank: 1", 1)
            invalid.write_text(content, encoding="utf-8")
            result = run(VALIDATOR, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate rank", result.stdout)


class InstallerTests(unittest.TestCase):
    def test_installer_is_dry_run_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            codex_root = Path(temporary) / "codex"
            result = run(INSTALLER, "--codex-root", codex_root)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertFalse((codex_root / "skills" / "devbuddy").exists())

    def test_installer_applies_to_configured_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            codex_root = Path(temporary) / "codex"
            result = run(INSTALLER, "--codex-root", codex_root, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue((codex_root / "skills" / "devbuddy" / "SKILL.md").is_file())

    def test_installer_rejects_non_devbuddy_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "codex" / "skills" / "devbuddy"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("unrelated skill", encoding="utf-8")
            result = run(INSTALLER, "--codex-root", target.parents[1])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-DevBuddy", result.stdout)

    def test_installer_replaces_only_an_explicitly_recognized_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "codex"
            target = root / "skills" / "devbuddy"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("---\nname: devbuddy\n---\nold DevBuddy skill\n", encoding="utf-8")
            (target / "roles").mkdir()
            (target / "roles" / "ba-pm.md").write_text("old custom content", encoding="utf-8")
            blocked = run(INSTALLER, "--codex-root", root, "--apply")
            self.assertNotEqual(blocked.returncode, 0)
            replaced = run(INSTALLER, "--codex-root", root, "--apply", "--replace-recognized-skill")
            self.assertEqual(replaced.returncode, 0, replaced.stderr or replaced.stdout)
            self.assertIn("BA/PM", (target / "roles" / "ba-pm.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
