#!/usr/bin/env python3
"""Create, coordinate, and validate compact DevBuddy task memory.

This is deliberately dependency-free so the identical tool can ship with both
adapters.  It enforces the protocol at its file boundary; platform identity and
filesystem ACLs remain an adapter-host responsibility.
"""
from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path

import bootstrap_knowledge

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RELATIVE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
REVISION = re.compile(r"^- Memory revision: (\d+)$", re.MULTILINE)
CORE = {"Context.md", "BusinessContext.md", "DecisionLog.md", "KnowledgeBase.md"}
MAX_HANDOFF_BYTES = 12_000


def identifier(value: str, label: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def relative_path(value: str, label: str) -> str:
    cleaned = value.strip().replace("\\", "/").rstrip("/")
    if not cleaned or not RELATIVE_PATH.fullmatch(cleaned) or cleaned.startswith(".") or "/../" in f"/{cleaned}/":
        raise ValueError(f"invalid {label}: {value!r}")
    return cleaned


def root(args: argparse.Namespace) -> Path:
    selected = [path for path in (args.root, args.project_root) if path is not None]
    if len(selected) != 1:
        raise ValueError("provide exactly one of --root or --project-root")
    value = args.root if args.root is not None else args.project_root / ".devbuddy"
    resolved = value.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"memory root not found: {resolved}")
    missing = sorted(name for name in CORE if not (resolved / name).is_file())
    if missing:
        raise ValueError("memory root is incomplete: " + ", ".join(missing))
    return resolved


def task_paths(memory: Path, project_id: str, task_id: str) -> tuple[Path, Path, Path]:
    base = memory / "tasks" / project_id
    task_dir = base / f"task-{task_id}"
    return base / f"task-{task_id}.md", task_dir, task_dir / "handoffs"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        Path(temporary).unlink(missing_ok=True)
        raise


def task(args: argparse.Namespace) -> tuple[Path, str, str, Path, Path, Path]:
    memory = root(args)
    project_id = identifier(args.project_id, "project ID")
    task_id = identifier(args.task_id, "task ID")
    ledger, task_dir, handoffs = task_paths(memory, project_id, task_id)
    return memory, project_id, task_id, ledger, task_dir, handoffs


def revision(ledger: Path) -> int:
    match = REVISION.search(ledger.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"task ledger has no Memory revision: {ledger}")
    return int(match.group(1))


def require_ledger(ledger: Path) -> None:
    if not ledger.is_file():
        raise ValueError(f"task ledger not found: {ledger}")


def require_owner(actor: str) -> None:
    if actor != "owner":
        raise ValueError("only --actor owner may mutate ledger state")


def initialise(args: argparse.Namespace) -> int:
    memory, project_id, task_id, ledger, _task_dir, handoffs = task(args)
    session_id = identifier(args.session_id or "session-1", "session ID")
    handoffs.mkdir(parents=True, exist_ok=True)
    if ledger.exists():
        content = ledger.read_text(encoding="utf-8")
        marker = f"- {session_id}\n"
        if marker not in content:
            atomic_write(ledger, content.rstrip() + f"\n\n## Sessions\n{marker}")
        action = "RESUME"
    else:
        atomic_write(ledger, "\n".join((
            f"# Task Ledger: {task_id}", "", "- Status: `queued`", f"- Project ID: {project_id}",
            f"- Session ID / attempt: {session_id} / 1", "- Memory revision: 0", "- Memory root reference: " + str(memory),
            "", "## Slices, locks, and handoffs", "", "## Approvals and decisions", "", "## Audit references", "",
        )))
        action = "CREATE"
    print(f"{action}: ledger={ledger}")
    print(f"HANDOFFS: {handoffs}")
    return 0


def record_handoff(args: argparse.Namespace) -> int:
    _memory, _project_id, task_id, ledger, _task_dir, handoffs = task(args)
    slice_id = identifier(args.slice_id, "slice ID")
    if args.attempt < 1:
        raise ValueError("attempt must be at least 1")
    require_ledger(ledger)
    if args.parent_revision != revision(ledger):
        raise ValueError("stale parent revision; read the latest ledger before writing a handoff")
    source = args.input.expanduser().resolve()
    content = source.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) > MAX_HANDOFF_BYTES:
        raise ValueError(f"handoff exceeds {MAX_HANDOFF_BYTES} bytes; keep only the next-slice delta")
    required = (f"- Task ID: {task_id}", "- Slice ID / attempt:", "- Parent handoff / revision:", "- Status:")
    if any(field not in content for field in required):
        raise ValueError("handoff must include Task ID, Slice ID / attempt, Parent handoff / revision, and Status")
    target = handoffs / f"{slice_id}-{args.attempt}.md"
    atomic_write(target, content)
    print(f"OK: handoff={target}")
    return 0


def reserve(args: argparse.Namespace) -> int:
    _memory, _project_id, _task_id, ledger, task_dir, _handoffs = task(args)
    require_ledger(ledger)
    scope = relative_path(args.scope, "reservation scope")
    if args.expected_revision != revision(ledger):
        raise ValueError("stale expected revision; reservation refused")
    lock = task_dir / "locks" / f"{scope.replace('/', '__')}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError(f"reservation already exists: {lock}") from None
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"actor: {identifier(args.actor, 'actor')}\nscope: {scope}\nrevision: {args.expected_revision}\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(f"OK: reservation={lock}")
    return 0


