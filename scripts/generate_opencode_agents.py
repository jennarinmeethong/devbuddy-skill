#!/usr/bin/env python3
"""Generate OpenCode specialist-agent Markdown files from canonical roles."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLORS = ("purple", "pink", "orange", "blue", "green", "red", "cyan", "yellow")


def render(source: Path, index: int) -> str:
    lines = source.read_text(encoding="utf-8").strip().splitlines()
    title = lines[0].removeprefix("# ")
    body = "\n".join(lines[1:]).strip()
    return f"""---
description: DevBuddy {title} specialist; use only for a bounded orchestrated slice.
mode: subagent
color: {COLORS[index % len(COLORS)]}
---

# DevBuddy {title}

Read the portable DevBuddy core contract and the assigned task scope before acting. Respect its approval, evidence, and slice-record requirements; do not select a model, expand scope, or perform unapproved external or destructive actions.

{body}
"""


def presets() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for profile in sorted((ROOT / "profiles").glob("*.yaml")):
        name = ""; roles: list[str] = []; active = False
        for raw in profile.read_text(encoding="utf-8").splitlines():
            if match := re.match(r"^name:\s*([a-z0-9-]+)\s*$", raw): name = match.group(1); active = False
            elif raw == "roles:": active = True
            elif re.match(r"^[a-z]+:", raw): active = False
            elif active and (match := re.match(r"^\s*-\s*([a-z0-9-]+)\s*$", raw)): roles.append(match.group(1))
        if roles: result[name] = roles
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "plugin" / "devbuddy-core" / "opencode" / "agents")
    parser.add_argument("--preset-out", type=Path, default=ROOT / "plugin" / "devbuddy-core" / "opencode" / "agent-presets.json")
    parser.add_argument("--check", action="store_true", help="fail when generated files differ")
    args = parser.parse_args()
    roles = [path for path in sorted((ROOT / "devbuddy-source-of-truth" / "roles").glob("*.md")) if path.stem != "orchestrator"]
    stale: list[str] = []
    args.out.mkdir(parents=True, exist_ok=True)
    for index, source in enumerate(roles):
        target = args.out / f"{source.stem}.md"
        content = render(source, index)
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != content:
                stale.append(target.name)
        else:
            target.write_text(content, encoding="utf-8")
    preset_content = json.dumps({"schema_version": 1, "presets": presets()}, indent=2) + "\n"
    if args.check and (not args.preset_out.is_file() or args.preset_out.read_text(encoding="utf-8") != preset_content):
        stale.append(args.preset_out.name)
    elif not args.check:
        args.preset_out.write_text(preset_content, encoding="utf-8")
    if args.check and stale:
        print("ERROR: stale or missing OpenCode agents: " + ", ".join(stale))
        return 1
    print(f"OK: {'verified' if args.check else 'wrote'} {len(roles)} OpenCode specialist agents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
