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
    "KnowledgeBase.md": "# Knowledge Base\n\n",
}
# Keep legacy files during an explicit layout migration, but do not create or
# require them.  Business context belongs in typed business entities and
# decisions in the decisions/ directory, where each item has evidence.
LEGACY_CORE = (*CORE, "BusinessContext.md", "DecisionLog.md")
KNOWLEDGE_DIRS = [
    "domains", "features", "requirements", "flows", "business-rules", "screens",
    "technical/architecture", "technical/apis", "technical/database", "technical/events",
    "technical/integrations", "tests", "decisions", "releases", "incidents",
]
TOOLS = (
    "init_project_memory.py", "bootstrap_knowledge.py", "task_memory.py",
    "validate_project_settings.py", "validate_knowledge.py",
)
# Never copied into a workspace: build output is regenerated locally, and the
# host's real configuration holds credentials the skill must never carry.
SKIP_DIRS = {"bin", "obj", "releases", ".venv", "__pycache__", "node_modules"}
SKIP_FILES = {"appsettings.json", "tool.json", ".DS_Store"}


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


def bundled_tool(name: str) -> Path:
    """Locate a bundled custom-tool directory under templates/project-tools/.

    These are opt-in: unlike the five Python runtime tools, a bundled custom
    tool may need another runtime and a build step, so seeding it is an explicit
    request rather than part of workspace initialisation.
    """
    if not PROJECT_ID.fullmatch(name):
        raise ValueError(f"invalid custom tool name: {name!r}")
    source = Path(__file__).resolve().parents[1] / "templates" / "project-tools" / name
    if not source.is_dir():
        raise ValueError(f"bundled custom tool not found: {name}")
    return source


def bundled_tool_pairs(source: Path, root: Path) -> list[tuple[Path, Path]]:
    """Plan the copy, skipping anything a build produces or a host owns."""
    pairs: list[tuple[Path, Path]] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        parts = set(path.relative_to(source).parts)
        if parts & SKIP_DIRS or path.name in SKIP_FILES:
            continue
        pairs.append((path, root / "tools" / path.relative_to(source)))
    return pairs


def workspace_root(args: argparse.Namespace) -> Path:
    if args.devbuddy_root is not None:
        selected = args.devbuddy_root.expanduser().resolve()
    elif args.root is not None:
        print("DEPRECATED: --root is now an alias for --devbuddy-root")
        selected = args.root.expanduser().resolve()
    elif args.project_root is not None:
        print("DEPRECATED: --project-root selects one project; prefer --devbuddy-root and --project id=path")
        selected = args.project_root.expanduser().resolve() / DEFAULT_ROOT
    else:
        selected = (Path.cwd() / DEFAULT_ROOT).resolve()
    if selected.name != DEFAULT_ROOT:
        raise ValueError(f"DevBuddy root must be named {DEFAULT_ROOT}: {selected}")
    return selected


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
    lines.extend((
        "memory_root: knowledge-base",
        "tools:",
        "  is_rtk: false",
        "orchestration:",
        "  max_concurrency: 2",
        "  task_timeout_seconds: 900",
        "  retry_limit: 1",
        "",
    ))
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
    names = list(LEGACY_CORE) + [directory.split("/", 1)[0] for directory in KNOWLEDGE_DIRS]
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
    parser.add_argument("--seed-custom-tool", action="append", default=[], metavar="NAME",
                        help="copy a bundled custom tool from templates/project-tools/NAME into tools/; repeatable")
    args = parser.parse_args()
    try:
        root = workspace_root(args)
        project_map = projects(args.project, root, args.project_root)
        sources = {name: tool_source(name) for name in TOOLS}
        bundled = [(name, bundled_tool(name)) for name in args.seed_custom_tool]
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
    custom_actions: list[tuple[Path, Path]] = []
    for name, source in bundled:
        pairs = bundled_tool_pairs(source, root)
        existing = [target for _source, target in pairs if target.exists()]
        if existing:
            # The host may have edited the seeded copy or built inside it, so an
            # overwrite here could destroy local work the manifest cannot vouch for.
            print(f"ERROR: refusing to overwrite existing custom tool files for {name}: " + ", ".join(map(str, existing[:3])))
            return 1
        custom_actions.extend(pairs)

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
    for _source, target in custom_actions:
        print(f"CREATE: {target}")
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
        for source, target in custom_actions:
            target.parent.mkdir(parents=True, exist_ok=True)
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
