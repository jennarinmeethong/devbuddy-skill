#!/usr/bin/env python3
"""Build and install one read-only database adapter into a DevBuddy workspace.

The command is deliberately dry-run by default.  `--apply` is an explicit
approval to run `dotnet publish` and write the selected engine's executable,
manifest, and non-secret configuration template below `.devbuddy/tools/`.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "plugin" / "devbuddy-database-core" / "src" / "DevBuddy.Database.Policy" / "DevBuddy.Database.Policy.csproj"
ENGINES = ("sqlserver", "postgresql", "mariadb", "oracle", "mongodb", "redis")
DATABASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def runtime_id() -> str:
    system = sys.platform
    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x64" if machine in {"x86_64", "amd64", "x64"} else ""
    prefixes = {"win32": "win", "darwin": "osx", "linux": "linux"}
    prefix = prefixes.get(system)
    if not prefix or not architecture:
        raise ValueError(f"cannot infer a supported .NET runtime from {system}/{machine}; pass --runtime explicitly")
    return f"{prefix}-{architecture}"


def workspace_root(value: Path) -> Path:
    selected = value.resolve()
    if selected.name != ".devbuddy":
        raise ValueError("--devbuddy-root must point to a directory named .devbuddy")
    if not (selected / "settings.yaml").is_file():
        raise ValueError("workspace must be initialized first: missing settings.yaml")
    return selected


def executable_name(rid: str) -> str:
    return "DevBuddy.Database.Policy.exe" if rid.startswith("win-") else "DevBuddy.Database.Policy"


def plan(root: Path, database_id: str, engine: str, rid: str) -> dict[str, str]:
    target = root / "tools" / "databases" / database_id
    return {
        "database_id": database_id,
        "engine": engine,
        "runtime": rid,
        "target": str(target),
        "manifest": str(target / "tool.json"),
        "template": str(target / "appsettings.template.json"),
        "executable": str(target / "runtime" / rid / executable_name(rid)),
    }


def materialize(root: Path, database_id: str, engine: str, rid: str, apply: bool) -> int:
    details = plan(root, database_id, engine, rid)
    target = Path(details["target"])
    print(json.dumps({"operation": "materialize-database-adapter", **details}, indent=2))
    if target.exists():
        print(f"ERROR: refusing to overwrite existing database adapter: {target}")
        return 1
    if not apply:
        print("DRY RUN: pass --apply to publish and materialize the database adapter")
        return 0
    source_manifest = ROOT / "plugin" / f"devbuddy-database-{engine}" / "tool.json"
    source_template = ROOT / "plugin" / f"devbuddy-database-{engine}" / "appsettings.template.json"
    if not PROJECT.is_file() or not source_manifest.is_file() or not source_template.is_file():
        print("ERROR: database package source is incomplete")
        return 1
    with tempfile.TemporaryDirectory(prefix="devbuddy-database-materialize-") as temporary:
        stage = Path(temporary) / database_id
        published = stage / "runtime" / rid
        command = [
            "dotnet", "publish", str(PROJECT), "--configuration", "Release", "--runtime", rid,
            "--self-contained", "true", "--nologo", "-p:PublishSingleFile=true", "-p:DebugType=None",
            "--output", str(published),
        ]
        print("PUBLISH: " + " ".join(command))
        try:
            result = subprocess.run(command, cwd=ROOT, check=False)
        except OSError as error:
            print(f"ERROR: cannot publish database adapter: {error}")
            return 1
        executable = published / executable_name(rid)
        if result.returncode or not executable.is_file():
            print("ERROR: database adapter publish failed")
            return result.returncode or 1
        shutil.copy2(source_manifest, stage / "tool.json")
        shutil.copy2(source_template, stage / "appsettings.template.json")
        (stage / "runtime.json").write_text(json.dumps({
            "schema_version": 1,
            "database_id": database_id,
            "engine": engine,
            "runtime": rid,
            "executable": f"runtime/{rid}/{executable.name}",
            "read_only": True,
        }, indent=2) + "\n", encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stage), str(target))
    print(f"APPLIED: materialized database adapter at {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devbuddy-root", type=Path, required=True)
    parser.add_argument("--database-id", required=True)
    parser.add_argument("--engine", choices=ENGINES, required=True)
    parser.add_argument("--runtime", help=".NET runtime identifier; inferred from the current host when omitted")
    parser.add_argument("--apply", action="store_true", help="publish and write the adapter into the workspace")
    args = parser.parse_args()
    try:
        if not DATABASE_ID.fullmatch(args.database_id):
            raise ValueError("--database-id must contain only letters, digits, dot, underscore, or hyphen")
        root = workspace_root(args.devbuddy_root)
        rid = args.runtime or runtime_id()
        if not re.fullmatch(r"(?:win|linux|osx)-(?:x64|arm64)", rid):
            raise ValueError("--runtime must be one of win/linux/osx with x64 or arm64")
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1
    return materialize(root, args.database_id, args.engine, rid, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
