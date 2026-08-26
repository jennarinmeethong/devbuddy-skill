#!/usr/bin/env python3
"""Check that the Codex adapter covers all common checklist requirements."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ITEM = re.compile(r"^- \[([ x-])\] `?([A-Za-z0-9_-]+)`? .*Status:\s*`?(done|not_started|in_progress)`?")
REQUIRED = [
    "SKILL.md",
    "agents/openai.yaml",
    "settings.yaml",
    "schemas/project-settings.schema.json",
    "references/policy.md",
    "references/codex-dispatch.md",
    "references/role-routing.md",
    "references/settings.md",
    "references/knowledge-model.md",
    "references/task-memory.md",
    "references/loop.md",
    "references/custom-tools.md",
    "schemas/slice-record.schema.json",
    "templates/task-ledger.md",
    "templates/knowledge-entity.md",
    "scripts/validate_project_settings.py",
    "scripts/validate_skill_metadata.py",
    "scripts/init_project_memory.py",
    "scripts/bootstrap_knowledge.py",
    "scripts/task_memory.py",
    "scripts/validate_knowledge.py",
    "scripts/run_scenarios.py",
    "scripts/validate_manual.py",
    "scripts/install_codex_adapter.py",
    "manual/index.html",
    "tests/scenarios.json",
    "tests/test_project_memory.py",
]

ROLES = sorted(path.stem for path in (Path(__file__).resolve().parents[1] / "roles").glob("*.md") if path.stem != "orchestrator")


def items(path: Path) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ITEM.match(line)
        if match:
            found[match.group(2)] = (match.group(1), match.group(3))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-template", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = args.source_template or root.parent / "devbuddy-source-of-truth" / "templates" / "adapter-implementation-checklist.md"
    checklist = root / "adapter-implementation-checklist.md"
    errors: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing adapter file: {relative}")
    for role in ROLES:
        if not (root / "roles" / f"{role}.md").is_file():
            errors.append(f"missing role workflow: roles/{role}.md")
    if not source.is_file() or not checklist.is_file():
        errors.append("source template or adapter checklist is missing")
    else:
        source_items, adapter_items = items(source), items(checklist)
        for key in source_items:
            if key not in adapter_items:
                errors.append(f"missing checklist item: {key}")
                continue
            box, status = adapter_items[key]
            if (box, status) != ("x", "done"):
                errors.append(f"checklist item is incomplete: {key}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: Codex adapter conforms to the common checklist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
