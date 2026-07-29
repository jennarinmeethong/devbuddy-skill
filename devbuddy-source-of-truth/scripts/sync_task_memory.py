#!/usr/bin/env python3
"""Copy the canonical task-memory tool to the Codex and Claude adapters."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show target files without writing")
    args = parser.parse_args()
    source = Path(__file__).with_name("task_memory.py")
    repository = source.parents[2]
    targets = [
        repository / "devbuddy-codex" / "scripts" / "task_memory.py",
        repository / "devbuddy-claude" / "scripts" / "task_memory.py",
    ]
    content = source.read_text(encoding="utf-8")
    for target in targets:
        if args.dry_run:
            print(f"SYNC: {source} -> {target}")
            continue
        target.write_text(content, encoding="utf-8")
        print(f"OK: synced {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
