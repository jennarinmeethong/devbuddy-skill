#!/usr/bin/env python3
"""Ensure the additive implementation has not modified legacy DevBuddy sources."""
from __future__ import annotations

import subprocess
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ("devbuddy-source-of-truth", "devbuddy-codex", "devbuddy-claude")
ALLOWLIST = ROOT / "source-change-allowlist.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approved_changes() -> dict[str, str]:
    if not ALLOWLIST.is_file():
        return {}
    try:
        data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if data.get("schema_version") != 1 or not isinstance(data.get("files"), list):
        return {}
    return {
        item["path"]: item["sha256"]
        for item in data["files"]
        if isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str)
    }


def main() -> int:
    changed = subprocess.run(["git", "diff", "--name-only", "--", *LEGACY], cwd=ROOT, capture_output=True, text=True, check=False)
    staged = subprocess.run(["git", "diff", "--cached", "--name-only", "--", *LEGACY], cwd=ROOT, capture_output=True, text=True, check=False)
    files = sorted({*changed.stdout.splitlines(), *staged.stdout.splitlines()} - {""})
    approved = approved_changes()
    unexpected = []
    for relative in files:
        expected = approved.get(relative)
        path = ROOT / relative
        if expected is None or not path.is_file() or sha256(path) != expected:
            unexpected.append(relative)
    if unexpected:
        print("SOURCE PRESERVATION FAILED")
        print("\n".join(unexpected))
        return 1
    if files:
        print(f"OK: {len(files)} approved legacy source change(s) match {ALLOWLIST.name}")
    else:
        print("OK: legacy DevBuddy source and adapters are unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
