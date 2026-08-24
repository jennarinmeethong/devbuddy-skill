#!/usr/bin/env python3
"""Inventory every packaged DevBuddy asset with owner, tier, and provenance.

The command is read-only unless --apply is supplied. The generated report is
review evidence for the Plugin-first migration; it intentionally excludes
workspace state and does not inspect user configuration roots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "package-source-map.json"
DEFAULT_REPORT = ROOT / "reports" / "plugin-runtime-inventory.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_mappings() -> list[tuple[str, Path, Path]]:
    data = json.loads(MAP.read_text(encoding="utf-8"))
    result: list[tuple[str, Path, Path]] = []
    for package in data["packages"]:
        for entry in package["sources"]:
            result.append((package["name"], ROOT / entry["from"], ROOT / entry["to"]))
    return result


def classification(relative: Path, mapped_source: Path | None) -> str:
    name = relative.as_posix()
    if mapped_source is not None and mapped_source.as_posix().startswith("skills/"):
        return "portable-policy"
    if "opencode/" in name or "devbuddy-claude-code/" in name or "/agents/" in name or "/skills/" in name:
        return "host-adapter-payload"
    if name.endswith("devbuddy.package.json") or ".codex-plugin/" in name or ".claude-plugin/" in name:
        return "package-control-metadata"
    if "/tool.json" in name or "/runtime/" in name or "/src/" in name or "/templates/" in name:
        return "package-runtime"
    return "package-runtime"


def provenance(path: Path, mappings: list[tuple[str, Path, Path]]) -> str:
    for _package, source, target in mappings:
        if target.is_file() and path == target:
            return source.relative_to(ROOT).as_posix()
        if target.is_dir() and path.is_relative_to(target):
            return (source / path.relative_to(target)).relative_to(ROOT).as_posix()
    return "package-owned"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the report; otherwise print a dry run")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    mappings = source_mappings()
    manifests = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / "plugin").glob("*/devbuddy.package.json")
    }
    assets: list[dict[str, str | list[str]]] = []
    for owner, manifest in sorted(manifests.items()):
        package_root = ROOT / "plugin" / owner
        for path in sorted(package_root.rglob("*")):
            if not path.is_file() or set(path.parts) & {"__pycache__", "bin", "obj", "releases", ".venv", "node_modules"}:
                continue
            mapped = next((source for package, source, target in mappings if package == owner and ((target.is_file() and path == target) or (target.is_dir() and path.is_relative_to(target)))), None)
            assets.append({
                "path": path.relative_to(ROOT).as_posix(),
                "owner": owner,
                "classification": classification(path.relative_to(ROOT), mapped),
                "permissions": manifest["permissions"],
                "provenance": provenance(path, mappings),
                "sha256": sha256(path),
            })
    report = {"schema_version": 1, "asset_count": len(assets), "assets": assets}
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if not args.apply:
        print(json.dumps({"asset_count": len(assets), "output": str(args.output), "status": "dry-run"}, indent=2))
        return 0
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized, encoding="utf-8")
    print(f"APPLIED: wrote {len(assets)} asset records to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
