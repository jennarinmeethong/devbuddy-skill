#!/usr/bin/env python3
"""Regression tests for the common memory layout and settings validator."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_project_memory.py"
KNOWLEDGE_VALIDATOR = ROOT / "scripts" / "validate_knowledge.py"
VALIDATOR = ROOT / "scripts" / "validate_settings.py"
SETTINGS = ROOT / "settings.yaml"


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

    def test_initializer_refuses_to_overwrite_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            first = run(INIT, "--project-root", project)
            second = run(INIT, "--project-root", project)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stdout)


class SettingsValidatorTests(unittest.TestCase):
    def test_shipped_settings_validate(self) -> None:
        result = run(VALIDATOR, SETTINGS)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_missing_common_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "settings.yaml"
            invalid.write_text(SETTINGS.read_text(encoding="utf-8").replace("quality:\n", ""), encoding="utf-8")
            result = run(VALIDATOR, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("quality", result.stdout)

    def test_noncanonical_memory_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "settings.yaml"
            content = SETTINGS.read_text(encoding="utf-8").replace("  default_root: .devbuddy", "  default_root: memory")
            invalid.write_text(content, encoding="utf-8")
            result = run(VALIDATOR, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("memory.default_root", result.stdout)


if __name__ == "__main__":
    unittest.main()
