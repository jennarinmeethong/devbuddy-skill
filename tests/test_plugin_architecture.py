#!/usr/bin/env python3
"""Regression coverage for the additive plugin architecture."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PYTHON, str(ROOT / "scripts" / script), *args], cwd=ROOT, capture_output=True, text=True, check=False)


class PluginArchitectureTests(unittest.TestCase):
    def test_source_preservation_and_generated_skills(self) -> None:
        self.assertEqual(run("check_source_preservation.py").returncode, 0)
        self.assertEqual(run("check_package_drift.py").returncode, 0)
        self.assertEqual(run("validate_packages.py").returncode, 0)
        self.assertEqual(run("scan_secret_exclusion.py").returncode, 0)
        generated = ROOT / "plugin" / "devbuddy-core" / "skills" / "devbuddy-core" / ".devbuddy-generation.json"
        self.assertTrue(generated.is_file())
        self.assertEqual(json.loads(generated.read_text(encoding="utf-8"))["provenance"], "skills/devbuddy-core")

    def test_database_skill_is_policy_only_and_requires_plugin_owned_adapter(self) -> None:
        skill = (ROOT / "skills" / "devbuddy-database" / "SKILL.md").read_text(encoding="utf-8")
        core = (ROOT / "skills" / "devbuddy-core" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("This skill is policy only", skill)
        self.assertIn("devbuddy-database-core", skill)
        self.assertIn("do not fall back to a workspace custom", skill)
        self.assertIn("never ships, selects, or invokes a database executable", core)

    def test_packaged_hosts_exclude_the_retired_database_tool_from_guidance(self) -> None:
        for host in ("devbuddy-codex", "devbuddy-claude-code"):
            with self.subTest(host=host):
                reference = (ROOT / "plugin" / host / "references" / "settings.md").read_text(encoding="utf-8")
                self.assertIn("register_database_adapter.py", reference)
                self.assertIn("must not be invoked", reference)
                self.assertNotIn("manifest: tools/db-query-tool/tool.json", reference)
                self.assertTrue((ROOT / "plugin" / host / "scripts" / "migration_report.py").is_file())
                self.assertTrue((ROOT / "plugin" / host / "scripts" / "register_database_adapter.py").is_file())

    def test_profile_resolution_is_deterministic_and_non_mutating(self) -> None:
        result = run("profile_resolver.py", "profiles/data-postgresql.yaml")
        self.assertEqual(result.returncode, 0, result.stdout)
        data = json.loads(result.stdout.split("\nDRY RUN:", 1)[0])
        self.assertEqual(data["packages"], ["devbuddy-core", "devbuddy-database-core", "devbuddy-database-postgresql"])
        self.assertIn("tier-2-database", data["permissions"])

    def test_database_profiles_support_every_host_platform(self) -> None:
        profiles = [ROOT / "profiles" / f"data-{engine}.yaml" for engine in ("sqlserver", "postgresql", "mariadb", "oracle", "mongodb", "redis")]
        for profile in profiles:
            for platform in ("codex", "claude-code", "opencode"):
                with self.subTest(profile=profile.name, platform=platform):
                    result = run("profile_resolver.py", str(profile), "--platform", platform)
                    self.assertEqual(result.returncode, 0, result.stdout)

    def test_every_profile_resolves_and_apply_reports_changes(self) -> None:
        for profile in (ROOT / "profiles").glob("*.yaml"):
            self.assertEqual(run("profile_resolver.py", str(profile)).returncode, 0, profile)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".devbuddy"
            applied = run("profile_resolver.py", "profiles/minimal.yaml", "--devbuddy-root", str(root), "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            state = json.loads((root / "packages.json").read_text(encoding="utf-8"))
            self.assertEqual(state["changes"]["add"], ["devbuddy-core"])
            removed = run("profile_resolver.py", "profiles/minimal.yaml", "--devbuddy-root", str(root), "--operation", "uninstall", "--apply")
            self.assertEqual(removed.returncode, 0, removed.stdout)
            self.assertEqual(json.loads((root / "packages.json").read_text(encoding="utf-8"))["packages"], [])

    def test_profile_composition_can_add_and_remove_presets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".devbuddy"
            initial = run("profile_resolver.py", "product-delivery", "--devbuddy-root", str(root), "--apply")
            self.assertEqual(initial.returncode, 0, initial.stdout)
            added = run("profile_resolver.py", "--add-profile", "data-ai", "--devbuddy-root", str(root), "--apply")
            self.assertEqual(added.returncode, 0, added.stdout)
            state = json.loads((root / "packages.json").read_text(encoding="utf-8"))
            self.assertEqual(state["profiles"], ["product-delivery", "data-ai"])
            self.assertIn("model-evaluator", state["agent_roles"])
            removed = run("profile_resolver.py", "--remove-profile", "data-ai", "--devbuddy-root", str(root), "--apply")
            self.assertEqual(removed.returncode, 0, removed.stdout)
            state = json.loads((root / "packages.json").read_text(encoding="utf-8"))
            self.assertEqual(state["profiles"], ["product-delivery"])
            self.assertNotIn("model-evaluator", state["agent_roles"])

    def test_profile_composition_preserves_the_active_host(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".devbuddy"
            initial = run("profile_resolver.py", "opencode", "--devbuddy-root", str(root), "--apply")
            self.assertEqual(initial.returncode, 0, initial.stdout)
            added = run("profile_resolver.py", "--add-profile", "cloud-operations", "--devbuddy-root", str(root), "--apply")
            self.assertEqual(added.returncode, 0, added.stdout)
            state = json.loads((root / "packages.json").read_text(encoding="utf-8"))
            self.assertEqual(state["platform"], "opencode")

    def test_workspace_requires_apply_and_does_not_store_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"
            preview = run("workspace.py", "init", "--devbuddy-root", str(workspace))
            self.assertEqual(preview.returncode, 0, preview.stdout)
            self.assertFalse(workspace.exists())
            applied = run("workspace.py", "init", "--devbuddy-root", str(workspace), "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            self.assertEqual(run("workspace.py", "validate", "--devbuddy-root", str(workspace)).returncode, 0)
            settings = workspace / "settings.yaml"
            settings.write_text(settings.read_text(encoding="utf-8") + "password: leaked\n", encoding="utf-8")
            self.assertNotEqual(run("workspace.py", "validate", "--devbuddy-root", str(workspace)).returncode, 0)

    def test_workspace_database_registry_requires_local_secret_and_production_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"
            self.assertEqual(run("workspace.py", "init", "--devbuddy-root", str(workspace), "--apply").returncode, 0)
            settings = workspace / "settings.yaml"
            settings.write_text(settings.read_text(encoding="utf-8").replace("databases: []", """databases:
  - id: billing-prod
    engine: postgresql
    environment: production
    adapter_package: devbuddy-database-postgresql
    manifest: tools/databases/billing-prod/tool.json
    secret_file: tools/databases/billing-prod/appsettings.json
    approval: allow
    max_rows: 500
    timeout_seconds: 30"""), encoding="utf-8")
            self.assertNotEqual(run("workspace.py", "validate", "--devbuddy-root", str(workspace)).returncode, 0)
            database_dir = workspace / "tools" / "databases" / "billing-prod"; database_dir.mkdir()
            (database_dir / "tool.json").write_text("{}", encoding="utf-8")
            (database_dir / "appsettings.json").write_text("{}", encoding="utf-8")
            settings.write_text(settings.read_text(encoding="utf-8").replace("approval: allow", "approval: ask"), encoding="utf-8")
            self.assertEqual(run("workspace.py", "validate", "--devbuddy-root", str(workspace)).returncode, 0)

    def test_database_connection_templates_are_parseable_and_use_placeholders(self) -> None:
        engines = ("sqlserver", "postgresql", "mariadb", "oracle", "mongodb", "redis")
        for engine in engines:
            template = ROOT / "plugin" / f"devbuddy-database-{engine}" / "appsettings.template.json"
            data = json.loads(template.read_text(encoding="utf-8"))
            connection = data["ConnectionStrings"]["Connection"]
            self.assertIn("__LOCAL_SECRET__", connection, engine)
            self.assertIn("_instructions", data, engine)

    def test_plugin_build_is_dry_run_by_default(self) -> None:
        result = run("build_plugin.py", "--runtime", "win-x64")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DRY RUN", result.stdout)

    def test_database_materializer_is_explicit_and_dry_run_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"
            self.assertEqual(run("workspace.py", "init", "--devbuddy-root", str(workspace), "--apply").returncode, 0)
            result = run(
                "materialize_database_adapter.py", "--devbuddy-root", str(workspace),
                "--database-id", "billing", "--engine", "postgresql", "--runtime", "linux-x64",
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("DRY RUN", result.stdout)
            self.assertFalse((workspace / "tools" / "databases" / "billing").exists())

    def test_legacy_database_tool_retirement_is_dry_run_first_and_reversible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"
            self.assertEqual(run("workspace.py", "init", "--devbuddy-root", str(workspace), "--apply").returncode, 0)
            settings = workspace / "settings.yaml"
            settings.write_text(settings.read_text(encoding="utf-8") + """custom_tools:
  - name: readonly_database_query
    runtime: dotnet
    manifest: tools/db-query-tool/tool.json
    secret_file: tools/db-query-tool/appsettings.json
