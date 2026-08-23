#!/usr/bin/env python3
"""Publish the self-contained database adapter as part of a plugin build.

The adapter is a single binary shared by all six engine manifests. It contains
the engine drivers but chooses an engine only from the approved tool request.
The default remains a dry run so a plugin build cannot replace an artifact by
accident.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "plugin" / "devbuddy-database-core" / "src" / "DevBuddy.Database.Policy" / "DevBuddy.Database.Policy.csproj"
ARTIFACT_ROOT = ROOT / "plugin" / "devbuddy-database-core" / "runtime"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", default="win-x64", help=".NET runtime identifier to publish (default: win-x64)")
    parser.add_argument("--apply", action="store_true", help="publish the executable into the plugin package")
    parser.add_argument("--verify", action="store_true", help="verify an existing published executable without rebuilding")
    args = parser.parse_args()
    if args.apply and args.verify:
        parser.error("--apply and --verify cannot be combined")
    output = ARTIFACT_ROOT / args.runtime
    executable = output / ("DevBuddy.Database.Policy.exe" if args.runtime.startswith("win-") else "DevBuddy.Database.Policy")
    if args.verify:
        if executable.is_file():
            print(f"OK: published database adapter exists: {executable.relative_to(ROOT)}")
            return 0
        print(f"ERROR: database adapter is not built: {executable.relative_to(ROOT)}")
        return 1
    command = [
        "dotnet", "publish", str(PROJECT), "--configuration", "Release", "--runtime", args.runtime,
        "--self-contained", "true", "--nologo", "-p:PublishSingleFile=true", "-p:DebugType=None",
    ]
    print("PUBLISH: " + " ".join(command) + f" --output {output}")
    if not args.apply:
        print("DRY RUN: pass --apply to create the database adapter artifact")
        return 0
    try:
        with tempfile.TemporaryDirectory(prefix="devbuddy-plugin-build-") as temporary:
            staged = Path(temporary) / args.runtime
            result = subprocess.run(command + ["--output", str(staged)], cwd=ROOT, check=False)
            if result.returncode:
                return result.returncode
            staged_executable = staged / executable.name
            if not staged_executable.is_file():
                print(f"ERROR: publish did not produce {staged_executable.name}")
                return 1
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                shutil.rmtree(output)
            shutil.move(str(staged), str(output))
    except OSError as error:
        print(f"ERROR: cannot publish database adapter: {error}")
        return 1
    metadata = {
        "runtime": args.runtime,
        "executable": executable.name,
        "published_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    (output / "artifact-manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"APPLIED: published database adapter: {executable.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
