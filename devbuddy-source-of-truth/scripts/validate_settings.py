#!/usr/bin/env python3
"""Validate DevBuddy's dependency-free YAML settings subset."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_TOP = {
    "schema_version", "skill", "governance", "orchestration", "loops",
    "memory", "tools", "environments", "quality", "adapters",
}
REQUIRED_CHILDREN = {
    "skill": {"name", "common_spec_version", "internal_language", "user_language"},
    "orchestration": {"max_concurrency", "task_timeout", "retry_limit", "approved_models", "approved_effort_levels", "adapter_profile_selection", "require_model_and_effort_per_dispatch", "model_effort_selection_policy", "escalation_requires_recorded_reason", "user_update_events"},
    "memory": {"default_root", "project_settings_path", "locator_key", "knowledge_root", "project_registry_key"},
    "adapters": {"claude", "codex"},
}
CANONICAL_MEMORY = {
    "default_root": ".devbuddy",
    "project_settings_path": ".devbuddy/settings.yaml",
    "locator_key": "memory_root",
    "knowledge_root": "knowledge-base",
    "project_registry_key": "workspace.projects",
}


def parse_keys(text: str) -> tuple[set[str], dict[str, set[str]], list[str]]:
    top: set[str] = set()
    children: dict[str, set[str]] = {}
    errors: list[str] = []
    parent: str | None = None
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = re.match(r"^( *)([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)", raw)
        if not match:
            continue
        indent, key = len(match.group(1)), match.group(2)
        if indent == 0:
            top.add(key)
            parent = key
        elif indent == 2 and parent:
            children.setdefault(parent, set()).add(key)
        elif indent % 2:
            errors.append(f"line {number}: indentation must use whole two-space levels")
    return top, children, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("settings", type=Path, help="path to settings.yaml")
    args = parser.parse_args()
    if not args.settings.is_file():
        print(f"ERROR: settings file not found: {args.settings}")
        return 1
    text = args.settings.read_text(encoding="utf-8")
    top, children, errors = parse_keys(text)
    missing = REQUIRED_TOP - top
    if missing:
        errors.append("missing top-level keys: " + ", ".join(sorted(missing)))
    for parent, required in REQUIRED_CHILDREN.items():
        absent = required - children.get(parent, set())
        if absent:
            errors.append(f"missing {parent} keys: " + ", ".join(sorted(absent)))
    for key, expected in CANONICAL_MEMORY.items():
        match = re.search(rf"^  {re.escape(key)}:\s*(\S+)\s*$", text, re.MULTILINE)
        if match is None:
            errors.append(f"memory.{key} must be present")
        elif match.group(1).strip("\"'") != expected:
            errors.append(f"memory.{key} must be {expected}")
    if not re.search(r"^schema_version:\s*1\s*$", text, re.MULTILINE):
        errors.append("schema_version must be 1")
    is_rtk = re.search(r"^  is_rtk:\s*(\S+)\s*$", text, re.MULTILINE)
    if is_rtk and is_rtk.group(1).strip("\"'") not in {"true", "false"}:
        errors.append("tools.is_rtk must be true or false")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {args.settings} validates against schema version 1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
