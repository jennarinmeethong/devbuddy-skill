#!/usr/bin/env python3
"""Fail if package artifacts contain a secret file or credential-shaped value."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = ("plugin", "profiles", "skills", "schemas", "scripts", "package-source-map.json", "generation-report.json")
PATTERNS = (
    re.compile(r"(?i)(?:password|pwd)\s*=\s*(?![|\[<]|__[A-Z0-9_]+__)[^\s;\"'|]{8,}"),
    re.compile(r"(?i)(?:postgres(?:ql)?|mongodb(?:\+srv)?|redis|mysql|sqlserver)://(?!__[A-Z0-9_]+__)[^\s\"']+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def main() -> int:
    findings: list[dict[str, str]] = []
    for raw in SCAN_ROOTS:
        path = ROOT / raw
        files = list(path.rglob("*")) if path.is_dir() else [path]
        for item in files:
            if not item.is_file():
                continue
            relative = item.relative_to(ROOT).as_posix()
            if item.name == "appsettings.json":
                findings.append({"file": relative, "reason": "local secret file must not be packaged"}); continue
            try: text = item.read_text(encoding="utf-8")
            except UnicodeDecodeError: continue
            for pattern in PATTERNS:
                if pattern.search(text):
                    findings.append({"file": relative, "reason": "credential-shaped value"}); break
    tracked = subprocess.run(["git", "ls-files", "**/appsettings.json"], cwd=ROOT, capture_output=True, text=True, check=False)
    for item in tracked.stdout.splitlines(): findings.append({"file": item, "reason": "tracked local secret file"})
    print(json.dumps({"clean": not findings, "findings": findings}, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