""", encoding="utf-8")
            legacy_tool = workspace / "tools" / "db-query-tool"
            legacy_tool.mkdir()
            (legacy_tool / "tool.json").write_text("{}\n", encoding="utf-8")
            preview = run("migrate_legacy_database_tools.py", "--devbuddy-root", str(workspace))
            self.assertEqual(preview.returncode, 0, preview.stdout)
            self.assertIn("DRY RUN", preview.stdout)
            self.assertTrue(legacy_tool.is_dir())
            applied = run("migrate_legacy_database_tools.py", "--devbuddy-root", str(workspace), "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            self.assertFalse(legacy_tool.exists())
            self.assertIn("custom_tools: []", settings.read_text(encoding="utf-8"))
            backups = list((workspace / "backups" / "legacy-database-tools").glob("*/db-query-tool/tool.json"))
            self.assertEqual(len(backups), 1)

    def test_plugin_generated_knowledge_keys_are_collision_resistant(self) -> None:
        first = run("new_knowledge_key.py", "--prefix", "inc")
        second = run("new_knowledge_key.py", "--prefix", "INC")
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertRegex(first.stdout.strip(), r"^INC-\d{8}T\d{6}Z-[0-9A-F]{32}$")
        self.assertNotEqual(first.stdout, second.stdout)

    def test_profile_catalog_and_migration_report_are_read_only(self) -> None:
        catalog = run("profile_resolver.py", "--list")
        self.assertEqual(catalog.returncode, 0, catalog.stdout)
        self.assertIn("data-mariadb", catalog.stdout)
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"
            self.assertEqual(run("workspace.py", "init", "--devbuddy-root", str(workspace), "--apply").returncode, 0)
            (workspace / "BusinessContext.md").write_text("legacy\n", encoding="utf-8")
            report = run("migration_report.py", "--devbuddy-root", str(workspace))
            self.assertEqual(report.returncode, 0, report.stdout)
            self.assertIn("BusinessContext.md", report.stdout)
            self.assertTrue((workspace / "BusinessContext.md").is_file())

    def test_database_registration_requires_materialized_adapter_and_is_dry_run_first(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"
            self.assertEqual(run("workspace.py", "init", "--devbuddy-root", str(workspace), "--apply").returncode, 0)
            adapter = workspace / "tools" / "databases" / "billing"; adapter.mkdir(parents=True)
            (adapter / "tool.json").write_text("{}\n", encoding="utf-8")
            preview = run("register_database_adapter.py", "--devbuddy-root", str(workspace), "--database-id", "billing", "--engine", "postgresql")
            self.assertEqual(preview.returncode, 0, preview.stdout)
            self.assertIn("DRY RUN", preview.stdout)
            applied = run("register_database_adapter.py", "--devbuddy-root", str(workspace), "--database-id", "billing", "--engine", "postgresql", "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            self.assertIn("adapter_package: devbuddy-database-postgresql", (workspace / "settings.yaml").read_text(encoding="utf-8"))

    def test_legacy_host_skill_retirement_is_dry_run_first_and_reversible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            host = Path(temporary) / ".claude"
            skill = host / "skills" / "devbuddy"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# DevBuddy legacy\n", encoding="utf-8")
            agent = host / "agents" / "devbuddy-qa-low.md"
            agent.parent.mkdir()
            agent.write_text("DevBuddy legacy agent\n", encoding="utf-8")
            preview = run("retire_legacy_host_skill.py", "--host", "claude-code", "--host-root", str(host))
            self.assertEqual(preview.returncode, 0, preview.stdout)
            self.assertIn("DRY RUN", preview.stdout)
            self.assertTrue(skill.exists())
            applied = run("retire_legacy_host_skill.py", "--host", "claude-code", "--host-root", str(host), "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            self.assertFalse(skill.exists())
            backups = list((host / "backups" / "devbuddy-legacy-host").glob("*/skills/devbuddy/SKILL.md"))
            self.assertEqual(len(backups), 1)

    def test_workspace_upgrade_and_migration_are_dry_run_first_and_conflict_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"; workspace.mkdir()
            (workspace / "settings.yaml").write_text("schema_version: 1\nworkspace_schema_version: 1\n", encoding="utf-8")
            (workspace / "Context.md").write_text("legacy\n", encoding="utf-8")
            preview = run("workspace.py", "migrate", "--devbuddy-root", str(workspace))
            self.assertEqual(preview.returncode, 0, preview.stdout)
            self.assertTrue((workspace / "Context.md").is_file())
            applied = run("workspace.py", "migrate", "--devbuddy-root", str(workspace), "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout)
            self.assertEqual((workspace / "knowledge-base" / "Context.md").read_text(encoding="utf-8"), "legacy\n")
            upgraded = run("workspace.py", "upgrade", "--devbuddy-root", str(workspace), "--apply")
            self.assertEqual(upgraded.returncode, 0, upgraded.stdout)
            self.assertIn("plugin_version: 1.0.0", (workspace / "settings.yaml").read_text(encoding="utf-8"))

    def test_portable_task_lifecycle_requires_evidence_for_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / ".devbuddy"
            created = run("task_lifecycle.py", "init", "--devbuddy-root", str(workspace), "--task-id", "task-1", "--operation", "review", "--risk", "low", "--scope", "src", "--tier", "0", "--apply")
            self.assertEqual(created.returncode, 0, created.stdout)
            running = run("task_lifecycle.py", "transition", "--devbuddy-root", str(workspace), "--task-id", "task-1", "--state", "running", "--apply")
            self.assertEqual(running.returncode, 0, running.stdout)
            blocked_completion = run("task_lifecycle.py", "transition", "--devbuddy-root", str(workspace), "--task-id", "task-1", "--state", "completed", "--apply")
            self.assertNotEqual(blocked_completion.returncode, 0)
            completed = run("task_lifecycle.py", "transition", "--devbuddy-root", str(workspace), "--task-id", "task-1", "--state", "completed", "--evidence", "tests", "--closure", "tests=passed", "--apply")
            self.assertEqual(completed.returncode, 0, completed.stdout)
            record = workspace / "tasks" / "task-1" / "task.json"
            self.assertEqual(run("validate_task_contract.py", str(record)).returncode, 0)

    def test_database_gate_rejects_writes_and_redis_escape(self) -> None:
        limits = '"max_rows":500,"max_result_bytes":1048576,"timeout_seconds":30'
        allowed = run("validate_database_request.py", "postgresql", '{"database_id":"billing",' + limits + ',"sql":"SELECT id FROM reporting.invoice"}')
        self.assertEqual(allowed.returncode, 0, allowed.stdout)
        denied = run("validate_database_request.py", "postgresql", '{"database_id":"billing",' + limits + ',"sql":"UPDATE invoice SET status=1"}')
        self.assertNotEqual(denied.returncode, 0)
        redis = run("validate_database_request.py", "redis", '{"database_id":"cache",' + limits + ',"command":"GET","key":"other:x","key_prefix":"app:"}')
        self.assertNotEqual(redis.returncode, 0)

    def test_tier_two_approval_is_bound_to_operation_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / ".devbuddy"; root.mkdir()
            manifest = ROOT / "plugin" / "devbuddy-database-postgresql" / "tool.json"
            approval = Path(temporary) / "approval.json"
            target = "billing-prod"
            denied = run("authorize_operation.py", "--manifest", str(manifest), "--operation", "query", "--target", target, "--devbuddy-root", str(root))
            self.assertNotEqual(denied.returncode, 0)
            approval.write_text(json.dumps({"manifest_id": "devbuddy.database.postgresql.read", "operation": "query", "target": target, "approved": True}), encoding="utf-8")
            allowed = run("authorize_operation.py", "--manifest", str(manifest), "--operation", "query", "--target", target, "--devbuddy-root", str(root), "--approval", str(approval))
            self.assertEqual(allowed.returncode, 0, allowed.stdout)

    def test_dotnet_adapter_rejects_unsafe_sql_before_opening_connection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            request = Path(temporary) / "request.json"
            request.write_text(json.dumps({"database_id": "billing", "sql": "DELETE FROM invoice", "max_rows": 10, "max_result_bytes": 1024, "timeout_seconds": 5}), encoding="utf-8")
            project = ROOT / "plugin" / "devbuddy-database-core" / "src" / "DevBuddy.Database.Policy" / "DevBuddy.Database.Policy.csproj"
            result = subprocess.run(["dotnet", "run", "--no-build", "--project", str(project), "--", "--engine", "postgresql", "--request", str(request), "--config", str(Path(temporary) / "missing.json")], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("policy_rejected", result.stdout)


if __name__ == "__main__":
    unittest.main()
