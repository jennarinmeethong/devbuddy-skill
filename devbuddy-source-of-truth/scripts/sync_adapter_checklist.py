#!/usr/bin/env python3
"""Synchronise missing source checklist items into an adapter checklist."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ITEM = re.compile(r"^- \[[ x-]\] `?([A-Za-z0-9_-]+)`? .*Status:", re.MULTILINE)


def ids(text: str) -> set[str]:
    return {match.group(1) for match in ITEM.finditer(text) if not match.group(1).startswith("<")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("adapter", type=Path)
    args = parser.parse_args()
    source = args.template.read_text(encoding="utf-8")
    adapter = args.adapter.read_text(encoding="utf-8") if args.adapter.exists() else "# Adapter Implementation Checklist\n\n## Checklist\n"
    missing = ids(source) - ids(adapter)
    if not missing:
        print("OK: no checklist items to add")
        return 0
    source_lines = source.splitlines()
    lines: list[str] = []
    for index, line in enumerate(source_lines):
        match = ITEM.match(line)
        if not match or match.group(1) not in missing:
            continue
        lines.append(line)
        if index + 1 < len(source_lines) and "Remark:" in source_lines[index + 1]:
            lines.append(source_lines[index + 1])
    with args.adapter.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n## Synced items\n")
        for line in lines:
            handle.write(line + "\n")
    print("ADDED: " + ", ".join(sorted(missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
