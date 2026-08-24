#!/usr/bin/env python3
"""Run release evidence checks without mutating source or workspace state by default."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
NODE = shutil.which("node") or r"C:\Users\jenna\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
CHECKS = [
    ("package_validation", [PYTHON, "scripts/validate_packages.py"]),
    ("secret_exclusion", [PYTHON, "scripts/scan_secret_exclusion.py"]),
    ("source_preservation", [PYTHON, "scripts/check_source_preservation.py"]),
    ("package_drift", [PYTHON, "scripts/check_package_drift.py"]),
    ("architecture_tests", [PYTHON, "-m", "unittest", "discover", "tests", "-v"]),
    ("opencode_compatibility", [NODE, "tests/test_opencode_adapter.mjs"]),
    ("claude_plugin", [PYTHON, "scripts/validate_claude_plugin.py"]),
    ("codex_plugin", [PYTHON, "scripts/validate_codex_plugin.py"]),
    ("asset_ownership", [PYTHON, "scripts/inventory_plugin_assets.py"]),
    ("semantic_conformance", [PYTHON, "devbuddy-source-of-truth/scripts/check_semantic_conformance.py"]),
    ("skill_contract", [PYTHON, "devbuddy-source-of-truth/scripts/validate_skill_contract.py"]),
    ("claude_manual", [PYTHON, "devbuddy-claude/scripts/validate_manual.py", "devbuddy-claude/manual"]),
    ("codex_manual", [PYTHON, "devbuddy-codex/scripts/validate_manual.py", "devbuddy-codex/manual"]),
    ("database_build", ["dotnet", "build", "plugin/devbuddy-database-core/src/DevBuddy.Database.Policy/DevBuddy.Database.Policy.csproj", "--nologo"]),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", type=Path, help="write the JSON evidence report explicitly")
    args = parser.parse_args()
    checks = []
    for name, command in CHECKS:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        checks.append({"name": name, "passed": result.returncode == 0, "returncode": result.returncode, "output": (result.stdout + result.stderr)[-4000:]})
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip() or "uncommitted"
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "source_revision": revision, "passed": all(item["passed"] for item in checks), "checks": checks}
    print(json.dumps(report, indent=2))
    if args.write_report:
        target = args.write_report.resolve()
        try: target.relative_to(ROOT)
        except ValueError: print("ERROR: report path must stay inside the repository"); return 1
        target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {target}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
