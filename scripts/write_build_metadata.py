#!/usr/bin/env python3
"""Record a reviewable .NET build environment for the database core."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "plugin" / "devbuddy-database-core" / "build-metadata.json"


def command(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="update the checked-in metadata file")
    args = parser.parse_args()
    try:
        sdk = command("dotnet", "--version")
        runtime = next(line.split()[1] for line in command("dotnet", "--list-runtimes").splitlines() if line.startswith("Microsoft.NETCore.App "))
        revision = command("git", "rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError, IndexError) as error:
        print(f"ERROR: cannot determine build environment: {error}"); return 1
    drivers = {"Microsoft.Data.SqlClient": "7.0.2", "Npgsql": "10.0.3", "MySqlConnector": "2.6.2", "Oracle.ManagedDataAccess.Core": "23.26.300", "MongoDB.Driver": "3.11.0", "StackExchange.Redis": "3.1.13"}
    data = {"target_framework": "net10.0", "dotnet_sdk": sdk, "runtime": runtime, "self_contained": True, "single_file": True, "drivers": drivers, "source_revision": revision, "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    print(json.dumps(data, indent=2))
    if not args.apply:
        print("DRY RUN: pass --apply to update build metadata")
        return 0
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"APPLIED: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
