#!/usr/bin/env python3
"""Check semantic invariants shared by the source and both adapters."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


COMMON_TOKENS = (
    "minimum_sufficient",
    "waiting_user",
    "knowledge",
    "model",
    "effort",
    "memory_root",
    "read_keys",
    "record_path",
    "slice-record.schema.json",
    "adapter_profiles",
    "is_rtk",
    "rtk_required",
    "devbuddy-ref",
)
ROLES = {
    "ba-pm", "requirements-analyst", "ux-ui", "architect", "developer",
    "frontend-engineer", "backend-engineer", "qa", "security",
    "vulnerability-scanner", "compliance-policy", "security-incident-response",
    "devops-sre", "devops-engineer", "cloud-infrastructure", "site-reliability",
    "dba-data", "data-pipeline", "data-analyst", "model-evaluator",
    "helpdesk-support", "knowledge-base", "reviewer", "code-reviewer",
}
RECORD_FIELDS = {"schema_version", "task_id", "slice_id", "attempt", "parent_revision", "role", "model", "effort", "status", "result", "evidence", "next_slice", "knowledge_keys", "knowledge_proposal", "blockers", "required_approval"}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def value(path: Path, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}:\s*(\S+)\s*$", text(path), re.MULTILINE)
    return match.group(1) if match else None


def roles(root: Path) -> set[str]:
    return {path.stem for path in (root / "roles").glob("*.md")} - {"orchestrator"}


def record_fields(path: Path) -> set[str]:
    try:
        data = json.loads(text(path))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid slice record schema {path}: {error}") from None
    return set(data.get("properties", {})) if isinstance(data, dict) else set()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--claude", type=Path)
    parser.add_argument("--codex", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    claude = (args.claude or source.parent / "devbuddy-claude").resolve()
    codex = (args.codex or source.parent / "devbuddy-codex").resolve()
    errors: list[str] = []

    source_version = value(source / "settings.yaml", "common_spec_version")
    if source_version is None:
        errors.append("source settings missing skill.common_spec_version")

    source_record = record_fields(source / "schemas" / "slice-record.schema.json")
    if missing := RECORD_FIELDS - source_record:
        errors.append("source slice record missing: " + ", ".join(sorted(missing)))

    source_roles = roles(source)
    if source_roles != ROLES:
        errors.append("source role catalogue mismatch: " + ", ".join(sorted(source_roles ^ ROLES)))

    source_text = "\n".join(
        text(path)
        for path in (
            source / "SKILL.md",
            source / "settings.yaml",
            source / "references" / "policies.md",
            source / "references" / "task-memory.md",
            source / "references" / "adapter-contract.md",
            source / "schemas" / "slice-record.schema.json",
        )
    )
    for token in COMMON_TOKENS:
        if token not in source_text:
            errors.append(f"source missing semantic token: {token}")

    expected = {
        "devbuddy-claude": {
            "root": claude,
            "invocation": "/devbuddy",
            "default_task_form": "/devbuddy <task>",
            "entrypoint": "orchestrator",
            "model_transport": "agent_tool_model_parameter",
            "effort_transport": "agent_definition_frontmatter",
        },
        "devbuddy-codex": {
            "root": codex,
            "invocation": "$devbuddy",
            "default_task_form": "$devbuddy <task>",
            "entrypoint": "orchestrator",
            "model_transport": "subagent.model_parameter",
            "effort_transport": "subagent.reasoning_effort_parameter",
        },
    }
    for name, config in expected.items():
        root = config["root"]
        adapter_version = value(root / "settings.yaml", "source_spec_version")
        if source_version and adapter_version != source_version:
            errors.append(f"{name} source_spec_version {adapter_version!r} != {source_version!r}")
        adapter_text = "\n".join(
            text(path)
            for path in (
                root / "SKILL.md",
                root / "settings.yaml",
                root / "references" / "policy.md",
                root / "references" / "knowledge-model.md",
                root / "references" / "task-memory.md",
                root / "references" / ("claude-dispatch.md" if name.endswith("claude") else "codex-dispatch.md"),
                root / "schemas" / "slice-record.schema.json",
            )
        )
        if config["invocation"] not in adapter_text:
            errors.append(f"{name} missing explicit invocation {config['invocation']}")
        if config["default_task_form"] not in adapter_text:
            errors.append(f"{name} missing bare Orchestrator task form {config['default_task_form']}")
        if value(root / "settings.yaml", "entrypoint") != config["entrypoint"]:
            errors.append(f"{name} entrypoint must be {config['entrypoint']}")
        for token in COMMON_TOKENS:
            if token not in adapter_text:
                errors.append(f"{name} missing semantic token: {token}")
        if missing := RECORD_FIELDS - record_fields(root / "schemas" / "slice-record.schema.json"):
            errors.append(f"{name} slice record missing: " + ", ".join(sorted(missing)))
        if roles(root) != ROLES:
            errors.append(f"{name} role catalogue mismatch: " + ", ".join(sorted(roles(root) ^ ROLES)))
        settings_text = text(root / "settings.yaml")
        for transport in (config["model_transport"], config["effort_transport"]):
            if transport not in settings_text:
                errors.append(f"{name} missing transport mapping: {transport}")
        if ".devbuddy" not in settings_text or ".devbuddy" not in text(root / "SKILL.md"):
            errors.append(f"{name} missing .devbuddy default memory root")
        if text(root / "scripts" / "task_memory.py") != text(source / "scripts" / "task_memory.py"):
            errors.append(f"{name} task_memory.py differs from canonical source tool; run sync_task_memory.py")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: source, Claude, and Codex semantic contracts conform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
