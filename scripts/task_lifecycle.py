#!/usr/bin/env python3
"""Create and transition portable DevBuddy task records under `.devbuddy/tasks`."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "plugin" / "devbuddy-core" / "task-contract.json").read_text(encoding="utf-8"))
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def record_path(root: Path, task_id: str) -> Path:
    if root.resolve().name != ".devbuddy" or not TASK_ID.fullmatch(task_id): raise ValueError("invalid .devbuddy root or task ID")
    return root.resolve() / "tasks" / task_id / "task.json"


def output(data: dict[str, object], dry_run: bool) -> None:
    print(json.dumps(data, indent=2))
    if dry_run: print("DRY RUN: no task state written")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--devbuddy-root", type=Path, required=True); init.add_argument("--task-id", required=True); init.add_argument("--operation", required=True); init.add_argument("--risk", choices=("low", "medium", "high", "critical"), required=True); init.add_argument("--scope", action="append", required=True); init.add_argument("--tier", choices=("0", "1", "2"), required=True); init.add_argument("--apply", action="store_true")
    transition = sub.add_parser("transition"); transition.add_argument("--devbuddy-root", type=Path, required=True); transition.add_argument("--task-id", required=True); transition.add_argument("--state", choices=CONTRACT["states"], required=True); transition.add_argument("--evidence", action="append", default=[]); transition.add_argument("--closure", action="append", default=[], metavar="ID=STATUS"); transition.add_argument("--knowledge-impact", choices=("none", "proposed", "approved")); transition.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try: path = record_path(args.devbuddy_root, args.task_id)
    except ValueError as error: print(f"ERROR: {error}"); return 1
    if args.command == "init":
        if path.exists(): print(f"ERROR: task already exists: {path}"); return 1
        tier = int(args.tier)
        data: dict[str, object] = {"schema_version": 1, "task_id": args.task_id, "state": "planned", "requested_operation": args.operation, "risk": args.risk, "allowed_scope": args.scope, "approval": {"tier": tier, "state": "not_required" if tier == 0 else "pending"}, "knowledge_impact": "none", "required_evidence": [], "evidence": [], "closure": {"criteria": []}}
    else:
        if not path.is_file(): print(f"ERROR: task not found: {path}"); return 1
        data = json.loads(path.read_text(encoding="utf-8")); current = data.get("state")
        if args.state not in CONTRACT["transitions"].get(current, []): print(f"ERROR: invalid transition {current} -> {args.state}"); return 1
        data["state"] = args.state
        data["evidence"] = [*data.get("evidence", []), *({"ref": value, "outcome": "recorded"} for value in args.evidence)]
        if args.knowledge_impact is not None: data["knowledge_impact"] = args.knowledge_impact
        criteria = data.setdefault("closure", {"criteria": []}).setdefault("criteria", [])
        for value in args.closure:
            if "=" not in value: print("ERROR: closure must use ID=STATUS"); return 1
            identifier, status = value.split("=", 1)
            if not identifier or status not in {"passed", "failed", "skipped"}: print("ERROR: closure status must be passed, failed, or skipped"); return 1
            criteria.append({"id": identifier, "status": status})
        if args.state == "completed" and (not data["evidence"] or not criteria or any(item.get("status") != "passed" for item in criteria)):
            print("ERROR: completed task requires evidence and passed closure criteria"); return 1
    output(data, not args.apply)
    if not args.apply: return 0
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
