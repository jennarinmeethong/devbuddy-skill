#!/usr/bin/env python3
"""Resolve a profile package graph and optionally record it in .devbuddy."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[a-z0-9-]+$")


def profile(path: Path) -> tuple[str, list[str], list[str]]:
    name = ""; packages: list[str] = []; hosts: list[str] = []; active = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"^name:\s*([a-z0-9-]+)\s*$", raw): name = match.group(1)
        elif raw.strip() == "hosts:": active = False
        elif raw.strip() == "packages:": active = True
        elif not active and (match := re.match(r"^\s*-\s*(codex|claude-code|opencode)\s*$", raw)): hosts.append(match.group(1))
        elif active and (match := re.match(r"^\s*-\s*([a-z0-9-]+)\s*$", raw)): packages.append(match.group(1))
    if not NAME.fullmatch(name) or not packages or len(set(packages)) != len(packages) or len(set(hosts)) != len(hosts): raise ValueError(f"invalid profile: {path}")
    return name, packages, hosts


def manifests() -> dict[str, dict[str, object]]:
    result = {}
    for item in (ROOT / "plugin").glob("*/devbuddy.package.json"):
        data = json.loads(item.read_text(encoding="utf-8")); name = data.get("name")
        if not isinstance(name, str) or name in result: raise ValueError(f"invalid or duplicate package manifest: {item}")
        result[name] = data
    return result


def validate_catalog(catalog: dict[str, dict[str, object]]) -> None:
    core = catalog.get("devbuddy-core")
    if core is None:
        raise ValueError("devbuddy-core package manifest is required")
    core_version = core.get("version")
    if not isinstance(core_version, str):
        raise ValueError("devbuddy-core has no valid version")
    tool_ids: dict[str, Path] = {}
    for package, data in catalog.items():
        compatibility = data.get("compatibility", {})
        if not isinstance(compatibility, dict) or compatibility.get("core") != core_version:
            raise ValueError(f"package incompatible with devbuddy-core {core_version}: {package}")
        path = ROOT / "plugin" / package / "tool.json"
        if path.is_file():
            tool = json.loads(path.read_text(encoding="utf-8")); identifier = tool.get("id")
            if not isinstance(identifier, str): raise ValueError(f"tool has no ID: {path}")
            if identifier in tool_ids: raise ValueError(f"tool ID conflict {identifier}: {tool_ids[identifier]} and {path}")
            tool_ids[identifier] = path


def resolve(requested: list[str], catalog: dict[str, dict[str, object]]) -> list[str]:
    ordered: list[str] = []; visiting: set[str] = set(); seen: set[str] = set()
    def visit(name: str) -> None:
        if name in visiting: raise ValueError(f"cyclic dependency at {name}")
        if name in seen: return
        data = catalog.get(name)
        if data is None: raise ValueError(f"missing package: {name}")
        visiting.add(name)
        for dependency in data.get("dependencies", []): visit(dependency)
        visiting.remove(name); seen.add(name); ordered.append(name)
    for item in requested: visit(item)
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--platform", choices=("codex", "claude-code", "opencode"), help="host to resolve; defaults to a profile's sole declared host or codex")
    parser.add_argument("--devbuddy-root", type=Path, help="workspace .devbuddy root")
    parser.add_argument("--operation", choices=("install", "upgrade", "uninstall"), default="install")
    parser.add_argument("--apply", action="store_true", help="write package composition; otherwise dry-run")
    args = parser.parse_args()
    try:
        name, requested, hosts = profile(args.profile)
        platform = args.platform or (hosts[0] if len(hosts) == 1 else "codex")
        if hosts and platform not in hosts:
            raise ValueError(f"profile {name} does not select platform {platform}")
        catalog = manifests(); validate_catalog(catalog); packages = resolve(requested, catalog)
        incompatible = [item for item in packages if platform not in catalog[item]["compatibility"]["platforms"]]
        if incompatible: raise ValueError("platform incompatible: " + ", ".join(incompatible))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}"); return 1
    permissions = sorted({permission for item in packages for permission in catalog[item].get("permissions", [])})
    current: list[str] = []
    target: Path | None = None
    if args.devbuddy_root is not None:
        target = args.devbuddy_root.resolve() / "packages.json"
        if target.is_file():
            try:
                data = json.loads(target.read_text(encoding="utf-8")); current = data.get("packages", [])
                if not isinstance(current, list) or not all(isinstance(item, str) for item in current): raise ValueError("packages must be a string array")
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print(f"ERROR: invalid existing composition: {error}"); return 1
    desired = [] if args.operation == "uninstall" else packages
    result = {
        "profile": name,
        "operation": args.operation,
        "platform": platform,
        "profile_hosts": hosts,
        "packages": desired,
        "permissions": permissions if desired else [],
        "changes": {"add": [item for item in desired if item not in current], "keep": [item for item in desired if item in current], "remove": [item for item in current if item not in desired]},
    }
    print(json.dumps(result, indent=2))
    if not args.apply:
        print("DRY RUN: no workspace changes")
        return 0
    if args.devbuddy_root is None or args.devbuddy_root.name != ".devbuddy":
        print("ERROR: --apply requires --devbuddy-root pointing to .devbuddy")
        return 1
    assert target is not None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"APPLIED: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
