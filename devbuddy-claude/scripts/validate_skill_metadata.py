#!/usr/bin/env python3
"""Validate Claude Code Skill and subagent metadata without PyYAML.

Checks the skill frontmatter and every agent definition, because a subagent
whose `effort` is missing or whose `model` is pinned would silently break the
per-dispatch model/effort guarantee the Orchestrator records in the ledger.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROLES = ["ba-pm", "ux-ui", "architect", "developer", "qa", "security", "devops-sre", "dba-data", "reviewer"]
TIERS = ["low", "medium", "high"]
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
CORE = ("Context.md", "BusinessContext.md", "DecisionLog.md", "KnowledgeBase.md")


def exercise_task_memory(root: Path, errors: list[str]) -> None:
    tool = root / "scripts" / "task_memory.py"
    if not tool.is_file():
        errors.append("missing scripts/task_memory.py")
        return
    with tempfile.TemporaryDirectory(prefix="devbuddy-claude-smoke-") as temporary:
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


def frontmatter(path: Path) -> tuple[dict[str, str], str | None]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing YAML frontmatter"
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, "unterminated YAML frontmatter"
    fields = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields, None


def check_skill(root: Path, errors: list[str]) -> None:
    skill = root / "SKILL.md"
    if not skill.is_file():
        errors.append("missing SKILL.md")
        return
    fields, problem = frontmatter(skill)
    if problem:
        errors.append(f"SKILL.md: {problem}")
        return
    if set(fields) != {"name", "description"}:
        errors.append("SKILL.md: frontmatter must contain only name and description")
    if fields.get("name") != "devbuddy":
        errors.append("SKILL.md: name must be devbuddy for /devbuddy invocation")
    description = fields.get("description", "")
    if not description:
        errors.append("SKILL.md: description is required")
    elif "/devbuddy" not in description:
        errors.append("SKILL.md: description must state the explicit /devbuddy invocation")


def resolve_agents_dir(root: Path, override: Path | None) -> Path | None:
    """Find the agent definitions.

    In the source tree they sit in <root>/agents. Once installed, the skill and
    the agents are separate: the skill lands in ~/.claude/skills/devbuddy and the
    definitions in ~/.claude/agents. Check both so the documented verification
    command works before and after install.
    """
    if override is not None:
        return override if override.is_dir() else None
    candidates = [root / "agents", Path.home() / ".claude" / "agents", root.parent.parent / "agents"]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("devbuddy-*.md")):
            return candidate
    return None


def check_agents(root: Path, directory: Path | None, errors: list[str]) -> int:
    if directory is None:
        errors.append("no agent definitions found; run scripts/generate_agents.py or pass --agents-dir")
        return 0
    expected = {f"devbuddy-{role}-{tier}" for role in ROLES for tier in TIERS}
    seen = set()
    for path in sorted(directory.glob("devbuddy-*.md")):
        fields, problem = frontmatter(path)
        if problem:
            errors.append(f"{path.name}: {problem}")
            continue
        name = fields.get("name", "")
        if name != path.stem:
            errors.append(f"{path.name}: name '{name}' does not match filename")
        seen.add(name)
        if not fields.get("description"):
            errors.append(f"{path.name}: description is required")
        effort = fields.get("effort")
        if not effort:
            errors.append(f"{path.name}: missing effort; per-dispatch effort selection cannot be verified")
        elif effort not in EFFORTS:
            errors.append(f"{path.name}: effort '{effort}' is not an accepted level")
        elif not name.endswith(f"-{effort}"):
            errors.append(f"{path.name}: effort '{effort}' contradicts the agent name")
        if "model" in fields:
            errors.append(f"{path.name}: must not pin a model; the Orchestrator selects it per dispatch")
    for missing in sorted(expected - seen):
        errors.append(f"missing agent definition: {missing}")
    return len(seen)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    parser.add_argument("--agents-dir", type=Path, default=None,
                        help="directory holding devbuddy-*.md definitions (default: auto-detect)")
    parser.add_argument("--exercise-task-memory", action="store_true", help="run a temporary no-model-call task-memory smoke test")
    args = parser.parse_args()
    errors: list[str] = []
    check_skill(args.skill_root, errors)
    directory = resolve_agents_dir(args.skill_root, args.agents_dir)
    count = check_agents(args.skill_root, directory, errors)
    if args.exercise_task_memory:
        exercise_task_memory(args.skill_root, errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    suffix = " with task-memory smoke" if args.exercise_task_memory else ""
    print(f"OK: Claude Skill metadata validates for {args.skill_root}{suffix}")
    print(f"OK: {count} agent definitions validate in {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
