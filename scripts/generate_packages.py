#!/usr/bin/env python3
"""Safely sync portable sources into DevBuddy package staging or targets.

The default is a dry run.  Existing generated targets are never overwritten
unless --apply --overwrite are both supplied.  This keeps legacy sources and
locally changed package files safe by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "package-source-map.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(source: Path, destination: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for item in sorted(source.rglob("*")):
        if not item.is_file() or "__pycache__" in item.parts:
            continue
        relative = item.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        entries.append({"path": relative.as_posix(), "sha256": digest(item)})
    return entries


def revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write generated package content")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing generated destination; requires --apply")
    parser.add_argument("--staging", type=Path, help="write to an isolated staging directory")
    args = parser.parse_args()
    if args.overwrite and not args.apply:
        parser.error("--overwrite requires --apply")
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    if mapping.get("schema_version") != 1:
        print("ERROR: unsupported source-map schema")
        return 1
    if args.staging:
        output_root = args.staging.resolve()
    else:
        output_root = ROOT
    plans: list[tuple[Path, Path]] = []
    for package in mapping.get("packages", []):
        for entry in package.get("sources", []):
            source = ROOT / entry["from"]
            destination = output_root / entry["to"]
            if not source.is_dir():
                print(f"ERROR: mapped source does not exist: {source}")
                return 1
            plans.append((source, destination))
    conflicts = [target for _source, target in plans if target.exists() and not args.staging]
    for source, target in plans:
        print(f"SYNC: {source.relative_to(ROOT)} -> {target.relative_to(output_root)}")
    if conflicts and not args.overwrite:
        print("CONFLICT: destinations already exist; pass --apply --overwrite to replace generated content")
        return 2
    if not args.apply:
        print("DRY RUN: no files written")
        return 0
    records: list[dict[str, object]] = []
    source_revision = revision()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for source, target in plans:
        if target.exists():
            shutil.rmtree(target)
        files = copy_tree(source, target)
        (target / ".devbuddy-generation.json").write_text(json.dumps({
            "schema_version": 1,
            "provenance": str(source.relative_to(ROOT)).replace("\\", "/"),
            "source_revision": source_revision,
            "generated_at": generated_at,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        records.append({"source": str(source.relative_to(ROOT)).replace("\\", "/"), "target": str(target.relative_to(output_root)).replace("\\", "/"), "files": files})
    report = {"schema_version": 1, "source_revision": source_revision, "generated_at": generated_at, "mappings": records}
    (output_root / "generation-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: generated {len(records)} mapping(s) at {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
