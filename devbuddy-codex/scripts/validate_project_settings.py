#!/usr/bin/env python3
"""Validate DevBuddy Codex's restricted project settings YAML without packages."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROLES = {"ba-pm", "ux-ui", "architect", "developer", "qa", "security", "devops-sre", "dba-data", "reviewer"}
RISKS = {"low", "medium", "high", "critical"}
SCALARS = {"max_concurrency", "task_timeout_seconds", "retry_limit"}


def list_values(value: str) -> set[str]:
    if not (value.startswith("[") and value.endswith("]")):
        return set()
    return {part.strip() for part in value[1:-1].split(",") if part.strip()}


def parse(path: Path) -> tuple[dict[str, str], dict[str, list[dict[str, str]]], list[str]]:
    scalars: dict[str, str] = {}
    groups = {"approved_models": [], "approved_effort_levels": []}
    errors: list[str] = []
    group: str | None = None
    entry: dict[str, str] | None = None
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw == "schema_version: 1":
            scalars["schema_version"] = "1"
            continue
        if raw == "orchestration:":
            continue
        group_match = re.match(r"^  (approved_models|approved_effort_levels):$", raw)
        if group_match:
            group, entry = group_match.group(1), None
            continue
        scalar_match = re.match(r"^  (max_concurrency|task_timeout_seconds|retry_limit):\s*(\d+)\s*$", raw)
        if scalar_match:
            scalars[scalar_match.group(1)] = scalar_match.group(2)
            continue
        item_match = re.match(r"^    - id:\s*([A-Za-z0-9._-]+)\s*$", raw)
        if item_match and group:
            entry = {"id": item_match.group(1)}
            groups[group].append(entry)
            continue
        field_match = re.match(r"^      (rank|allowed_roles|allowed_risks):\s*(.+?)\s*$", raw)
        if field_match and entry is not None:
            entry[field_match.group(1)] = field_match.group(2)
            continue
        if raw.startswith(" "):
            errors.append(f"line {number}: unsupported restricted-YAML shape")
    return scalars, groups, errors


def validate_entries(kind: str, entries: list[dict[str, str]], errors: list[str]) -> None:
    if not entries:
        errors.append(f"{kind} must contain at least one entry")
        return
    ids: set[str] = set()
    ranks: set[int] = set()
    for entry in entries:
        missing = {"id", "rank", "allowed_roles", "allowed_risks"} - set(entry)
        if missing:
            errors.append(f"{kind} {entry.get('id', '<unknown>')}: missing " + ", ".join(sorted(missing)))
            continue
        if entry["id"] in ids:
            errors.append(f"{kind}: duplicate id {entry['id']}")
        ids.add(entry["id"])
        if not entry["rank"].isdigit() or int(entry["rank"]) < 1:
            errors.append(f"{kind} {entry['id']}: rank must be a positive integer")
        elif int(entry["rank"]) in ranks:
            errors.append(f"{kind}: duplicate rank {entry['rank']}")
        else:
            ranks.add(int(entry["rank"]))
        roles, risks = list_values(entry["allowed_roles"]), list_values(entry["allowed_risks"])
        if not roles or not roles <= ROLES:
            errors.append(f"{kind} {entry['id']}: allowed_roles must contain canonical roles")
        if not risks or not risks <= RISKS:
            errors.append(f"{kind} {entry['id']}: allowed_risks must contain low/medium/high/critical")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("settings", type=Path)
    args = parser.parse_args()
    if not args.settings.is_file():
        print(f"ERROR: settings file not found: {args.settings}")
        return 1
    scalars, groups, errors = parse(args.settings)
    if scalars.get("schema_version") != "1":
        errors.append("schema_version must be 1")
    for key in SCALARS:
        if key not in scalars:
            errors.append(f"missing orchestration.{key}")
    if "max_concurrency" in scalars and int(scalars["max_concurrency"]) < 1:
        errors.append("max_concurrency must be at least 1")
    if "task_timeout_seconds" in scalars and int(scalars["task_timeout_seconds"]) < 1:
        errors.append("task_timeout_seconds must be at least 1")
    validate_entries("approved_models", groups["approved_models"], errors)
    validate_entries("approved_effort_levels", groups["approved_effort_levels"], errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {args.settings} has valid dispatch settings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
