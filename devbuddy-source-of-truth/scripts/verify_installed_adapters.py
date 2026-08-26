#!/usr/bin/env python3
"""Smoke-check installed DevBuddy adapters without making a model call."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


CORE = ("Context.md", "KnowledgeBase.md")
EFFORTS = ("low", "medium", "high", "extra", "max", "ultracode")


def version(path: Path, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}:\s*([^\s#]+)", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def identical(expected: Path, actual: Path, label: str, errors: list[str]) -> None:
    if not actual.is_file():
        errors.append(f"missing {label}: {actual}")
    elif expected.read_bytes() != actual.read_bytes():
        errors.append(f"stale {label}: {actual}")


def exercise(task_tool: Path, label: str, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="devbuddy-live-smoke-") as temporary:
        project = Path(temporary) / "project"
        memory = project / ".devbuddy"
        project.mkdir()
        (project / "package.json").write_text('{"name":"devbuddy-smoke"}', encoding="utf-8")
        memory.mkdir()
        for name in CORE:
            (memory / name).write_text(f"# {name}\n", encoding="utf-8")
        base = [sys.executable, "-B", str(task_tool), "--project-root", str(project), "--project-id", "smoke", "--task-id", "001"]
        commands = (
            base[:3] + ["init"] + base[3:],
            base[:3] + ["analyze"] + base[3:] + ["--source-root", str(project)],
            base[:3] + ["validate"] + base[3:],
        )
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode:
                errors.append(f"{label} task-memory smoke failed: {result.stdout.strip() or result.stderr.strip()}")
                return
        report = memory / "tasks" / "smoke" / "task-001" / "analysis.md"
        if not report.is_file() or "package.json" not in report.read_text(encoding="utf-8"):
            errors.append(f"{label} task-memory smoke did not persist analysis")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    repository = Path(__file__).resolve().parents[2]
    parser.add_argument("--repository-root", type=Path, default=repository)
    parser.add_argument("--codex-root", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--claude-root", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--exercise-task-memory", action="store_true", help="run a temporary, no-model-call task-memory exercise")
    args = parser.parse_args()
    repository = args.repository_root.expanduser().resolve()
    source = repository / "devbuddy-source-of-truth"
    expected_version = version(source / "settings.yaml", "common_spec_version")
    errors: list[str] = []
    if expected_version is None:
        errors.append("source settings missing common_spec_version")

    checks = (
        ("Codex", repository / "devbuddy-codex", args.codex_root.expanduser() / "skills" / "devbuddy", "source_spec_version"),
        ("Claude", repository / "devbuddy-claude", args.claude_root.expanduser() / "skills" / "devbuddy", "source_spec_version"),
    )
    for label, adapter, installed, version_key in checks:
        identical(adapter / "SKILL.md", installed / "SKILL.md", f"{label} SKILL.md", errors)
        identical(adapter / "scripts" / "task_memory.py", installed / "scripts" / "task_memory.py", f"{label} task_memory.py", errors)
        identical(adapter / "references" / "task-memory.md", installed / "references" / "task-memory.md", f"{label} task-memory reference", errors)
        settings = installed / "settings.yaml"
        if settings.is_file() and expected_version and version(settings, version_key) != expected_version:
            errors.append(f"{label} installed source_spec_version differs from {expected_version}")
        elif not settings.is_file():
            errors.append(f"missing {label} settings: {settings}")
        if args.exercise_task_memory and (installed / "scripts" / "task_memory.py").is_file():
            exercise(installed / "scripts" / "task_memory.py", label, errors)

    claude_agents = args.claude_root.expanduser() / "agents"
    roles = tuple(sorted(path.stem for path in (source / "roles").glob("*.md") if path.stem != "orchestrator"))
    for role in roles:
        for effort in EFFORTS:
            agent = claude_agents / f"devbuddy-{role}-{effort}.md"
            if not agent.is_file():
                errors.append(f"missing Claude agent: {agent}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    mode = "with temporary task-memory exercise" if args.exercise_task_memory else "artifact checks only"
    print(f"OK: installed Codex and Claude adapters match source {expected_version} ({mode}; no model call)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
