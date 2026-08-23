#!/usr/bin/env python3
"""Safe maintenance commands for a DevBuddy `.devbuddy` workspace."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
SECRET_PATTERN = re.compile(r"(?i)(password|connection\s*string|access[_ -]?token|api[_ -]?key)\s*:")
DATABASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ENGINES = {"sqlserver", "postgresql", "mariadb", "oracle", "mongodb", "redis"}


def root(value: Path) -> Path:
    selected = value.resolve()
    if selected.name != ".devbuddy": raise ValueError("workspace root must be named .devbuddy")
    return selected


def defaults() -> str:
    return "schema_version: 1\nplugin_version: 1.0.0\nworkspace_schema_version: 1\ntool_manifest_version: 1\ndatabases: []\n"


def required_directories(selected: Path) -> tuple[Path, ...]:
    return (selected / "knowledge-base", selected / "tasks", selected / "tools" / "databases")


def upgrade_settings(text: str) -> str:
    required = {"plugin_version": "1.0.0", "workspace_schema_version": "1", "tool_manifest_version": "1", "databases": "[]"}
    missing = [f"{key}: {value}" for key, value in required.items() if not re.search(rf"^{key}:\s*", text, re.MULTILINE)]
    return text.rstrip() + ("\n" + "\n".join(missing) if missing else "") + "\n"


def migration_pairs(selected: Path) -> list[tuple[Path, Path]]:
    return [(selected / name, selected / "knowledge-base" / name) for name in ("Context.md", "KnowledgeBase.md") if (selected / name).is_file()]


def find_database_ids(text: str) -> list[str]:
    return re.findall(r"^\s*-\s+id:\s*([A-Za-z0-9._-]+)\s*$", text, re.MULTILINE)


def database_profiles(text: str) -> list[dict[str, str]]:
    """Parse the intentionally small YAML subset used by the registry.

    Settings remains extensible: fields unknown to this validator are retained
    and ignored, while the contract fields below are checked fail-closed.
    """
    profiles: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_databases = False
    for raw in text.splitlines():
        if raw == "databases:":
            in_databases = True
            continue
        if in_databases and raw and not raw.startswith((" ", "\t", "#")):
            break
        if not in_databases:
            continue
        if match := re.match(r"^  - id:\s*(\S+)\s*$", raw):
            current = {"id": match.group(1).strip("\"'")}; profiles.append(current)
        elif current and (match := re.match(r"^    ([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", raw)):
            current[match.group(1)] = match.group(2).strip("\"'")
    return profiles


def validate(selected: Path) -> list[str]:
    errors: list[str] = []
    settings = selected / "settings.yaml"
    manifest = selected / "tools" / "manifest.json"
    if not settings.is_file(): return [f"missing settings: {settings}"]
    text = settings.read_text(encoding="utf-8")
    for key, expected in (("schema_version", "1"), ("workspace_schema_version", "1")):
        if not re.search(rf"^{key}:\s*{re.escape(expected)}\s*$", text, re.MULTILINE): errors.append(f"{key} must be {expected}")
    if SECRET_PATTERN.search(text): errors.append("settings.yaml must not contain credential-shaped values")
    profiles = database_profiles(text)
    ids = [profile["id"] for profile in profiles]
    if len(ids) != len(set(ids)): errors.append("database IDs must be unique")
    for identifier in ids:
        if not DATABASE_ID.fullmatch(identifier): errors.append(f"invalid database ID: {identifier}")
    for match in re.finditer(r"^\s+engine:\s*(\S+)\s*$", text, re.MULTILINE):
        if match.group(1) not in ENGINES: errors.append(f"unsupported database engine: {match.group(1)}")
    for match in re.finditer(r"^\s+secret_file:\s*(\S+)\s*$", text, re.MULTILINE):
        relative = Path(match.group(1).strip("\"'"))
        if relative.is_absolute() or ".." in relative.parts or not str(relative).replace("\\", "/").startswith("tools/databases/"):
            errors.append(f"secret_file must remain below tools/databases: {relative}")
    for profile in profiles:
        missing = {"engine", "environment", "adapter_package", "manifest", "secret_file", "approval", "max_rows", "timeout_seconds"} - profile.keys()
        if missing:
            errors.append(f"database {profile['id']} missing fields: {', '.join(sorted(missing))}")
            continue
        engine = profile["engine"]
        if engine not in ENGINES:
            errors.append(f"database {profile['id']} has unsupported engine: {engine}")
        if profile["adapter_package"] != f"devbuddy-database-{engine}":
            errors.append(f"database {profile['id']} adapter_package must match engine")
        if profile["environment"] == "production" and profile["approval"] != "ask":
            errors.append(f"database {profile['id']} production approval must be ask")
        if profile["approval"] not in {"ask", "deny"}:
            errors.append(f"database {profile['id']} approval must be ask or deny")
        expected = f"tools/databases/{profile['id']}/tool.json"
        if profile["manifest"].replace("\\", "/") != expected:
            errors.append(f"database {profile['id']} manifest must be {expected}")
        manifest = selected / Path(profile["manifest"])
        secret = selected / Path(profile["secret_file"])
        if not manifest.is_file():
            errors.append(f"database {profile['id']} manifest not found: {manifest}")
        if not secret.is_file():
            errors.append(f"database {profile['id']} secret file not found: {secret}")
        for field, lower, upper in (("max_rows", 1, 5000), ("timeout_seconds", 1, 120)):
            try: value = int(profile[field])
            except ValueError: errors.append(f"database {profile['id']} {field} must be an integer"); continue
            if not lower <= value <= upper: errors.append(f"database {profile['id']} {field} must be {lower}..{upper}")
    if manifest.is_file():
        try: json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError: errors.append("invalid tools/manifest.json")
    return errors


def report(command: str, selected: Path, errors: list[str]) -> None:
    print(json.dumps({"command": command, "workspace": str(selected), "valid": not errors, "errors": errors}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "validate", "inspect", "doctor", "init", "upgrade", "migrate", "repair", "bootstrap"))
    parser.add_argument("--devbuddy-root", type=Path, default=Path.cwd() / ".devbuddy")
    parser.add_argument("--apply", action="store_true", help="explicitly write workspace state")
    parser.add_argument("--dry-run", action="store_true", help="show planned changes only")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        print("ERROR: --apply and --dry-run cannot be combined")
        return 1
    try: selected = root(args.devbuddy_root)
    except ValueError as error: print(f"ERROR: {error}"); return 1
    readonly = {"status", "validate", "inspect", "doctor"}
    if args.command in readonly:
        errors = validate(selected)
        report(args.command, selected, errors)
        return 0 if not errors else 1
    settings = selected / "settings.yaml"
    migrations = migration_pairs(selected) if args.command == "migrate" and selected.exists() else []
    conflicts = [destination for _source, destination in migrations if destination.exists()]
    creates = [directory for directory in required_directories(selected) if not directory.exists()]
    if not args.apply:
        print(f"PLAN: {args.command} would only add or repair DevBuddy-managed files under {selected}")
        for directory in creates: print(f"CREATE DIR: {directory}")
        for source, destination in migrations: print(f"MOVE: {source} -> {destination}")
        if args.command == "upgrade" and settings.is_file() and upgrade_settings(settings.read_text(encoding="utf-8")) != settings.read_text(encoding="utf-8"):
            print(f"UPGRADE SETTINGS: {settings}")
        for destination in conflicts: print(f"CONFLICT: migration destination exists: {destination}")
        print("DRY RUN: pass --apply to mutate workspace state")
        return 1 if conflicts else 0
    if settings.exists() and args.command == "init":
        print(f"ERROR: refusing to overwrite existing settings: {settings}")
        return 1
    if conflicts:
        print("ERROR: migration destinations already exist: " + ", ".join(map(str, conflicts)))
        return 1
    if settings.exists() and args.command in {"upgrade", "migrate", "repair", "bootstrap"}:
        backup = selected / "backups" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-settings.yaml")
        backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(settings, backup)
        print(f"BACKUP: {backup}")
    selected.mkdir(parents=True, exist_ok=True)
    if not settings.exists(): settings.write_text(defaults(), encoding="utf-8")
    elif args.command == "upgrade":
        settings.write_text(upgrade_settings(settings.read_text(encoding="utf-8")), encoding="utf-8")
    for source, destination in migrations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
    for directory in required_directories(selected):
        directory.mkdir(parents=True, exist_ok=True)
    manifest = selected / "tools" / "manifest.json"
    if not manifest.exists(): manifest.write_text(json.dumps({"tool_manifest_version": 1, "tools": []}, indent=2) + "\n", encoding="utf-8")
    print(f"APPLIED: {args.command} completed at {selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
