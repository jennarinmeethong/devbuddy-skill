#!/usr/bin/env python3
"""Install the DevBuddy Claude adapter into a Claude Code configuration root.

Copies the skill to <root>/skills/devbuddy/ and the 54 subagent definitions to
<root>/agents/. Dry-run is the default: nothing is written until --apply is
given, so the user can see the exact file list first.

Only the self-contained scripts travel with the install; see SKILL_SCRIPTS.

The installer refuses to overwrite any existing file it cannot identify as a
DevBuddy artefact. A same-named file from another tool is a conflict for the
user to resolve, not something to silently replace.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKILL_CONTENT = ["SKILL.md", "settings.yaml", "references", "roles", "templates", "schemas", "manual"]

# Scripts the installed skill can actually run. Each one is self-contained: it
# needs nothing outside the skill root. The adapter's other scripts compare this
# adapter against devbuddy-source-of-truth/, which no install ever contains, so
# shipping them would only hand the user a command that cannot work. SKILL.md's
# validation section is split along this same line.
SKILL_SCRIPTS = ["init_project_memory.py", "validate_skill_metadata.py", "run_scenarios.py"]
SKILL_EXTRAS = [Path("tests") / "scenarios.json"]

# Never installed. Bundled custom tools carry real project files, so a local
# build or an editor's restore can leave output beside them; shipping that would
# put stale binaries in the user's configuration. Host-owned configuration is
# excluded for the stronger reason that it holds credentials.
SKIP_DIRS = {"__pycache__", "bin", "obj", "releases", ".venv", "node_modules"}
SKIP_FILES = {"appsettings.json", ".DS_Store"}
MARKER = "devbuddy"


def is_devbuddy_artefact(path: Path, source: Path | None = None) -> bool:
    """True when an existing file is safe for this installer to replace."""
    if MARKER in path.name.lower():
        return True
    try:
        if source is not None and path.read_bytes() == source.read_bytes():
            return True
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return False
    return MARKER in head.lower()


def plan_skill(target: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for entry in SKILL_CONTENT:
        source = ROOT / entry
        if not source.exists():
            continue
        if source.is_file():
            pairs.append((source, target / entry))
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.name in SKIP_FILES:
                continue
            if set(path.relative_to(ROOT).parts) & SKIP_DIRS:
                continue
            pairs.append((path, target / path.relative_to(ROOT)))
    for name in SKILL_SCRIPTS:
        script = ROOT / "scripts" / name
        if script.is_file():
            pairs.append((script, target / "scripts" / name))
    for relative in SKILL_EXTRAS:
        extra = ROOT / relative
        if extra.is_file():
            pairs.append((extra, target / relative))
    return pairs


def plan_agents(target: Path) -> list[tuple[Path, Path]]:
    return [(path, target / path.name) for path in sorted((ROOT / "agents").glob("*.md"))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claude-root", type=Path, default=Path.home() / ".claude",
                        help="Claude Code configuration root (default: ~/.claude)")
    parser.add_argument("--apply", action="store_true", help="write files; omit for a dry run")
    parser.add_argument(
        "--replace-recognized-skill",
        action="store_true",
        help="replace differing files only when the existing skill root identifies itself as DevBuddy",
    )
    args = parser.parse_args()

    root = args.claude_root.expanduser()
    skill_target = root / "skills" / "devbuddy"
    agent_target = root / "agents"

    pairs = plan_skill(skill_target) + plan_agents(agent_target)
    if not pairs:
        print("ERROR: nothing to install; run scripts/generate_agents.py first")
        return 1

    recognized_skill = is_devbuddy_artefact(skill_target / "SKILL.md")
    conflicts = [dst for src, dst in pairs if dst.exists() and not is_devbuddy_artefact(dst, src)]
    if args.replace_recognized_skill and recognized_skill:
        conflicts = [dst for dst in conflicts if skill_target not in dst.parents and dst != skill_target]
    if conflicts:
        for path in conflicts:
            print(f"ERROR: refusing to overwrite non-DevBuddy file: {path}")
        print("Resolve these conflicts or choose a different --claude-root.")
        return 1
    if args.replace_recognized_skill and not recognized_skill:
        print(f"ERROR: {skill_target} is not a recognized DevBuddy skill; refusing replacement")
        return 1

    if not args.apply:
        for _, dst in pairs:
            print(f"{'REPLACE' if dst.exists() else 'CREATE '}: {dst}")
        print(f"\nDry run: {len(pairs)} files. Re-run with --apply to install.")
        return 0

    try:
        for src, dst in pairs:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    except OSError as error:
        print(f"ERROR: install failed: {error}")
        return 1

    print(f"OK: installed {len(pairs)} files")
    print(f"  skill:  {skill_target}")
    print(f"  agents: {agent_target}")
    print("Restart or refresh the Claude Code session so /devbuddy and the devbuddy-* agents load.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
