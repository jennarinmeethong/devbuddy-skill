#!/usr/bin/env python3
"""Check required DevBuddy manual pages and basic metadata."""
from __future__ import annotations

import argparse
from pathlib import Path

PAGES = [
    "index.html", "th/index.html", "en/index.html",
    "th/claude.html", "th/codex.html", "en/claude.html", "en/codex.html",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manual_root", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    for relative in PAGES:
        path = args.manual_root / relative
        if not path.is_file():
            errors.append(f"missing manual page: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        if "data-manual-version=" not in text:
            errors.append(f"{relative}: missing data-manual-version")
        if relative != "index.html" and "lang=" not in text:
            errors.append(f"{relative}: missing language metadata")
    if not (args.manual_root / "assets" / "style.css").is_file():
        errors.append("missing manual stylesheet")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: manual conformance passed for {args.manual_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
