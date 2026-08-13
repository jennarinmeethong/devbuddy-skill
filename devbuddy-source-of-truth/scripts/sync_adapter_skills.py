#!/usr/bin/env python3
"""Render the shared DevBuddy adapter SKILL.md core for Codex and Claude."""
from __future__ import annotations

import argparse
from pathlib import Path


ADAPTERS = {
    "codex": {
        "directory": "devbuddy-codex",
        "frontmatter": "---\nname: devbuddy\ndescription: Policy-driven Codex software-delivery orchestrator. Use only for an explicit $devbuddy invocation to assess work, route specialist subagents, enforce approvals, select approved minimum-sufficient model and effort, preserve project memory, and verify delivery evidence.\n---\n",
        "heading": "# DevBuddy for Codex\n\nUse only through `$devbuddy <task>`, `$devbuddy loop <task>`, or `$devbuddy analyze <project>`. Advanced forms are `$devbuddy <role> <task>`, `$devbuddy owner <task>`, and `$devbuddy owner loop <task>`. The bare form is the Orchestrator entrypoint; it chooses the role graph. `analyze` is read-only; only `owner` promotes approved observations. Canonical roles are `ba-pm`, `ux-ui`, `architect`, `developer`, `qa`, `security`, `devops-sre`, `dba-data`, and `reviewer`; aliases are defined in `references/role-routing.md`.\n\n",
        "adapter_name": "Codex",
        "dispatch_reference": "codex-dispatch.md",
        "dispatch_instruction": "Dispatch a real specialist with explicit `model` and `reasoning_effort`; the Orchestrator never performs specialist work.",
        "unavailable_condition": "explicit model/effort subagents are unavailable",
        "unavailable_term": "subagents are unavailable",
    },
    "claude": {
        "directory": "devbuddy-claude",
        "frontmatter": "---\nname: devbuddy\ndescription: Policy-driven Claude Code software-delivery orchestrator for an explicit /devbuddy invocation. Assess the task, route specialist subagents, enforce approvals, select approved minimum-sufficient model and effort, preserve project memory, and verify delivery evidence.\ndisable-model-invocation: true\nargument-hint: <task> | loop <task> | analyze <project> | <role> <task>\n---\n",
        "heading": "# DevBuddy for Claude Code\n\nUse only through `/devbuddy <task>`, `/devbuddy loop <task>`, or `/devbuddy analyze <project>`. Advanced forms are `/devbuddy <role> <task>`, `/devbuddy owner <task>`, and `/devbuddy owner loop <task>`. The bare form is the Orchestrator entrypoint; it chooses the role graph. `analyze` is read-only; only `owner` promotes approved observations. Canonical roles are `ba-pm`, `ux-ui`, `architect`, `developer`, `qa`, `security`, `devops-sre`, `dba-data`, and `reviewer`; aliases are defined in `references/role-routing.md`.\n\n",
        "adapter_name": "Claude",
        "dispatch_reference": "claude-dispatch.md",
        "dispatch_instruction": "Dispatch a real specialist through the Agent tool as `devbuddy-<role>-<effort>` with explicit `model`; the Orchestrator never performs specialist work.",
        "unavailable_condition": "the required agent is unavailable",
        "unavailable_term": "an agent is unavailable",
    },
}


def render(config: dict[str, str], template: str) -> str:
    body = template
    for key, value in config.items():
        body = body.replace("{{" + key + "}}", value)
    return config["frontmatter"] + "\n" + config["heading"] + body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when generated files differ")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    repository = source.parent
    template = (source / "templates" / "adapter-skill-core.md.template").read_text(encoding="utf-8")
    matrix = (source / "references" / "loading-matrix.md").read_text(encoding="utf-8")
    shared_runtime = (
        "scripts/init_project_memory.py",
        "scripts/validate_project_settings.py",
    )
    errors: list[str] = []
    for name, config in ADAPTERS.items():
        target = repository / config["directory"] / "SKILL.md"
        matrix_target = repository / config["directory"] / "references" / "loading-matrix.md"
        expected = render(config, template)
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != expected:
                errors.append(f"stale generated adapter skill: {target}; run sync_adapter_skills.py")
            if not matrix_target.is_file() or matrix_target.read_text(encoding="utf-8") != matrix:
                errors.append(f"stale loading matrix: {matrix_target}; run sync_adapter_skills.py")
            for relative in shared_runtime:
                source_file = source / relative
                adapter_file = repository / config["directory"] / relative
                template_file = repository / config["directory"] / "templates" / "project-tools" / f"{source_file.name}.template"
                for target_file in (adapter_file, template_file):
                    if not target_file.is_file() or target_file.read_bytes() != source_file.read_bytes():
                        errors.append(f"stale shared runtime tool: {target_file}; run sync_adapter_skills.py")
            continue
        target.write_text(expected, encoding="utf-8")
        matrix_target.write_text(matrix, encoding="utf-8")
        for relative in shared_runtime:
            source_file = source / relative
            adapter_file = repository / config["directory"] / relative
            template_file = repository / config["directory"] / "templates" / "project-tools" / f"{source_file.name}.template"
            adapter_file.write_bytes(source_file.read_bytes())
            template_file.write_bytes(source_file.read_bytes())
        print(f"OK: generated {target}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: adapter skills match the shared template" if args.check else "OK: adapter skills generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
