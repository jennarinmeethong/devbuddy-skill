#!/usr/bin/env python3
"""Check adapter checklist coverage and required remarks."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ITEM = re.compile(r"^- \[([ x-])\] `?([A-Za-z0-9_-]+)`? .*Status:\s*`?(done|not_started|in_progress)`?", re.MULTILINE)


def read_items(path: Path) -> tuple[dict[str, tuple[str, str, int]], list[str]]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    result: dict[str, tuple[str, str, int]] = {}
    for index, line in enumerate(lines):
        match = ITEM.match(line)
        if not match:
            continue
        box, key, status = match.groups()
        if key.startswith("<"):
            continue
        if key in result:
            errors.append(f"{path}: duplicate change ID {key}")
        result[key] = (box, status, index)
        expected = {"done": "x", "not_started": " ", "in_progress": "-"}[status]
        if box != expected:
            errors.append(f"{path}: {key} checkbox does not match status {status}")
        if status != "done":
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if "Remark:" not in next_line:
                errors.append(f"{path}: {key} is {status} without immediate Remark")
    return result, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("checklists", nargs="+", type=Path)
    args = parser.parse_args()
    if not args.template.is_file():
        print(f"ERROR: template not found: {args.template}")
        return 1
    template, errors = read_items(args.template)
    for path in args.checklists:
        if not path.is_file():
            errors.append(f"checklist not found: {path}")
            continue
        items, item_errors = read_items(path)
        errors.extend(item_errors)
        missing = set(template) - set(items)
        if missing:
            errors.append(f"{path}: missing change IDs: {', '.join(sorted(missing))}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {len(template)} source change IDs are covered by {len(args.checklists)} adapter checklists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
