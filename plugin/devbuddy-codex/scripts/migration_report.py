#!/usr/bin/env python3
"""Inventory a legacy DevBuddy host and workspace without modifying either."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


DOCUMENTS = {
    "BusinessContext.md": {"folder": "domains", "prefix": "DOM"},
    "DecisionLog.md": {"folder": "decisions", "prefix": "ADR"},
    "Context.md": {"folder": "technical/architecture", "prefix": "ADR"},
    "KnowledgeBase.md": {"folder": "requirements", "prefix": "REQ"},
}


def workspace_root(value: Path) -> Path:
    selected = value.resolve()
    if selected.name != ".devbuddy":
        raise ValueError("--devbuddy-root must point to a directory named .devbuddy")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devbuddy-root", type=Path, required=True)
    parser.add_argument("--host", choices=("codex", "claude-code", "opencode"))
    parser.add_argument("--host-root", type=Path)
    args = parser.parse_args()
    try:
        root = workspace_root(args.devbuddy_root)
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1
    legacy: list[dict[str, str]] = []
    for name, target in DOCUMENTS.items():
        for candidate in (root / name, root / "knowledge-base" / "legacy" / name):
            if candidate.is_file():
                legacy.append({"source": str(candidate), "target_folder": target["folder"], "key_prefix": target["prefix"], "action": "preserve_as_evidence_then_propose_typed_document"})
    database_tool = root / "tools" / "db-query-tool"
    host_legacy = False
    if args.host and args.host_root:
        host_legacy = (args.host_root / "skills" / "devbuddy" / "SKILL.md").is_file()
    report = {
        "operation": "devbuddy-migrate",
        "workspace": str(root),
        "workspace_initialized": (root / "settings.yaml").is_file(),
        "legacy_documents": legacy,
        "legacy_database_tool": str(database_tool) if database_tool.exists() else None,
        "host": args.host,
        "legacy_host_skill_detected": host_legacy,
        "next_steps": [
            "Review this mapping; retain every legacy document as evidence.",
            "Create typed documents only after approval and mint each key with new_knowledge_key.py.",
            "Preview workspace layout, legacy database-tool, and host-skill retirement separately before --apply.",
        ],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
