#!/usr/bin/env python3
"""Initialise or safely upgrade a multi-project DevBuddy workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

DEFAULT_ROOT = ".devbuddy"
KNOWLEDGE = "knowledge-base"
TOOL_VERSION = "1"
PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
CORE = {
    "Context.md": "# Technical Context\n\n",
    "BusinessContext.md": "# Business Context\n\n",
    "DecisionLog.md": "# Decision Log\n\n",
    "KnowledgeBase.md": "# Knowledge Base\n\n",
}
KNOWLEDGE_DIRS = [
    "domains", "features", "requirements", "flows", "business-rules", "screens",
    "technical/architecture", "technical/apis", "technical/database", "technical/events",
    "technical/integrations", "tests", "decisions", "releases", "incidents",
]
TOOLS = (
    "init_project_memory.py", "bootstrap_knowledge.py", "task_memory.py",
    "validate_project_settings.py", "validate_knowledge.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tool_source(name: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    candidates = (
        root / "templates" / "project-tools" / f"{name}.template",
        Path(__file__).resolve().parent / name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError(f"project-tool template not found: {name}")


def workspace_root(args: argparse.Namespace) -> Path:
    if args.devbuddy_root is not None:
        return args.devbuddy_root.expanduser().resolve()
    if args.root is not None:
        print("DEPRECATED: --root is now an alias for --devbuddy-root")
        return args.root.expanduser().resolve()
    if args.project_root is not None:
        print("DEPRECATED: --project-root selects one project; prefer --devbuddy-root and --project id=path")
        return (args.project_root.expanduser().resolve() / DEFAULT_ROOT)
    return (Path.cwd() / DEFAULT_ROOT).resolve()


def projects(values: list[str], root: Path, legacy: Path | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    resolved: set[Path] = set()
    if legacy is not None and not values:
        values = [f"{legacy.expanduser().resolve().name}={legacy}"]
    for value in values:
        if "=" not in value:
            raise ValueError(f"project must use <id>=<path>: {value!r}")
        project_id, raw_path = value.split("=", 1)
        if not PROJECT_ID.fullmatch(project_id):
            raise ValueError(f"invalid project ID: {project_id!r}")
        if project_id in parsed:
            raise ValueError(f"duplicate project ID: {project_id}")
        path = Path(raw_path).expanduser()
        absolute = (path if path.is_absolute() else root.parent / path).resolve()
        if not absolute.is_dir():
            raise ValueError(f"project path not found: {absolute}")
        if absolute == root or root in absolute.parents:
            raise ValueError(f"project path must not point inside the DevBuddy root: {absolute}")
        if absolute in resolved:
            raise ValueError(f"duplicate resolved project path: {absolute}")
        resolved.add(absolute)
        try:
            stored = Path(os.path.relpath(absolute, root.parent)).as_posix()
        except ValueError:
            stored = str(absolute)
        parsed[project_id] = stored
    return parsed


def render_settings(project_map: dict[str, str]) -> str:
    lines = ["schema_version: 1", "workspace:", "  projects:"]
    if not project_map:
        lines.append("    {}")
    for project_id, path in sorted(project_map.items()):
        lines.extend((f"    {project_id}:", f"      path: {path}"))
    lines.extend(("memory_root: knowledge-base", ""))
    return "\n".join(lines)


def settings_projects(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"^    ([A-Za-z0-9][A-Za-z0-9._-]*):$", raw):
            current = match.group(1)
        elif current and (match := re.match(r"^      path:\s*(.+?)\s*$", raw)):
            result[current] = match.group(1).strip("\"'")
    return result


def migration_pairs(root: Path) -> list[tuple[Path, Path]]:
    names = list(CORE) + [directory.split("/", 1)[0] for directory in KNOWLEDGE_DIRS]
    return [(root / name, root / KNOWLEDGE / name) for name in sorted(set(names)) if (root / name).exists()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devbuddy-root", type=Path, help="selected .devbuddy workspace root")
    parser.add_argument("--project", action="append", default=[], metavar="ID=PATH", help="register a source project; repeatable")
    parser.add_argument("--root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--project-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help="show planned changes only")
    parser.add_argument("--upgrade-tools", action="store_true", help="safely replace recognized project tools")
    parser.add_argument("--migrate-layout", action="store_true", help="move the legacy memory layout below knowledge-base")
    args = parser.parse_args()
    root = workspace_root(args)
    try:
        project_map = projects(args.project, root, args.project_root)
        sources = {name: tool_source(name) for name in TOOLS}
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    moves = migration_pairs(root) if args.migrate_layout else []
    migration_destinations = {destination for _source, destination in moves}
    settings = root / "settings.yaml"
    settings_content = render_settings(project_map)
    creates: list[tuple[Path, str]] = []
    directories = [root / KNOWLEDGE / item for item in KNOWLEDGE_DIRS] + [root / "tasks", root / "tools"]
    for name, content in CORE.items():
        target = root / KNOWLEDGE / name
        if not target.exists() and target not in migration_destinations:
            creates.append((target, content))
    if not settings.exists():
        creates.append((settings, settings_content))
    elif project_map and settings_projects(settings) != project_map:
        print(f"ERROR: settings already exists with different project registry: {settings}")
        return 1

    conflicts = [destination for source, destination in moves if destination.exists()]
    if conflicts:
        print("ERROR: migration destinations already exist: " + ", ".join(map(str, conflicts)))
        return 1

    manifest_path = root / "tools" / "manifest.json"
    old_manifest: dict[str, object] = {}
    if manifest_path.is_file():
        try:
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print(f"ERROR: invalid tool manifest: {manifest_path}")
            return 1
    old_hashes = old_manifest.get("files", {}) if isinstance(old_manifest.get("files", {}), dict) else {}
    tool_actions: list[tuple[str, Path, Path]] = []
    for name, source in sources.items():
        target = root / "tools" / name
        if not target.exists():
            tool_actions.append(("CREATE", source, target))
        elif args.upgrade_tools and sha256(target) != sha256(source):
            if old_hashes.get(name) != sha256(target):
                print(f"ERROR: refusing to replace modified or unrecognized project tool: {target}")
                return 1
            tool_actions.append(("REPLACE", source, target))
    new_manifest = {"tool_version": TOOL_VERSION, "files": {name: sha256(source) for name, source in sources.items()}}
    manifest_content = json.dumps(new_manifest, indent=2, sort_keys=True) + "\n"
    write_manifest = not manifest_path.exists() or (args.upgrade_tools and manifest_path.read_text(encoding="utf-8") != manifest_content)

    for directory in directories:
        if not directory.exists():
            print(f"CREATE DIR: {directory}")
    for source, destination in moves:
        print(f"MOVE: {source} -> {destination}")
    for path, _content in creates:
        print(f"CREATE: {path}")
    for action, _source, target in tool_actions:
        print(f"{action}: {target}")
    if write_manifest:
        print(f"{'REPLACE' if manifest_path.exists() else 'CREATE'}: {manifest_path}")
    if args.dry_run:
        print("DRY RUN: no files written")
        return 0
    try:
        root.mkdir(parents=True, exist_ok=True)
        for source, destination in moves:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        for path, content in creates:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        for _action, source, target in tool_actions:
            shutil.copy2(source, target)
        if write_manifest:
            manifest_path.write_text(manifest_content, encoding="utf-8")
    except OSError as error:
        print(f"ERROR: cannot initialise DevBuddy workspace at {root}: {error}")
        return 1
    print(f"OK: DevBuddy workspace ready at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
