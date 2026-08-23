#!/usr/bin/env python3
"""Dependency-free validation for DevBuddy package and Codex plugin metadata."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = re.compile(r"^devbuddy-[a-z0-9-]+$")
# SemVer 2.0.0, including optional prerelease and build metadata.  The Codex
# manifest uses build metadata as its cache-buster, so accepting only the
# core X.Y.Z form would reject a valid release manifest.
SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def main() -> int:
    errors: list[str] = []
    seen: set[str] = set()
    for path in sorted((ROOT / "plugin").glob("*/devbuddy.package.json")):
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error: errors.append(f"{path}: invalid JSON: {error.msg}"); continue
        name = data.get("name")
        if not isinstance(name, str) or not PACKAGE.fullmatch(name): errors.append(f"{path}: invalid package name")
        elif name in seen: errors.append(f"{path}: duplicate package {name}")
        else: seen.add(name)
        if not isinstance(data.get("version"), str) or not SEMVER.fullmatch(data["version"]): errors.append(f"{path}: version must be semver")
        for required in ("kind", "dependencies", "permissions", "compatibility"):
            if required not in data: errors.append(f"{path}: missing {required}")
        if not isinstance(data.get("dependencies"), list) or not all(isinstance(item, str) and PACKAGE.fullmatch(item) for item in data.get("dependencies", [])): errors.append(f"{path}: invalid dependencies")
    for path in sorted((ROOT / "plugin").glob("*/.codex-plugin/plugin.json")):
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error: errors.append(f"{path}: invalid JSON: {error.msg}"); continue
        interface = data.get("interface")
        for required in ("name", "version", "description", "author", "interface"):
            if required not in data: errors.append(f"{path}: missing {required}")
        if not isinstance(data.get("name"), str) or not PACKAGE.fullmatch(data["name"]): errors.append(f"{path}: invalid plugin name")
        if not isinstance(data.get("version"), str) or not SEMVER.fullmatch(data["version"]): errors.append(f"{path}: plugin version must be semver")
        if not isinstance(data.get("author"), dict) or not isinstance(data["author"].get("name"), str): errors.append(f"{path}: author.name is required")
        if not isinstance(interface, dict) or any(not interface.get(key) for key in ("displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities")): errors.append(f"{path}: incomplete interface metadata")
        skills = data.get("skills")
        if skills and not (path.parents[1] / str(skills)).is_dir(): errors.append(f"{path}: missing skill path {skills}")
    opencode = ROOT / "plugin" / "devbuddy-core" / "opencode"
    for required in ("index.js", "package.json", "agents/orchestrator.md", "tools/approval-contract.json"):
        if not (opencode / required).is_file(): errors.append(f"missing OpenCode adapter component: {required}")
    for path in sorted((ROOT / "plugin").glob("devbuddy-database-*/tool.json")):
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error: errors.append(f"{path}: invalid JSON: {error.msg}"); continue
        if data.get("permission_tier") != 2 or data.get("risk") != "database-read": errors.append(f"{path}: database tool must be Tier 2 database-read")
        scope = data.get("scope", {})
        if not isinstance(scope, dict) or not scope.get("database_id_required") or not scope.get("read_only") or scope.get("approval") != "target-specific": errors.append(f"{path}: incomplete database safety scope")
    missing_dependencies = sorted({dependency for path in (ROOT / "plugin").glob("*/devbuddy.package.json") for dependency in json.loads(path.read_text(encoding="utf-8")).get("dependencies", []) if dependency not in seen})
    if missing_dependencies: errors.append("missing dependency manifests: " + ", ".join(missing_dependencies))
    if errors:
        print("PACKAGE VALIDATION FAILED\n" + "\n".join(errors)); return 1
    print(f"OK: validated {len(seen)} package manifests and Codex plugin metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
