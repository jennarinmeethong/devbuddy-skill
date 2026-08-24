#!/usr/bin/env python3
"""Report source/package drift without changing either side."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hashes(directory: Path) -> dict[str, str]:
    if directory.is_file():
        return {directory.name: hashlib.sha256(directory.read_bytes()).hexdigest()}
    return {item.relative_to(directory).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest() for item in directory.rglob("*") if item.is_file() and "__pycache__" not in item.parts and item.name != ".devbuddy-generation.json"}


def main() -> int:
    mapping = json.loads((ROOT / "package-source-map.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    for package in mapping["packages"]:
        for entry in package["sources"]:
            source, target = ROOT / entry["from"], ROOT / entry["to"]
            if not target.exists() or (source.is_dir() and not target.is_dir()) or (source.is_file() and not target.is_file()):
                problems.append(f"missing generated target: {target.relative_to(ROOT)}")
                continue
            left, right = hashes(source), hashes(target)
            if left != right:
                problems.append(f"drift: {source.relative_to(ROOT)} != {target.relative_to(ROOT)}")
    if problems:
        print("DRIFT CHECK FAILED")
        print("\n".join(problems))
        return 1
    print("OK: no package drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
