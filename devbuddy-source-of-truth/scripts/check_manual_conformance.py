#!/usr/bin/env python3
"""Validate the generated bilingual DevBuddy documentation manual."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

VERSION = "0.4.6"
COMMON = ["index", "getting-started", "workspace", "scripts", "tasks-and-knowledge", "migration", "troubleshooting", "plugin-first", "git-install", "database-profiles"]
REQUIRED_SCRIPTS = ("init_project_memory.py", "bootstrap_knowledge.py", "task_memory.py", "validate_project_settings.py", "validate_knowledge.py")
HREF = re.compile(r'href="([^"]+)"')
ANCHOR = re.compile(r'id="([^"]+)"')


def pages(root: Path, adapters: tuple[str, ...] = ("codex", "claude")) -> list[str]:
    result = ["index.html"]
    for language in ("en", "th"):
        result.extend(f"{language}/{page}.html" for page in COMMON)
        result.extend(f"{language}/{page}.html" for page in adapters)
    return result


def check_root(root: Path, adapters: tuple[str, ...] = ("codex", "claude")) -> int:
    """Validate one manual root.

    Adapters call this directly with their own single-adapter tuple, so the
    arguments must be honoured as passed; re-reading sys.argv here would ignore
    the caller and silently validate the wrong root.
    """
    errors: list[str] = []
    expected = pages(root, adapters)
    texts: dict[str, str] = {}
    for relative in expected:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing manual page: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        texts[relative] = text
        if f'data-manual-version="{VERSION}"' not in text:
            errors.append(f"{relative}: version must be {VERSION}")
        if relative != "index.html" and not re.search(r'<html[^>]+lang="(?:en|th)"', text):
            errors.append(f"{relative}: missing language metadata")
        if relative != "index.html" and ('id="main"' not in text or 'class="sidebar"' not in text or 'class="toc"' not in text):
            errors.append(f"{relative}: missing documentation layout landmarks")
        anchors = ANCHOR.findall(text)
        if len(anchors) != len(set(anchors)):
            errors.append(f"{relative}: duplicate anchor IDs")
        for href in HREF.findall(text):
            if href.startswith("#"):
                if href[1:] not in anchors:
                    errors.append(f"{relative}: broken anchor {href}")
            elif not href.startswith(("http://", "https://", "mailto:")):
                target = href.split("#", 1)[0]
                if target and not (path.parent / target).is_file():
                    errors.append(f"{relative}: broken link {href}")
        if relative.endswith("/scripts.html"):
            for script in REQUIRED_SCRIPTS:
                if script not in text:
                    errors.append(f"{relative}: missing runtime script inventory entry {script}")
        if re.search(r"scripts/(?:bootstrap_knowledge|task_memory|validate_knowledge|validate_project_settings)\.py", text):
            errors.append(f"{relative}: runtime command still points at global scripts/")
        if "--project-root" in text:
            errors.append(f"{relative}: legacy --project-root command remains")

    for page in COMMON + list(adapters):
        en = texts.get(f"en/{page}.html", "")
        th = texts.get(f"th/{page}.html", "")
        en_ids = set(ANCHOR.findall(en))
        th_ids = set(ANCHOR.findall(th))
        if len(en_ids) != len(th_ids):
            errors.append(f"language parity mismatch for {page}: en={len(en_ids)} sections, th={len(th_ids)} sections")
    for asset in ("assets/style.css", "assets/manual.js"):
        if not (root / asset).is_file():
            errors.append(f"missing manual asset: {asset}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: manual {VERSION} conformance passed for {root}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manual_root", type=Path)
    args = parser.parse_args()
    return check_root(args.manual_root)


if __name__ == "__main__":
    raise SystemExit(main())