def release(args: argparse.Namespace) -> int:
    _memory, _project_id, _task_id, ledger, task_dir, _handoffs = task(args)
    require_ledger(ledger)
    scope = relative_path(args.scope, "reservation scope")
    lock = task_dir / "locks" / f"{scope.replace('/', '__')}.lock"
    if not lock.is_file():
        raise ValueError(f"reservation not found: {lock}")
    if f"actor: {identifier(args.actor, 'actor')}\n" not in lock.read_text(encoding="utf-8"):
        raise ValueError("reservation belongs to another actor")
    lock.unlink()
    print(f"OK: released={lock}")
    return 0


def commit(args: argparse.Namespace) -> int:
    _memory, _project_id, _task_id, ledger, _task_dir, _handoffs = task(args)
    require_ledger(ledger)
    require_owner(args.actor)
    content = ledger.read_text(encoding="utf-8")
    current = revision(ledger)
    if args.expected_revision != current:
        raise ValueError("stale expected revision; canonical commit refused")
    updated, replacements = REVISION.subn(f"- Memory revision: {current + 1}", content, count=1)
    if replacements != 1:
        raise ValueError("unable to advance memory revision")
    summary = args.summary.strip()
    if not summary or len(summary) > 500 or "\n" in summary:
        raise ValueError("summary must be one non-empty line of at most 500 characters")
    atomic_write(ledger, updated.rstrip() + f"\n\n## Canonical commits\n- revision {current + 1}: {summary}\n")
    print(f"OK: memory revision={current + 1}")
    return 0


def check_scope(args: argparse.Namespace) -> int:
    _memory, _project_id, _task_id, ledger, _task_dir, _handoffs = task(args)
    require_ledger(ledger)
    scopes = [relative_path(value, "write scope") for value in args.write_scope.split(",")]
    for changed in args.changed:
        if changed.replace("\\", "/").strip().rstrip("/") == ".devbuddy" or changed.replace("\\", "/").strip().startswith(".devbuddy/"):
            raise ValueError("specialists may not write .devbuddy directly")
        candidate = relative_path(changed, "changed path")
        if not any(candidate == scope or candidate.startswith(scope + "/") for scope in scopes):
            raise ValueError(f"changed path outside write_scope: {candidate}")
    print("OK: changed paths remain within write_scope")
    return 0


def analyse(args: argparse.Namespace) -> int:
    memory, _project_id, _task_id, ledger, task_dir, _handoffs = task(args)
    require_ledger(ledger)
    source = args.source_root.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"source root not found: {source}")
    facts = bootstrap_knowledge.discover(source)
    sections = [
        "# Read-only Project Analysis", "", f"- Source root: `{source}`", f"- Memory root: `{memory}`",
        f"- Parent revision: {revision(ledger)}", "", "This is a bounded inventory, not canonical knowledge. Owner approval is required before promotion.",
    ]
    for title, key in (
        ("Manifests", "manifests"), ("Package managers", "package_managers"), ("Framework signals", "frameworks"),
        ("Source directories", "source_directories"), ("Test directories", "test_directories"),
        ("Candidate validation commands", "commands"), ("Architecture references", "architecture_references"),
    ):
        values = facts[key]
        sections.extend(("", f"## {title}", ""))
        sections.extend(f"- `{value}`" for value in values) if values else sections.append("- None detected.")
    target = task_dir / "analysis.md"
    atomic_write(target, "\n".join(sections) + "\n")
    print(f"OK: analysis={target}")
    return 0


def validate(args: argparse.Namespace) -> int:
    _memory, _project_id, _task_id, ledger, _task_dir, handoffs = task(args)
    errors = []
    if not ledger.is_file():
        errors.append(f"missing ledger: {ledger}")
    elif REVISION.search(ledger.read_text(encoding="utf-8")) is None:
        errors.append(f"missing memory revision: {ledger}")
    if not handoffs.is_dir():
        errors.append(f"missing handoff directory: {handoffs}")
    if errors:
        for error in errors:
            print("ERROR: " + error)
        return 1
    print(f"OK: task memory validates for {ledger}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "handoff", "reserve", "release", "commit", "check-scope", "analyze", "validate"):
        command = commands.add_parser(name)
        roots = command.add_mutually_exclusive_group(required=True)
        roots.add_argument("--root", type=Path)
        roots.add_argument("--project-root", type=Path)
        command.add_argument("--project-id", required=True)
        command.add_argument("--task-id", required=True)
    commands.choices["init"].add_argument("--session-id")
    handoff = commands.choices["handoff"]
    handoff.add_argument("--slice-id", required=True)
    handoff.add_argument("--attempt", type=int, required=True)
    handoff.add_argument("--parent-revision", type=int, required=True)
    handoff.add_argument("--input", type=Path, required=True)
    for name in ("reserve", "release"):
        commands.choices[name].add_argument("--scope", required=True)
        commands.choices[name].add_argument("--actor", required=True)
    commands.choices["reserve"].add_argument("--expected-revision", type=int, required=True)
    commit_command = commands.choices["commit"]
    commit_command.add_argument("--actor", required=True)
    commit_command.add_argument("--expected-revision", type=int, required=True)
    commit_command.add_argument("--summary", required=True)
    scope_command = commands.choices["check-scope"]
    scope_command.add_argument("--write-scope", required=True)
    scope_command.add_argument("--changed", action="append", required=True)
    commands.choices["analyze"].add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    handlers = {
        "init": initialise, "handoff": record_handoff, "reserve": reserve, "release": release,
        "commit": commit, "check-scope": check_scope, "analyze": analyse, "validate": validate,
    }
    try:
        return handlers[args.command](args)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
