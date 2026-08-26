#!/usr/bin/env python3
"""Validate the self-contained Claude Code Plugin payload without a host write.

This is the host-discovery evidence used in CI when Claude Code itself is not
installed. It verifies the official on-disk Plugin layout and prints the
components that Claude Code discovers after ``/reload-plugins``.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin" / "devbuddy-claude-code"
NAME = "devbuddy-claude-code"
AGENT = re.compile(r"^devbuddy-[a-z-]+-(low|medium|high|extra|max|ultracode)\.md$")
RUNTIME_FILES = (
    "settings.yaml", "references/policy.md", "references/claude-dispatch.md",
    "schemas/slice-record.schema.json", "templates/task-ledger.md",
    "scripts/init_project_memory.py", "scripts/validate_skill_metadata.py",
    "scripts/run_scenarios.py", "tests/scenarios.json",
)
MAINTENANCE_FILES = ("scripts/generate_agents.py", "scripts/check_adapter_conformance.py", "scripts/install_claude_adapter.py")


def main() -> int:
    errors: list[str] = []
    manifest_path = PLUGIN / ".claude-plugin" / "plugin.json"
    skill = PLUGIN / "skills" / "devbuddy" / "SKILL.md"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: invalid Claude Plugin manifest: {error}")
        return 1
    if manifest.get("name") != NAME or not isinstance(manifest.get("version"), str):
        errors.append("plugin manifest must declare the canonical package ID and version")
    try:
        source = skill.read_text(encoding="utf-8")
    except OSError:
        errors.append("missing skills/devbuddy/SKILL.md")
        source = ""
    if "disable-model-invocation: true" not in source:
        errors.append("DevBuddy entrypoint must require explicit user invocation")
    agents = sorted(path.name for path in (PLUGIN / "agents").glob("*.md") if AGENT.fullmatch(path.name))
    role_count = len([path for path in (ROOT / "devbuddy-source-of-truth" / "roles").glob("*.md") if path.stem != "orchestrator"])
    expected_agents = role_count * 6
    if len(agents) != expected_agents:
        errors.append(f"expected {expected_agents} generated role/effort agents, found {len(agents)}")
    for relative in RUNTIME_FILES:
        if not (PLUGIN / relative).is_file():
            errors.append(f"missing Plugin-owned runtime asset: {relative}")
    for relative in MAINTENANCE_FILES:
        if (PLUGIN / relative).exists():
            errors.append(f"source-maintenance utility must not ship in Plugin payload: {relative}")
    if errors:
        print("CLAUDE PLUGIN VALIDATION FAILED\n" + "\n".join(errors))
        return 1
    print(json.dumps({
        "plugin": NAME,
        "entrypoint": "/devbuddy-claude-code:devbuddy",
        "discovery": {"skills": ["devbuddy"], "agents": agents, "refresh": "/reload-plugins"},
        "status": "valid",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
