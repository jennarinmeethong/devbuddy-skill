#!/usr/bin/env python3
"""Validate required self-contained Claude manual pages."""
from __future__ import annotations

import argparse
from pathlib import Path

PAGES = ["index.html", "en/index.html", "th/index.html", "en/claude.html", "th/claude.html", "assets/style.css"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manual_root", type=Path)
    args = parser.parse_args()
    errors = [f"missing manual artefact: {relative}" for relative in PAGES if not (args.manual_root / relative).is_file()]
    for relative in PAGES[:-1]:
        path = args.manual_root / relative
        if path.is_file() and "data-manual-version=" not in path.read_text(encoding="utf-8"):
            errors.append(f"missing manual revision metadata: {relative}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: Claude manual conformance passed for {args.manual_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
