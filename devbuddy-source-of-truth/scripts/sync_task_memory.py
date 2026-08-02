#!/usr/bin/env python3
"""Copy canonical workspace tools to both adapters and their install templates."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show target files without writing")
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    repository = scripts.parents[1]
    common = ("init_project_memory.py", "bootstrap_knowledge.py", "task_memory.py", "validate_knowledge.py")
    for name in common:
        source = scripts / name
        for adapter in ("devbuddy-codex", "devbuddy-claude"):
            targets = (
                repository / adapter / "scripts" / name,
                repository / adapter / "templates" / "project-tools" / f"{name}.template",
            )
            for target in targets:
                if args.dry_run:
                    print(f"SYNC: {source} -> {target}")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"OK: synced {target}")
    for adapter in ("devbuddy-codex", "devbuddy-claude"):
        source = repository / adapter / "scripts" / "validate_project_settings.py"
        target = repository / adapter / "templates" / "project-tools" / "validate_project_settings.py.template"
        if args.dry_run:
            print(f"SYNC: {source} -> {target}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"OK: synced {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
