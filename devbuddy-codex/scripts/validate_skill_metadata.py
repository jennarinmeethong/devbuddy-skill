#!/usr/bin/env python3
"""Validate essential Codex Skill metadata without PyYAML."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    args = parser.parse_args()
    root = args.skill_root
    errors: list[str] = []
    skill = root / "SKILL.md"
    config = root / "agents" / "openai.yaml"
    if not skill.is_file():
        errors.append("missing SKILL.md")
    else:
        lines = skill.read_text(encoding="utf-8").splitlines()
        if len(lines) < 4 or lines[0] != "---":
            errors.append("SKILL.md: missing YAML frontmatter")
        else:
            try:
                end = lines.index("---", 1)
            except ValueError:
                errors.append("SKILL.md: unterminated YAML frontmatter")
                end = 1
            fields = {match.group(1): match.group(2) for line in lines[1:end] if (match := re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+)$", line))}
            if set(fields) != {"name", "description"}:
                errors.append("SKILL.md: frontmatter must contain only name and description")
            if fields.get("name") != "devbuddy":
                errors.append("SKILL.md: name must be devbuddy for $devbuddy invocation")
            if not fields.get("description"):
                errors.append("SKILL.md: description is required")
    if not config.is_file():
        errors.append("missing agents/openai.yaml")
    else:
        text = config.read_text(encoding="utf-8")
        for pattern, message in [
            (r'^  display_name: ".+"$', "display_name"),
            (r'^  short_description: ".+"$', "short_description"),
            (r'^  default_prompt: ".*\$devbuddy.*"$', "default_prompt with $devbuddy"),
            (r"^  allow_implicit_invocation: false$", "allow_implicit_invocation false"),
        ]:
            if not re.search(pattern, text, re.MULTILINE):
                errors.append(f"agents/openai.yaml: missing {message}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: Codex Skill metadata validates for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
