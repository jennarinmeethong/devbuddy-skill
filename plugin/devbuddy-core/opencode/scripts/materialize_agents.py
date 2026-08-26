#!/usr/bin/env python3
"""Safely materialize selected DevBuddy OpenCode agent presets into a project."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", action="append", default=[], help="preset name from agent-presets.json; repeatable")
    parser.add_argument("--role", action="append", default=[], help="specialist role ID; repeatable")
    parser.add_argument("--all", action="store_true", help="materialize every specialist agent")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="project root containing .opencode")
    parser.add_argument("--apply", action="store_true", help="copy agents; otherwise preview only")
    args = parser.parse_args()
    if not (args.preset or args.role or args.all):
        parser.error("select --preset, --role, or --all")
    presets = json.loads((ROOT / "agent-presets.json").read_text(encoding="utf-8")).get("presets", {})
    if not isinstance(presets, dict):
        print("ERROR: invalid agent preset catalog"); return 1
    roles = list(args.role)
    for preset in args.preset:
        selected = presets.get(preset)
        if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
            print(f"ERROR: unknown agent preset: {preset}"); return 1
        roles.extend(selected)
    available = {path.stem for path in (ROOT / "agents").glob("*.md")} - {"orchestrator"}
    if args.all: roles.extend(sorted(available))
    roles = list(dict.fromkeys(roles))
    unknown = [role for role in roles if role not in available]
    if unknown:
        print("ERROR: unknown OpenCode role: " + ", ".join(unknown)); return 1
    target = args.project_root.resolve() / ".opencode" / "agents" / "devbuddy"
    conflicts = [target / f"{role}.md" for role in roles if (target / f"{role}.md").exists()]
    for role in roles:
        print(f"MATERIALIZE: agents/{role}.md -> {target / (role + '.md')}")
    if conflicts:
        print("CONFLICT: existing agent definitions: " + ", ".join(path.name for path in conflicts)); return 2
    if not args.apply:
        print("DRY RUN: no files written"); return 0
    target.mkdir(parents=True, exist_ok=True)
    for role in roles:
        shutil.copy2(ROOT / "agents" / f"{role}.md", target / f"{role}.md")
    print(f"APPLIED: materialized {len(roles)} DevBuddy OpenCode agent(s)"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
