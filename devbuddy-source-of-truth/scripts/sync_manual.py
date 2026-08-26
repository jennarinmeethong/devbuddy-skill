#!/usr/bin/env python3
"""Synchronize the canonical offline manual into the adapter manuals.

This is a source/development-only command.  It intentionally copies only the
shared pages, assets, and the adapter-specific page; installed skills never
receive this script.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

COMMON_PAGES = (
    "getting-started.html",
    "workspace.html",
    "scripts.html",
    "tasks-and-knowledge.html",
    "migration.html",
    "troubleshooting.html",
    "plugin-first.html",
    "git-install.html",
)


def rendered(text: str, adapter: str) -> str:
    """Strip everything belonging to the other adapter from a shared page."""
    other = "claude" if adapter == "codex" else "codex"
    # This also removes an adapter-specific next/previous link, which would
    # otherwise point at a page intentionally not shipped in this adapter.
    text = re.sub(rf'<a href="{other}\.html"[^>]*>.*?</a>', "", text, flags=re.DOTALL)
    # A shared page may carry one install block per adapter. Shipping both would
    # put the wrong platform's command in front of a reader who only installed
    # this one, so keep only the block tagged for this adapter.
    return re.sub(
        rf'<div class="code-wrap" data-adapter="{other}">.*?</pre></div>',
        "",
        text,
        flags=re.DOTALL,
    )


def sync(source_root: Path, repository: Path, adapter: str, dry_run: bool) -> int:
    target_root = repository / f"devbuddy-{adapter}" / "manual"
    names = [source_root / "index.html"]
    for language in ("en", "th"):
        names.append(source_root / language / "index.html")
        names.extend(source_root / language / name for name in COMMON_PAGES)
        names.append(source_root / language / f"{adapter}.html")
    paths = names
    paths.extend((source_root / "assets" / name for name in ("style.css", "manual.js")))
    for source in paths:
        if not source.is_file():
            raise FileNotFoundError(source)
        relative = source.relative_to(source_root)
        target = target_root / relative
        content = rendered(source.read_text(encoding="utf-8"), adapter)
        if dry_run:
            print(f"SYNC: {source} -> {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_text(encoding="utf-8") == content:
            print(f"UNCHANGED: {target}")
            continue
        target.write_text(content, encoding="utf-8")
        print(f"OK: synced {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show files without writing")
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    repository = scripts.parents[1]
    source_root = repository / "devbuddy-source-of-truth" / "manual"
    for adapter in ("codex", "claude"):
        sync(source_root, repository, adapter, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
