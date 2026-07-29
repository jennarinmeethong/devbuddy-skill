#!/usr/bin/env python3
"""Create a reviewable knowledge bootstrap from a repository without guessing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_MEMORY_ROOT = ".devbuddy"
CORE = {
    "Context.md": "# Technical Context\n\n",
    "BusinessContext.md": "# Business Context\n\n",
    "DecisionLog.md": "# Decision Log\n\n",
    "KnowledgeBase.md": "# Knowledge Base\n\n",
}
DIRECTORIES = [
    "domains", "features", "requirements", "flows", "business-rules", "screens",
    "technical/architecture", "technical/apis", "technical/database", "technical/events",
    "technical/integrations", "tests", "decisions", "releases", "incidents", "tasks",
]
MANIFESTS = (
    "package.json", "pyproject.toml", "requirements.txt", "Pipfile", "Cargo.toml", "go.mod",
    "pom.xml", "build.gradle", "composer.json", "Gemfile", "mix.exs", "*.csproj",
)
FRAMEWORK_MARKERS = {
    "Angular": ("@angular/core", "angular.json"),
    "React": ("react",),
    "Next.js": ("next",),
    "Vue": ("vue",),
    "FastAPI": ("fastapi",),
    "Django": ("django",),
    "Rails": ("rails",),
}


def resolve_root(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[Path, Path]:
    selected = [value for value in (args.root, args.project_root) if value is not None]
    if len(selected) != 1:
        parser.error("provide --project-root <project-root> or --root <memory-root>")
    if args.project_root is not None:
        project = args.project_root.expanduser().resolve()
        return project, project / DEFAULT_MEMORY_ROOT
    memory = args.root.expanduser().resolve()
    project = (args.source_root or Path.cwd()).expanduser().resolve()
    return project, memory


def relative(path: Path, project: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path, limit: int = 100_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def discover(project: Path) -> dict[str, list[str] | str]:
    manifests: list[Path] = []
    for pattern in MANIFESTS:
        manifests.extend(project.glob(pattern))
    manifests = sorted({path for path in manifests if path.is_file()})
    manifest_names = [relative(path, project) for path in manifests]
    all_manifest_text = "\n".join(read_text(path) for path in manifests).lower()

    package_managers: list[str] = []
    for filename, manager in (
        ("bun.lockb", "bun"), ("bun.lock", "bun"), ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"), ("package-lock.json", "npm"),
    ):
        if (project / filename).is_file() and manager not in package_managers:
            package_managers.append(manager)
    if (project / "pyproject.toml").is_file() or (project / "requirements.txt").is_file():
        package_managers.append("python")
    if (project / "go.mod").is_file():
        package_managers.append("go")
    if (project / "Cargo.toml").is_file():
        package_managers.append("cargo")

    frameworks = [name for name, markers in FRAMEWORK_MARKERS.items() if any(marker.lower() in all_manifest_text for marker in markers)]
    if (project / "angular.json").is_file() and "Angular" not in frameworks:
        frameworks.append("Angular")

    source_directories = [
        relative(path, project) for path in sorted(project.iterdir())
        if path.is_dir() and not path.name.startswith(".") and path.name.lower() in {"src", "app", "lib", "packages", "services", "modules"}
    ]
    test_directories = [
        relative(path, project) for path in sorted(project.iterdir())
        if path.is_dir() and not path.name.startswith(".") and path.name.lower() in {"test", "tests", "spec", "e2e", "cypress", "__tests__"}
    ]
    architecture_references = [
        relative(path, project) for path in sorted(project.rglob("*"))
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(project).parts)
        and (path.name.lower() in {"readme.md", "context.md", "architecture.md", "decisionlog.md"}
             or "architecture" in {part.lower() for part in path.parts}
             or "adr" in {part.lower() for part in path.parts})
    ][:30]

    commands: list[str] = []
    package_json = project / "package.json"
    if package_json.is_file():
        try:
            scripts = json.loads(read_text(package_json)).get("scripts", {})
            if isinstance(scripts, dict):
                commands.extend(f"npm run {name}" for name in sorted(scripts) if any(token in name.lower() for token in ("test", "lint", "build", "check", "type")))
        except (json.JSONDecodeError, AttributeError):
            pass
    for marker, command in (("pytest", "pytest"), ("jest", "npx jest"), ("vitest", "npx vitest"), ("playwright", "npx playwright test")):
        if marker in all_manifest_text and command not in commands:
            commands.append(command)

    return {
        "project_name": project.name,
        "manifests": manifest_names,
        "package_managers": package_managers,
        "frameworks": frameworks,
        "source_directories": source_directories,
        "test_directories": test_directories,
        "architecture_references": architecture_references,
        "commands": commands,
    }


def bullet_section(title: str, values: list[str] | str) -> str:
    items = values if isinstance(values, list) else [values]
    if not items:
        return f"## {title}\n\n- None detected by the read-only scan.\n"
    return f"## {title}\n\n" + "\n".join(f"- `{item}`" for item in items) + "\n"


def render_context(project: Path, memory: Path, facts: dict[str, list[str] | str]) -> str:
    return (
        "# Technical Context\n\n"
        "## Bootstrap inventory\n\n"
        "This inventory was produced by a read-only repository scan. Review it before treating any observation as canonical knowledge.\n\n"
        f"- Project: `{facts['project_name']}`\n"
        f"- Repository root: `{project}`\n"
        f"- Memory root: `{memory}`\n\n"
        + bullet_section("Manifests and lockfile-derived runtimes", facts["manifests"])
        + bullet_section("Detected package managers", facts["package_managers"])
        + bullet_section("Detected frameworks or libraries", facts["frameworks"])
        + bullet_section("Likely source directories", facts["source_directories"])
        + bullet_section("Likely test directories", facts["test_directories"])
        + bullet_section("Candidate validation commands", facts["commands"])
        + bullet_section("Architecture and decision references", facts["architecture_references"])
        + "## Review gate\n\n- Status: pending user/role review.\n- Evidence boundary: only repository paths and manifest text were inspected; no business intent was inferred.\n"
    )


def render_knowledge(facts: dict[str, list[str] | str]) -> str:
    return (
        "# Knowledge Base\n\n"
        "## Bootstrap observations\n\n"
        "The following observations were extracted from repository metadata for review. They are not typed canonical entities and must not be promoted without Knowledge Impact Approval.\n\n"
        f"- Project: `{facts['project_name']}`\n"
        f"- Manifests detected: {', '.join(facts['manifests']) or 'none'}\n"
        f"- Runtime/package signals: {', '.join(facts['package_managers']) or 'none'}\n"
        f"- Framework/library signals: {', '.join(facts['frameworks']) or 'none'}\n"
        "\n## Review gate\n\n"
        "- Confirm each observation against source evidence before creating typed entities.\n"
        "- Record approved durable facts in the appropriate typed folder with an immutable key.\n"
        "- Do not add `devbuddy-ref` comments until the referenced knowledge key exists.\n"
    )


def scaffoldable(path: Path, name: str) -> bool:
    return not path.exists() or read_text(path) == CORE[name]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument("--project-root", type=Path, help="repository to inspect; memory is <project-root>/.devbuddy")
    roots.add_argument("--root", type=Path, help="approved external memory root, used directly")
    parser.add_argument("--source-root", type=Path, help="repository to inspect when using an external --root (default: current directory)")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="print observations and planned writes (default)")
    modes.add_argument("--apply", action="store_true", help="write only empty/bootstrap core files after review")
    args = parser.parse_args()
    project, memory = resolve_root(args, parser)
    if not project.is_dir():
        print(f"ERROR: repository root not found: {project}")
        return 1
    facts = discover(project)
    targets = [memory / "Context.md", memory / "KnowledgeBase.md"]
    conflicts = [path for path in targets if not scaffoldable(path, path.name)]
    print(f"SCAN: {project}")
    print(f"MEMORY: {memory}")
    for key in ("manifests", "package_managers", "frameworks", "source_directories", "test_directories", "commands", "architecture_references"):
        values = facts[key]
        print(f"FACT {key}: {', '.join(values) if isinstance(values, list) and values else 'none detected'}")
    for path in targets:
        print(f"{'CONFLICT' if path in conflicts else 'WRITE'}: {path}")
    if conflicts:
        print("ERROR: refusing to overwrite existing knowledge files: " + ", ".join(map(str, conflicts)))
        return 1
    if not args.apply:
        print("DRY RUN: no files written; review observations, then re-run with --apply after approval")
        return 0
    try:
        for directory in DIRECTORIES:
            (memory / directory).mkdir(parents=True, exist_ok=True)
        (memory / "Context.md").write_text(render_context(project, memory, facts), encoding="utf-8")
        (memory / "KnowledgeBase.md").write_text(render_knowledge(facts), encoding="utf-8")
    except OSError as error:
        print(f"ERROR: cannot write bootstrap knowledge at {memory}: {error}")
        return 1
    print(f"OK: wrote reviewable bootstrap knowledge at {memory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
