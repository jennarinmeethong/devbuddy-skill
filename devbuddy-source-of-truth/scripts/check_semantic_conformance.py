#!/usr/bin/env python3
"""Check semantic invariants shared by the source and both adapters."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


COMMON_TOKENS = (
    "minimum_sufficient",
    "waiting_user",
    "knowledge",
    "model",
    "effort",
    "memory_root",
    "devbuddy-ref",
)
ROLES = {"ba-pm", "ux-ui", "architect", "developer", "qa", "security", "devops-sre", "dba-data", "reviewer"}
HANDOFF_FIELDS = {
    "Task ID",
    "Role",
    "Model / effort used",
    "Status",
    "Objective",
    "Outputs and artefacts",
    "Verification evidence",
    "Knowledge keys/updates",
    "Risks and blockers",
    "Recommended next role/task",
    "Required approval",
}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def value(path: Path, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}:\s*(\S+)\s*$", text(path), re.MULTILINE)
    return match.group(1) if match else None


def roles(root: Path) -> set[str]:
    return {path.stem for path in (root / "roles").glob("*.md")} - {"orchestrator"}


def handoff_fields(path: Path) -> set[str]:
    found: set[str] = set()
    for line in text(path).splitlines():
        match = re.match(r"^- ([^:]+):", line)
        if match:
            found.add(match.group(1))
    return found


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

    source_handoff = handoff_fields(source / "templates" / "handoff.md")
    if missing := HANDOFF_FIELDS - source_handoff:
        errors.append("source handoff missing: " + ", ".join(sorted(missing)))

    source_roles = roles(source)
    if source_roles != ROLES:
        errors.append("source role catalogue mismatch: " + ", ".join(sorted(source_roles ^ ROLES)))

    source_text = "\n".join(
        text(path)
        for path in (
            source / "SKILL.md",
            source / "settings.yaml",
            source / "references" / "policies.md",
            source / "templates" / "handoff.md",
        )
    )
    for token in COMMON_TOKENS:
        if token not in source_text:
            errors.append(f"source missing semantic token: {token}")

    expected = {
        "devbuddy-claude": {
            "root": claude,
            "invocation": "/devbuddy",
            "model_transport": "agent_tool_model_parameter",
            "effort_transport": "agent_definition_frontmatter",
        },
        "devbuddy-codex": {
            "root": codex,
            "invocation": "$devbuddy",
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
                root / "references" / ("claude-dispatch.md" if name.endswith("claude") else "codex-dispatch.md"),
                root / "templates" / "handoff.md",
            )
        )
        if config["invocation"] not in adapter_text:
            errors.append(f"{name} missing explicit invocation {config['invocation']}")
        for token in COMMON_TOKENS:
            if token not in adapter_text:
                errors.append(f"{name} missing semantic token: {token}")
        if missing := HANDOFF_FIELDS - handoff_fields(root / "templates" / "handoff.md"):
            errors.append(f"{name} handoff missing: " + ", ".join(sorted(missing)))
        if roles(root) != ROLES:
            errors.append(f"{name} role catalogue mismatch: " + ", ".join(sorted(roles(root) ^ ROLES)))
        settings_text = text(root / "settings.yaml")
        for transport in (config["model_transport"], config["effort_transport"]):
            if transport not in settings_text:
                errors.append(f"{name} missing transport mapping: {transport}")
        if ".devbuddy" not in settings_text or ".devbuddy" not in text(root / "SKILL.md"):
            errors.append(f"{name} missing .devbuddy default memory root")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: source, Claude, and Codex semantic contracts conform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
