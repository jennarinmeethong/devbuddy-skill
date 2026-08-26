#!/usr/bin/env python3
"""Retire the recognized pre-Plugin DevBuddy database custom tool safely.

The migration is intentionally narrow: it recognizes only the old
``readonly_database_query`` registry entry paired with
``tools/db-query-tool/tool.json``. It never reads credentials and it never
creates a replacement database profile. Preview is the default; ``--apply``
backs up settings and moves the old tool directory below the workspace before
removing its registry entry.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


LEGACY_NAME = "readonly_database_query"
LEGACY_MANIFEST = "tools/db-query-tool/tool.json"


def workspace_root(value: Path) -> Path:
    selected = value.resolve()
    if selected.name != ".devbuddy":
        raise ValueError("workspace root must be named .devbuddy")
    return selected


def setting_without_legacy_registration(text: str) -> tuple[str, int]:
    """Remove only fully recognized legacy custom-tool list items."""
    lines = text.splitlines(keepends=True)
    header = next((index for index, line in enumerate(lines) if re.match(r"^custom_tools:\s*(?:#.*)?(?:\r?\n)?$", line)), None)
    if header is None:
        return text, 0
    end = len(lines)
    for index in range(header + 1, len(lines)):
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*", lines[index]):
            end = index
            break
    starts = [index for index in range(header + 1, end) if re.match(r"^  -\s+", lines[index])]
    if not starts:
        return text, 0
    entries = [(start, starts[position + 1] if position + 1 < len(starts) else end) for position, start in enumerate(starts)]
    retired = []
    for start, stop in entries:
        block = "".join(lines[start:stop])
        name = re.search(r"^\s*-\s+name:\s*['\"]?([^\s'\"]+)['\"]?\s*$", block, re.MULTILINE)
        manifest = re.search(r"^\s*manifest:\s*['\"]?([^\s'\"]+)['\"]?\s*$", block, re.MULTILINE)
        if name and manifest and name.group(1) == LEGACY_NAME and manifest.group(1).replace("\\", "/") == LEGACY_MANIFEST:
            retired.append((start, stop))
    if not retired:
        return text, 0
    retired_starts = {start for start, _stop in retired}
    kept = ["".join(lines[start:stop]) for start, stop in entries if start not in retired_starts]
    before_entries = lines[:starts[0]]
    after_section = lines[end:]
    if kept:
        return "".join(before_entries + kept + after_section), len(retired)
    return "".join(lines[:header] + ["custom_tools: []\n"] + after_section), len(retired)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devbuddy-root", type=Path, default=Path.cwd() / ".devbuddy")
    parser.add_argument("--apply", action="store_true", help="back up and retire the recognized legacy tool")
    args = parser.parse_args()
    try:
        root = workspace_root(args.devbuddy_root)
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1
    settings = root / "settings.yaml"
    if not settings.is_file():
        print(f"ERROR: missing settings: {settings}")
        return 1
    tool = root / "tools" / "db-query-tool"
    if tool.is_symlink() or (tool.exists() and not tool.is_dir()):
        print(f"ERROR: refusing unexpected legacy tool path: {tool}")
        return 1
    updated_settings, registrations = setting_without_legacy_registration(settings.read_text(encoding="utf-8"))
    if not registrations and not tool.exists():
        print("OK: no recognized legacy DevBuddy database tooling found")
        return 0
    print(f"LEGACY REGISTRATIONS: {registrations}")
    if tool.exists():
        print(f"MOVE: {tool} -> {root / 'backups' / 'legacy-database-tools' / '<timestamp>' / tool.name}")
    if registrations:
        print(f"BACKUP SETTINGS: {settings}")
        print(f"REMOVE REGISTRATION: {LEGACY_NAME} ({LEGACY_MANIFEST})")
    if not args.apply:
        print("DRY RUN: pass --apply to back up and retire only the recognized legacy database tool")
        return 0
    backup = root / "backups" / "legacy-database-tools" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, exist_ok=False)
    if registrations:
        shutil.copy2(settings, backup / "settings.yaml")
        settings.write_text(updated_settings, encoding="utf-8")
    if tool.exists():
        shutil.move(str(tool), str(backup / tool.name))
    print(f"RETIRED: legacy database tooling backed up at {backup}")
    print("NEXT: materialize and register a Plugin-owned database adapter before requesting database access")
    return 0


if __name__ == "__main__":
    sys.exit(main())
