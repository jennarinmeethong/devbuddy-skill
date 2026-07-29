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
KNOWLEDGE_VALIDATOR = ROOT / "scripts" / "validate_knowledge.py"
INSTALLER = ROOT / "scripts" / "install_codex_adapter.py"
VALIDATOR = ROOT / "scripts" / "validate_project_settings.py"
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


class SettingsValidatorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
