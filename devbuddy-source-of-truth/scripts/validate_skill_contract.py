#!/usr/bin/env python3
"""Validate generated DevBuddy prompt contracts without third-party packages."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED_FIELDS = {
    "source": {"name", "description"},
    "codex": {"name", "description"},
    "claude": {"name", "description", "disable-model-invocation", "argument-hint"},
}


def frontmatter(content: str) -> dict[str, str] | None:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    return {
        match.group(1): match.group(2).strip()
        for line in lines[1:end]
        if (match := re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+)$", line))
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--contracts", type=Path, default=Path(__file__).resolve().parents[1] / "tests" / "skill-contracts.json")
    args = parser.parse_args()
    try:
        contracts = json.loads(args.contracts.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: cannot read contracts: {error}")
        return 1
    paths = {
        "source": args.repository_root / "devbuddy-source-of-truth" / "SKILL.md",
        "codex": args.repository_root / "devbuddy-codex" / "SKILL.md",
        "claude": args.repository_root / "devbuddy-claude" / "SKILL.md",
    }
    errors: list[str] = []
    for name, required in contracts.items():
        if name not in paths or not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            errors.append(f"invalid contract entry: {name}")
            continue
        try:
            content = paths[name].read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"cannot read {paths[name]}: {error}")
            continue
        fields = frontmatter(content)
        if fields is None:
            errors.append(f"{name} prompt has invalid YAML frontmatter")
        elif set(fields) != EXPECTED_FIELDS[name]:
            errors.append(f"{name} prompt frontmatter fields differ: {', '.join(sorted(set(fields) ^ EXPECTED_FIELDS[name]))}")
        elif name == "claude" and fields["disable-model-invocation"].lower() != "true":
            errors.append("claude prompt must disable model invocation")
        missing = [item for item in required if item not in content]
        if missing:
            errors.append(f"{name} prompt missing: {', '.join(missing)}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {sum(len(items) for items in contracts.values())} prompt-contract assertions validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
