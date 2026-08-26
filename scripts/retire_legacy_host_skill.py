#!/usr/bin/env python3
"""Back up recognized standalone DevBuddy host files; preview by default."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def recognized(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return "devbuddy" in path.read_text(encoding="utf-8", errors="replace")[:4000].lower()
    except OSError:
        return False


def targets(host: str, root: Path) -> list[Path]:
    skill = root / "skills" / "devbuddy"
    selected = [skill] if skill.is_dir() and recognized(skill / "SKILL.md") else []
    if host == "claude-code":
        selected.extend(path for path in sorted((root / "agents").glob("devbuddy-*.md")) if recognized(path))
    return [path for path in selected if path.exists()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("codex", "claude-code"), required=True)
    parser.add_argument("--host-root", type=Path, help="override the host configuration root")
    parser.add_argument("--apply", action="store_true", help="move recognized standalone files into a timestamped backup")
    args = parser.parse_args()
    default = Path.home() / (".codex" if args.host == "codex" else ".claude")
    root = (args.host_root or default).expanduser().resolve()
    found = targets(args.host, root)
    skill = root / "skills" / "devbuddy"
    if skill.exists() and not skill.is_dir():
        print(f"ERROR: refusing unexpected skill path: {skill}")
        return 1
    if skill.is_dir() and not recognized(skill / "SKILL.md"):
        print(f"ERROR: refusing unrecognized skill directory: {skill}")
        return 1
    if not found:
        print("OK: no recognized standalone DevBuddy host files found")
        return 0
    destination = root / "backups" / "devbuddy-legacy-host" / "<timestamp>"
    for path in found:
        print(f"MOVE: {path} -> {destination / path.relative_to(root)}")
    if not args.apply:
        print("DRY RUN: pass --apply to back up the recognized standalone DevBuddy skill")
        return 0
    backup = root / "backups" / "devbuddy-legacy-host" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for path in found:
        target = backup / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
    print(f"RETIRED: standalone DevBuddy files backed up at {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
