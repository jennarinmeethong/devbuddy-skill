#!/usr/bin/env python3
"""Create the DevBuddy project-memory layout without overwriting files."""
from __future__ import annotations

import argparse
from pathlib import Path

CORE = {"Context.md": "# Technical Context\n\n", "BusinessContext.md": "# Business Context\n\n", "DecisionLog.md": "# Decision Log\n\n", "KnowledgeBase.md": "# Knowledge Base\n\n"}
DIRECTORIES = ["domains", "features", "requirements", "flows", "business-rules", "screens", "technical/architecture", "technical/apis", "technical/database", "technical/events", "technical/integrations", "tests", "decisions", "releases", "incidents", "tasks"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="approved DevBuddy memory root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    conflicts = [str(root / name) for name in CORE if (root / name).exists()]
    if conflicts:
        print("ERROR: refusing to overwrite existing files: " + ", ".join(conflicts))
        return 1
    planned = [root / name for name in CORE] + [root / directory for directory in DIRECTORIES]
    if args.dry_run:
        for path in planned:
            print(f"CREATE: {path}")
        return 0
    try:
        for directory in DIRECTORIES:
            (root / directory).mkdir(parents=True, exist_ok=True)
        for name, content in CORE.items():
            # No newline= argument: it needs Python 3.10+, and the content
            # already uses \n. Keep this runnable on the stock macOS 3.9.
            (root / name).write_text(content, encoding="utf-8")
    except OSError as error:
        print(f"ERROR: cannot create memory layout at {root}: {error}")
        return 1
    print(f"OK: created DevBuddy memory layout at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
