#!/usr/bin/env python3
"""Install the DevBuddy Codex skill with a dry-run-first workflow."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_CONTENT = [
    "README.md",
    "SKILL.md",
    "agents",
    "settings.yaml",
    "schemas",
    "references",
    "roles",
    "templates",
    "manual",
    "tests",
]
MARKER = "devbuddy"


def is_devbuddy_artefact(path: Path, source: Path | None = None) -> bool:
    if MARKER in path.name.lower():
        return True
    try:
        if source is not None and path.read_bytes() == source.read_bytes():
            return True
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return False
    return MARKER in head.lower()


def plan(target: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for entry in SKILL_CONTENT:
        source = ROOT / entry
        if not source.exists():
            continue
        if source.is_file():
            pairs.append((source, target / entry))
            continue
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                pairs.append((path, target / path.relative_to(ROOT)))
    initializer = ROOT / "scripts" / "init_project_memory.py"
    pairs.append((initializer, target / "scripts" / initializer.name))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-root",
        type=Path,
        default=Path.home() / ".codex",
        help="Codex configuration root (default: ~/.codex)",
    )
    parser.add_argument("--apply", action="store_true", help="write files; omit for a dry run")
    parser.add_argument(
        "--replace-recognized-skill",
        action="store_true",
        help="replace differing files only when the existing skill root identifies itself as DevBuddy",
    )
    args = parser.parse_args()

    target = args.codex_root.expanduser() / "skills" / "devbuddy"
    pairs = plan(target)
    if not pairs:
        print("ERROR: no Codex adapter files found")
        return 1
    recognized_skill = is_devbuddy_artefact(target / "SKILL.md")
    conflicts = [destination for source, destination in pairs if destination.exists() and not is_devbuddy_artefact(destination, source)]
    if args.replace_recognized_skill and recognized_skill:
        conflicts = [destination for destination in conflicts if target not in destination.parents and destination != target]
    if conflicts:
        for path in conflicts:
            print(f"ERROR: refusing to overwrite non-DevBuddy file: {path}")
        return 1
    if args.replace_recognized_skill and not recognized_skill:
        print(f"ERROR: {target} is not a recognized DevBuddy skill; refusing replacement")
        return 1

    if not args.apply:
        for _, destination in pairs:
            print(f"{'REPLACE' if destination.exists() else 'CREATE '}: {destination}")
        print(f"\nDry run: {len(pairs)} files. Re-run with --apply to install.")
        return 0

    try:
        for source, destination in pairs:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    except OSError as error:
        print(f"ERROR: install failed: {error}")
        return 1
    print(f"OK: installed {len(pairs)} files at {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
