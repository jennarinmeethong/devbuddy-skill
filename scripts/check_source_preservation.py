#!/usr/bin/env python3
"""Ensure the additive implementation has not modified legacy DevBuddy sources."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ("devbuddy-source-of-truth", "devbuddy-codex", "devbuddy-claude")


def main() -> int:
    changed = subprocess.run(["git", "diff", "--name-only", "--", *LEGACY], cwd=ROOT, capture_output=True, text=True, check=False)
    staged = subprocess.run(["git", "diff", "--cached", "--name-only", "--", *LEGACY], cwd=ROOT, capture_output=True, text=True, check=False)
    files = sorted({*changed.stdout.splitlines(), *staged.stdout.splitlines()} - {""})
    if files:
        print("SOURCE PRESERVATION FAILED")
        print("\n".join(files))
        return 1
    print("OK: legacy DevBuddy source and adapters are unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
