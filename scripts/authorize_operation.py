#!/usr/bin/env python3
"""Evaluate DevBuddy's target-specific approval contract without executing work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def below(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--devbuddy-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="explicitly authorize a Tier 1 workspace mutation")
    parser.add_argument("--approval", type=Path, help="JSON approval record required for Tier 2")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"allowed": False, "reason": f"invalid manifest: {error}"})); return 1
    tier = manifest.get("permission_tier")
    if tier not in {0, 1, 2}:
        print(json.dumps({"allowed": False, "reason": "manifest has no valid permission tier"})); return 1
    if tier == 0:
        print(json.dumps({"allowed": True, "tier": 0, "reason": "read-only operation"})); return 0
    if tier == 1:
        if not args.apply:
            print(json.dumps({"allowed": False, "tier": 1, "reason": "Tier 1 requires --apply"})); return 1
        if not below(Path(args.target), args.devbuddy_root):
            print(json.dumps({"allowed": False, "tier": 1, "reason": "Tier 1 target must be below .devbuddy"})); return 1
        print(json.dumps({"allowed": True, "tier": 1, "reason": "explicit workspace apply"})); return 0
    if args.approval is None:
        print(json.dumps({"allowed": False, "tier": 2, "reason": "Tier 2 requires a target-specific approval record"})); return 1
    try:
        approval = json.loads(args.approval.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"allowed": False, "tier": 2, "reason": f"invalid approval record: {error}"})); return 1
    expected = {"manifest_id": manifest.get("id"), "operation": args.operation, "target": args.target, "approved": True}
    if any(approval.get(key) != value for key, value in expected.items()):
        print(json.dumps({"allowed": False, "tier": 2, "reason": "approval does not match manifest, operation, and target"})); return 1
    if any(key.lower() in {"password", "token", "connection_string", "secret"} for key in approval):
        print(json.dumps({"allowed": False, "tier": 2, "reason": "approval record must not contain secrets"})); return 1
    print(json.dumps({"allowed": True, "tier": 2, "reason": "target-specific approval matched"})); return 0


if __name__ == "__main__":
    raise SystemExit(main())
