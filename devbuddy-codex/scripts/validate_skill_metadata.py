#!/usr/bin/env python3
"""Validate essential Codex Skill metadata without PyYAML."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


CORE = ("Context.md", "BusinessContext.md", "DecisionLog.md", "KnowledgeBase.md")


def exercise_task_memory(root: Path, errors: list[str]) -> None:
    tool = root / "scripts" / "task_memory.py"
    if not tool.is_file():
        errors.append("missing scripts/task_memory.py")
        return
    with tempfile.TemporaryDirectory(prefix="devbuddy-codex-smoke-") as temporary:
        project = Path(temporary) / "project"
        memory = project / ".devbuddy"
        project.mkdir()
        (project / "package.json").write_text('{"name":"devbuddy-smoke"}', encoding="utf-8")
        (memory / "knowledge-base").mkdir(parents=True)
        for name in CORE:
            (memory / "knowledge-base" / name).write_text(f"# {name}\n", encoding="utf-8")
        (memory / "settings.yaml").write_text("workspace:\n  projects:\n    smoke:\n      path: ..\nmemory_root: knowledge-base\n", encoding="utf-8")
        base = [sys.executable, "-B", str(tool), "--devbuddy-root", str(memory), "--project-id", "smoke", "--task-id", "001"]
        for command in (base[:3] + ["init"] + base[3:], base[:3] + ["analyze"] + base[3:], base[:3] + ["validate"] + base[3:]):
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode:
                errors.append("task-memory smoke failed: " + (result.stdout.strip() or result.stderr.strip()))
                return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    parser.add_argument("--exercise-task-memory", action="store_true", help="run a temporary no-model-call task-memory smoke test")
    args = parser.parse_args()
    root = args.skill_root
    errors: list[str] = []
    skill = root / "SKILL.md"
    config = root / "agents" / "openai.yaml"
    if not skill.is_file():
        errors.append("missing SKILL.md")
    else:
        lines = skill.read_text(encoding="utf-8").splitlines()
        if len(lines) < 4 or lines[0] != "---":
            errors.append("SKILL.md: missing YAML frontmatter")
        else:
            try:
                end = lines.index("---", 1)
            except ValueError:
                errors.append("SKILL.md: unterminated YAML frontmatter")
                end = 1
            fields = {match.group(1): match.group(2) for line in lines[1:end] if (match := re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+)$", line))}
            if set(fields) != {"name", "description"}:
                errors.append("SKILL.md: frontmatter must contain only name and description")
            if fields.get("name") != "devbuddy":
                errors.append("SKILL.md: name must be devbuddy for $devbuddy invocation")
            if not fields.get("description"):
                errors.append("SKILL.md: description is required")
    if not config.is_file():
        errors.append("missing agents/openai.yaml")
    else:
        text = config.read_text(encoding="utf-8")
        for pattern, message in [
            (r'^  display_name: ".+"$', "display_name"),
            (r'^  short_description: ".+"$', "short_description"),
            (r'^  default_prompt: ".*\$devbuddy.*"$', "default_prompt with $devbuddy"),
            (r"^  allow_implicit_invocation: false$", "allow_implicit_invocation false"),
        ]:
            if not re.search(pattern, text, re.MULTILINE):
                errors.append(f"agents/openai.yaml: missing {message}")
    if args.exercise_task_memory:
        exercise_task_memory(root, errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    suffix = " with task-memory smoke" if args.exercise_task_memory else ""
    print(f"OK: Codex Skill metadata validates for {root}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
