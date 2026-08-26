#!/usr/bin/env python3
"""Register an already materialized Plugin-owned database adapter; dry-run first."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from workspace import DATABASE_ID, ENGINES, database_profiles


def root(value: Path) -> Path:
    selected = value.resolve()
    if selected.name != ".devbuddy" or not (selected / "settings.yaml").is_file():
        raise ValueError("--devbuddy-root must name an initialized .devbuddy workspace")
    return selected


def registry_entry(args: argparse.Namespace) -> str:
    return "\n".join((
        f"  - id: {args.database_id}", f"    engine: {args.engine}", f"    environment: {args.environment}",
        f"    adapter_package: devbuddy-database-{args.engine}", f"    manifest: tools/databases/{args.database_id}/tool.json",
        f"    secret_file: tools/databases/{args.database_id}/appsettings.json", f"    approval: {args.approval}",
        f"    max_rows: {args.max_rows}", f"    timeout_seconds: {args.timeout_seconds}", "",
    ))


def insert_registry(text: str, entry: str) -> str:
    if "databases: []" in text:
        return text.replace("databases: []", "databases:\n" + entry.rstrip(), 1) + ("" if text.endswith("\n") else "\n")
    lines = text.splitlines(keepends=True)
    header = next((index for index, line in enumerate(lines) if line.rstrip("\r\n") == "databases:"), None)
    if header is None:
        return text.rstrip() + "\ndatabases:\n" + entry
    end = len(lines)
    for index in range(header + 1, len(lines)):
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*", lines[index]):
            end = index; break
    lines.insert(end, entry)
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devbuddy-root", type=Path, required=True)
    parser.add_argument("--database-id", required=True)
    parser.add_argument("--engine", choices=sorted(ENGINES), required=True)
    parser.add_argument("--environment", choices=("development", "staging", "production"), default="development")
    parser.add_argument("--approval", choices=("ask", "deny"))
    parser.add_argument("--max-rows", type=int, default=500)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        selected = root(args.devbuddy_root)
        if not DATABASE_ID.fullmatch(args.database_id): raise ValueError("invalid --database-id")
        if not 1 <= args.max_rows <= 5000 or not 1 <= args.timeout_seconds <= 120: raise ValueError("limits must be within the policy range")
        args.approval = args.approval or ("ask" if args.environment == "production" else "deny")
        manifest = selected / "tools" / "databases" / args.database_id / "tool.json"
        if not manifest.is_file(): raise ValueError("materialize the selected adapter before registering it")
        text = (selected / "settings.yaml").read_text(encoding="utf-8")
        if args.database_id in {item["id"] for item in database_profiles(text)}: raise ValueError("database ID is already registered")
    except ValueError as error:
        print(f"ERROR: {error}"); return 1
    entry = registry_entry(args)
    print("PLAN: register Plugin-owned database adapter\n" + entry)
    if not args.apply:
        print("DRY RUN: create appsettings.json locally, then pass --apply to update settings.yaml")
        return 0
    (selected / "settings.yaml").write_text(insert_registry(text, entry), encoding="utf-8")
    print("APPLIED: database registry added. Create the local ignored appsettings.json before validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
