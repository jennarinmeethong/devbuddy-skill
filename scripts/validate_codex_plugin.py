#!/usr/bin/env python3
"""Validate the self-contained Codex Plugin payload without host mutation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin" / "devbuddy-codex"
RUNTIME_FILES = (
    "skills/devbuddy/SKILL.md", "settings.yaml", "agents/openai.yaml",
    "references/policy.md", "references/codex-dispatch.md",
    "schemas/slice-record.schema.json", "templates/task-ledger.md",
    "scripts/init_project_memory.py",
)


def main() -> int:
    errors: list[str] = []
    manifest_path = PLUGIN / ".codex-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: invalid Codex Plugin manifest: {error}")
        return 1
    if manifest.get("name") != "devbuddy-codex" or not str(manifest.get("version", "")).startswith("1.0.2+"):
        errors.append("manifest must declare the canonical Codex package ID and cache-busted version")
    if manifest.get("skills") != "./skills/":
        errors.append("manifest must expose the generated skills directory")
    for relative in RUNTIME_FILES:
        if not (PLUGIN / relative).is_file():
            errors.append(f"missing Plugin-owned runtime asset: {relative}")
    skill = PLUGIN / "skills" / "devbuddy" / "SKILL.md"
    if skill.is_file() and "name: devbuddy" not in skill.read_text(encoding="utf-8"):
        errors.append("$devbuddy entrypoint metadata is missing")
    if errors:
        print("CODEX PLUGIN VALIDATION FAILED\n" + "\n".join(errors))
        return 1
    print(json.dumps({
        "plugin": "devbuddy-codex",
        "entrypoint": "$devbuddy",
        "discovery": "codex plugin list; start a new thread after install or update",
        "status": "valid",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
