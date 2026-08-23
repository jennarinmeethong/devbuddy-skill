#!/usr/bin/env python3
"""Validate a DevBuddy portable task record without accepting secret-shaped data."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SECRET = re.compile(r"(?i)(password|access[_ -]?token|api[_ -]?key|connection\s*string)")


def has_secret(value: object) -> bool:
    if isinstance(value, dict): return any(SECRET.search(str(key)) or has_secret(item) for key, item in value.items())
    if isinstance(value, list): return any(has_secret(item) for item in value)
    return isinstance(value, str) and bool(re.search(r"(?i)(password=|://[^\s/@]+:[^\s/@]+@|AKIA[0-9A-Z]{16})", value))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("record", type=Path); args = parser.parse_args()
    try: data = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: print(f"ERROR: invalid task record: {error}"); return 1
    errors: list[str] = []
    required = {"schema_version", "task_id", "state", "requested_operation", "risk", "allowed_scope", "approval", "knowledge_impact", "required_evidence", "evidence", "closure"}
    if missing := required - data.keys(): errors.append("missing fields: " + ", ".join(sorted(missing)))
    if data.get("schema_version") != 1 or not TASK_ID.fullmatch(str(data.get("task_id", ""))): errors.append("invalid task identity")
    if data.get("state") not in {"planned", "running", "waiting_approval", "blocked", "completed"}: errors.append("invalid task state")
    approval = data.get("approval", {})
    if not isinstance(approval, dict) or approval.get("tier") not in {0, 1, 2} or approval.get("state") not in {"not_required", "pending", "approved", "denied"}: errors.append("invalid approval state")
    elif approval["tier"] == 0 and approval["state"] != "not_required": errors.append("Tier 0 approval must be not_required")
    if not isinstance(data.get("allowed_scope"), list) or not data["allowed_scope"]: errors.append("allowed_scope is required")
    if has_secret(data): errors.append("task records must not contain secrets")
    if data.get("state") == "completed":
        if not data.get("evidence"): errors.append("completed task requires evidence")
        criteria = data.get("closure", {}).get("criteria", []) if isinstance(data.get("closure"), dict) else []
        if not criteria or any(not isinstance(item, dict) or item.get("status") != "passed" for item in criteria): errors.append("completed task requires passed closure criteria")
    if errors: print("ERROR: " + "; ".join(errors)); return 1
    print(f"OK: task contract validates: {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
