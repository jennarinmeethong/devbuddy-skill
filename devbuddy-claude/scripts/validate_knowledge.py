#!/usr/bin/env python3
"""Validate DevBuddy knowledge entity metadata without external packages."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

CORE = {"Context.md", "BusinessContext.md", "DecisionLog.md", "KnowledgeBase.md"}
TYPED = {"domains", "features", "requirements", "flows", "business-rules", "screens", "technical", "tests", "decisions", "releases", "incidents"}
FIELDS = {"id", "type", "status", "owner", "source", "last_verified", "confidence"}


def metadata(path: Path) -> dict[str, str] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+)$", line)
        if match:
            result[match.group(1)] = match.group(2).strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("memory_root", type=Path)
    args = parser.parse_args()
    root, errors = args.memory_root, []
    if not root.is_dir():
        print(f"ERROR: memory root not found: {root}")
        return 1
    errors.extend("missing core file: " + name for name in sorted(CORE) if not (root / name).is_file())
    seen: dict[str, Path] = {}
    count = 0
    for directory in TYPED:
        base = root / directory
        for path in base.rglob("*.md") if base.is_dir() else []:
            count += 1
            data = metadata(path)
            if data is None:
                errors.append(f"{path}: missing YAML metadata")
                continue
            absent = FIELDS - set(data)
            if absent:
                errors.append(f"{path}: missing fields: {', '.join(sorted(absent))}")
                continue
            if data["id"] in seen:
                errors.append(f"duplicate id {data['id']}: {seen[data['id']]} and {path}")
            seen[data["id"]] = path
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {root} has {count} validated typed knowledge entities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
