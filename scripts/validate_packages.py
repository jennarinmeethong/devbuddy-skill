#!/usr/bin/env python3
"""Dependency-free validation for DevBuddy package and Codex plugin metadata."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = re.compile(r"^devbuddy-[a-z0-9-]+$")
PLATFORMS = {"codex", "claude-code", "opencode"}
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
        compatibility = data.get("compatibility")
        platforms = compatibility.get("platforms") if isinstance(compatibility, dict) else None
        if not isinstance(platforms, list) or not platforms or len(platforms) != len(set(platforms)) or not set(platforms) <= PLATFORMS:
            errors.append(f"{path}: invalid compatibility platforms")
        if data.get("kind") == "adapter":
            adapter = data.get("adapter")
            required_adapter = {"host", "entrypoint", "dispatch_transport", "model_transport", "effort_transport", "explicit_invocation", "discovery", "update", "uninstall"}
            if not isinstance(adapter, dict) or set(adapter) != required_adapter:
                errors.append(f"{path}: incomplete adapter contract")
            elif adapter["host"] not in PLATFORMS or adapter["host"] not in platforms or not adapter["explicit_invocation"]:
                errors.append(f"{path}: invalid adapter host or invocation gate")
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
    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append("missing repository Codex marketplace manifest")
        marketplace = None
    except json.JSONDecodeError as error:
        errors.append(f"{marketplace_path}: invalid JSON: {error.msg}")
        marketplace = None
    if marketplace is not None:
        entries = marketplace.get("plugins") if isinstance(marketplace, dict) else None
        if marketplace.get("name") != "devbuddy" or not isinstance(entries, list):
            errors.append(f"{marketplace_path}: invalid DevBuddy marketplace metadata")
        else:
            expected = next((entry for entry in entries if isinstance(entry, dict) and entry.get("name") == "devbuddy-codex"), None)
            if not isinstance(expected, dict):
                errors.append(f"{marketplace_path}: missing devbuddy-codex marketplace entry")
            else:
                source = expected.get("source")
                policy = expected.get("policy")
                if source != {"source": "local", "path": "./plugins/devbuddy-codex"}:
                    errors.append(f"{marketplace_path}: invalid devbuddy-codex source")
                elif not (ROOT / "plugins" / "devbuddy-codex" / ".codex-plugin" / "plugin.json").is_file():
                    errors.append(f"{marketplace_path}: devbuddy-codex source manifest is missing")
                if policy != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"} or not expected.get("category"):
                    errors.append(f"{marketplace_path}: incomplete devbuddy-codex marketplace policy")
    opencode = ROOT / "plugin" / "devbuddy-core" / "opencode"
    for required in ("index.js", "package.json", "agents/orchestrator.md", "tools/approval-contract.json"):
        if not (opencode / required).is_file(): errors.append(f"missing OpenCode adapter component: {required}")
    codex = ROOT / "plugin" / "devbuddy-codex"
    codex_manifest = codex / ".codex-plugin" / "plugin.json"
    codex_skill = codex / "skills" / "devbuddy" / "SKILL.md"
    if not codex_manifest.is_file() or not codex_skill.is_file():
        errors.append("missing Codex adapter package component")
    else:
        try:
            data = json.loads(codex_manifest.read_text(encoding="utf-8"))
            if data.get("name") != "devbuddy-codex" or not SEMVER.fullmatch(str(data.get("version", ""))):
                errors.append(f"{codex_manifest}: invalid Codex adapter plugin metadata")
        except json.JSONDecodeError as error:
            errors.append(f"{codex_manifest}: invalid JSON: {error.msg}")
        if "name: devbuddy" not in codex_skill.read_text(encoding="utf-8"):
            errors.append(f"{codex_skill}: $devbuddy entrypoint metadata missing")
    claude = ROOT / "plugin" / "devbuddy-claude-code"
    manifest = claude / ".claude-plugin" / "plugin.json"
    skill = claude / "skills" / "devbuddy" / "SKILL.md"
    agents = sorted((claude / "agents").glob("devbuddy-*-*.md")) if (claude / "agents").is_dir() else []
    if not manifest.is_file() or not skill.is_file() or len(agents) != 54:
        errors.append("missing Claude Code adapter component or generated agent set")
    else:
        try:
            claude_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            if claude_manifest.get("name") != "devbuddy-claude-code" or not SEMVER.fullmatch(str(claude_manifest.get("version", ""))):
                errors.append(f"{manifest}: invalid Claude Code plugin metadata")
        except json.JSONDecodeError as error:
            errors.append(f"{manifest}: invalid JSON: {error.msg}")
        if "disable-model-invocation: true" not in skill.read_text(encoding="utf-8"):
            errors.append(f"{skill}: explicit invocation gate missing")
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
    print(f"OK: validated {len(seen)} package manifests and host plugin metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
