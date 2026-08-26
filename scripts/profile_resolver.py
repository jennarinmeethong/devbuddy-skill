#!/usr/bin/env python3
"""Resolve and safely add or remove DevBuddy profile compositions.

Profiles are declarative package and agent-role presets. A workspace stores
the selected profile names, so a later add/remove can recalculate dependencies
and safely remove packages no longer selected.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[a-z0-9-]+$")
PLATFORMS = ("codex", "claude-code", "opencode")


def read_profile(path: Path) -> tuple[str, list[str], list[str], list[str]]:
    """Parse the intentionally small profile YAML subset without a dependency."""
    name = ""
    values = {"hosts": [], "packages": [], "roles": []}
    active: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"^name:\s*([a-z0-9-]+)\s*$", raw):
            name = match.group(1); active = None
        elif match := re.match(r"^(hosts|packages|roles):\s*$", raw):
            active = match.group(1)
        elif active and (match := re.match(r"^\s*-\s*([a-z0-9-]+)\s*$", raw)):
            values[active].append(match.group(1))
        elif raw and not raw.lstrip().startswith("#"):
            active = None
    hosts, packages, roles = values["hosts"], values["packages"], values["roles"]
    if (not NAME.fullmatch(name) or not packages or len(set(packages)) != len(packages)
            or len(set(hosts)) != len(hosts) or len(set(roles)) != len(roles)
            or any(host not in PLATFORMS for host in hosts)):
        raise ValueError(f"invalid profile: {path}")
    return name, packages, hosts, roles


def profile_catalog() -> dict[str, Path]:
    catalog: dict[str, Path] = {}
    for path in sorted((ROOT / "profiles").glob("*.yaml")):
        name, _packages, _hosts, _roles = read_profile(path)
        if name in catalog:
            raise ValueError(f"duplicate profile name: {name}")
        catalog[name] = path
    return catalog


def resolve_profile_ref(value: str, catalog: dict[str, Path]) -> Path:
    candidate = Path(value)
    if candidate.is_file():
        return candidate
    if value in catalog:
        return catalog[value]
    raise ValueError(f"unknown profile: {value}; use --list to see built-in profiles")


def manifests() -> dict[str, dict[str, object]]:
    result = {}
    for item in (ROOT / "plugin").glob("*/devbuddy.package.json"):
        data = json.loads(item.read_text(encoding="utf-8")); name = data.get("name")
        if not isinstance(name, str) or name in result:
            raise ValueError(f"invalid or duplicate package manifest: {item}")
        result[name] = data
    return result


def validate_catalog(catalog: dict[str, dict[str, object]]) -> None:
    core = catalog.get("devbuddy-core")
    if core is None or not isinstance(core.get("version"), str):
        raise ValueError("devbuddy-core has no valid version")
    core_version = core["version"]
    tool_ids: dict[str, Path] = {}
    for package, data in catalog.items():
        compatibility = data.get("compatibility", {})
        if not isinstance(compatibility, dict) or compatibility.get("core") != core_version:
            raise ValueError(f"package incompatible with devbuddy-core {core_version}: {package}")
        path = ROOT / "plugin" / package / "tool.json"
        if path.is_file():
            identifier = json.loads(path.read_text(encoding="utf-8")).get("id")
            if not isinstance(identifier, str):
                raise ValueError(f"tool has no ID: {path}")
            if identifier in tool_ids:
                raise ValueError(f"tool ID conflict {identifier}: {tool_ids[identifier]} and {path}")
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


def load_state(root: Path | None) -> tuple[list[str], list[str], str | None]:
    if root is None or not (target := root.resolve() / "packages.json").is_file():
        return [], [], None
    try:
        data = json.loads(target.read_text(encoding="utf-8")); packages = data.get("packages", [])
        profiles = data.get("profiles")
        if profiles is None and isinstance(data.get("profile"), str): profiles = [data["profile"]]
        if not isinstance(packages, list) or not all(isinstance(item, str) for item in packages):
            raise ValueError("packages must be a string array")
        if not isinstance(profiles, list) or not all(isinstance(item, str) and NAME.fullmatch(item) for item in profiles):
            raise ValueError("profiles must be a string array")
        platform = data.get("platform")
        if platform is not None and platform not in PLATFORMS:
            raise ValueError("platform must be a supported host")
        return packages, profiles, platform
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid existing composition: {error}") from None


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", nargs="?", help="profile path or built-in profile name")
    parser.add_argument("--list", action="store_true", help="list built-in profiles")
    parser.add_argument("--add-profile", metavar="PROFILE", help="add a profile to the active workspace composition")
    parser.add_argument("--remove-profile", metavar="PROFILE", help="remove a profile from the active workspace composition")
    parser.add_argument("--status", action="store_true", help="show the active workspace profile composition")
    parser.add_argument("--platform", choices=PLATFORMS, help="host to resolve; defaults to a profile's sole host or codex")
    parser.add_argument("--devbuddy-root", type=Path, help="workspace .devbuddy root")
    parser.add_argument("--operation", choices=("install", "upgrade", "uninstall"), default="install")
    parser.add_argument("--apply", action="store_true", help="write package composition; otherwise dry-run")
    args = parser.parse_args()
    modes = sum(bool(value) for value in (args.profile, args.add_profile, args.remove_profile, args.status, args.list))
    if modes != 1: parser.error("choose exactly one profile, --add-profile, --remove-profile, --status, or --list")
    if (args.add_profile or args.remove_profile or args.status) and args.devbuddy_root is None:
        parser.error("profile changes and --status require --devbuddy-root")
    if (args.add_profile or args.remove_profile) and args.operation != "install":
        parser.error("--add-profile and --remove-profile use the install operation automatically")
    if args.apply and (args.devbuddy_root is None or args.devbuddy_root.name != ".devbuddy"):
        parser.error("--apply requires --devbuddy-root pointing to .devbuddy")
    try:
        profiles_by_name = profile_catalog()
        if args.list:
            print(json.dumps([{"profile": name, "packages": packages, "roles": roles, "hosts": hosts}
                              for name, path in profiles_by_name.items()
                              for name, packages, hosts, roles in [read_profile(path)]], indent=2))
            return 0
        current, active_profiles, active_platform = load_state(args.devbuddy_root)
        if args.status:
            print(json.dumps({"profiles": active_profiles, "platform": active_platform, "packages": current}, indent=2)); return 0
        action = args.operation
        if args.profile:
            selected_data = [read_profile(resolve_profile_ref(args.profile, profiles_by_name))]
        else:
            requested_name = args.add_profile or args.remove_profile
            assert requested_name is not None
            name, _packages, _hosts, _roles = read_profile(resolve_profile_ref(requested_name, profiles_by_name))
            if args.add_profile:
                if name in active_profiles: raise ValueError(f"profile is already active: {name}")
                selected_names = [*active_profiles, name]; action = "add-profile"
            else:
                if name not in active_profiles: raise ValueError(f"profile is not active: {name}")
                selected_names = [item for item in active_profiles if item != name]; action = "remove-profile"
            selected_data = [read_profile(profiles_by_name[name]) for name in selected_names]
        selected = [name for name, _packages, _hosts, _roles in selected_data]
        requested = [package for _name, packages, _hosts, _roles in selected_data for package in packages]
        hosts = [host for _name, _packages, host_list, _roles in selected_data for host in host_list]
        roles = [role for _name, _packages, _hosts, role_list in selected_data for role in role_list]
        platform = args.platform or active_platform or (hosts[0] if len(set(hosts)) == 1 and hosts else "codex")
        incompatible_profiles = [name for name, _packages, declared_hosts, _roles in selected_data if declared_hosts and platform not in declared_hosts]
        if incompatible_profiles: raise ValueError(f"profile platform incompatible: {', '.join(incompatible_profiles)} does not select {platform}")
        catalog = manifests(); validate_catalog(catalog); packages = resolve(unique(requested), catalog)
        incompatible_packages = [item for item in packages if platform not in catalog[item]["compatibility"]["platforms"]]
        if incompatible_packages: raise ValueError("platform incompatible: " + ", ".join(incompatible_packages))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}"); return 1
    desired = [] if args.operation == "uninstall" else packages
    desired_profiles = [] if args.operation == "uninstall" else selected
    result = {
        "profile": desired_profiles[0] if len(desired_profiles) == 1 else None,
        "profiles": desired_profiles, "agent_roles": unique(roles) if desired else [],
        "operation": action, "platform": platform, "profile_hosts": unique(hosts), "packages": desired,
        "permissions": sorted({permission for item in desired for permission in catalog[item].get("permissions", [])}),
        "changes": {"add": [item for item in desired if item not in current], "keep": [item for item in desired if item in current], "remove": [item for item in current if item not in desired]},
    }
    print(json.dumps(result, indent=2))
    if not args.apply:
        print("DRY RUN: no workspace changes"); return 0
    target = args.devbuddy_root.resolve() / "packages.json"; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"APPLIED: {target}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
