"""Black-box tests for the Plugin-first Claude Code migration path."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(*parts: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PYTHON, *parts], cwd=ROOT, capture_output=True, text=True, check=False)


class ClaudePluginMigrationTests(unittest.TestCase):
    def test_plugin_layout_and_discovery_are_valid(self) -> None:
        result = run("scripts/validate_claude_plugin.py")
        self.assertEqual(result.returncode, 0, result.stdout)
        discovery = json.loads(result.stdout)
        self.assertEqual(discovery["entrypoint"], "/devbuddy-claude-code:devbuddy")
        self.assertEqual(len(discovery["discovery"]["agents"]), 54)

    def test_claude_profile_selects_only_the_claude_adapter(self) -> None:
        result = run("scripts/profile_resolver.py", "profiles/claude-code.yaml", "--platform", "claude-code")
        self.assertEqual(result.returncode, 0, result.stdout)
        resolution = json.loads(result.stdout.split("\nDRY RUN:", 1)[0])
        self.assertEqual(resolution["packages"], ["devbuddy-core", "devbuddy-claude-code"])
        self.assertEqual(resolution["profile_hosts"], ["claude-code"])

    def test_legacy_installer_previews_migration_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            claude_root = Path(temporary) / ".claude"
            result = run("devbuddy-claude/scripts/install_claude_adapter.py", "--claude-root", str(claude_root))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertFalse(claude_root.exists())
            report = json.loads(result.stdout.split("\nDRY RUN:", 1)[0])
            self.assertEqual(report["entrypoint"], "/devbuddy-claude-code:devbuddy")

    def test_legacy_installer_requires_explicit_compatibility_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            claude_root = Path(temporary) / ".claude"
            result = run("devbuddy-claude/scripts/install_claude_adapter.py", "--claude-root", str(claude_root), "--legacy-install", "--apply")
            self.assertEqual(result.returncode, 0, result.stdout)
            skill = claude_root / "skills" / "devbuddy" / "SKILL.md"
            self.assertTrue(skill.is_file())
            self.assertIn("migration-only", skill.read_text(encoding="utf-8"))
            self.assertFalse((claude_root / "agents").exists())

    def test_legacy_installer_refuses_unknown_file_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            claude_root = Path(temporary) / ".claude"
            target = claude_root / "skills" / "devbuddy"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("unrelated user content\n", encoding="utf-8")
            result = run("devbuddy-claude/scripts/install_claude_adapter.py", "--claude-root", str(claude_root), "--legacy-install", "--apply")
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "unrelated user content\n")

    def test_codex_legacy_shim_previews_and_retains_rollback_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".codex"
            result = run("devbuddy-codex/scripts/install_codex_adapter.py", "--codex-root", str(root))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertFalse(root.exists())
            report = json.loads(result.stdout.split("\nDRY RUN:", 1)[0])
            self.assertTrue(report["migration_record"]["reversible"])
            self.assertIn("Plugin/profile", report["rollback"])

    def test_codex_plugin_layout_and_profile_are_valid(self) -> None:
        result = run("scripts/validate_codex_plugin.py")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["entrypoint"], "$devbuddy")
        result = run("scripts/profile_resolver.py", "profiles/codex.yaml", "--platform", "codex")
        self.assertEqual(result.returncode, 0, result.stdout)
        resolution = json.loads(result.stdout.split("\nDRY RUN:", 1)[0])
        self.assertEqual(resolution["packages"], ["devbuddy-core", "devbuddy-codex"])

    def test_codex_legacy_shim_requires_opt_in_and_refuses_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".codex"
            target = root / "skills" / "devbuddy"; target.mkdir(parents=True)
            (target / "SKILL.md").write_text("unrelated user content\n", encoding="utf-8")
            result = run("devbuddy-codex/scripts/install_codex_adapter.py", "--codex-root", str(root), "--legacy-install", "--apply")
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "unrelated user content\n")

    def test_asset_inventory_is_complete_and_dry_run_first(self) -> None:
        result = run("scripts/inventory_plugin_assets.py")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertGreater(json.loads(result.stdout)["asset_count"], 0)


if __name__ == "__main__":
    unittest.main()
