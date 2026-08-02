#!/usr/bin/env python3
"""Validate the generated Claude Code manual using the common checker."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "devbuddy-source-of-truth" / "scripts" / "check_manual_conformance.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manual_root", type=Path)
    args = parser.parse_args()
    namespace = {"__name__": "manual_checker", "__file__": str(ROOT)}
    exec(compile(ROOT.read_text(encoding="utf-8"), str(ROOT), "exec"), namespace)
    return int(namespace["check_root"](args.manual_root, ("claude",)))


if __name__ == "__main__":
    raise SystemExit(main())
