#!/usr/bin/env python3
"""Validate static, no-model-call orchestration scenario coverage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# The two model/effort selection gates are required because this adapter splits
# the pair across two transports: effort is baked into the chosen subagent
# definition, model is set per Agent call. A gap in either one is invisible in
# the other, so both the independent-selection and the unverified case are
# covered rather than folded into model_effort_escalation.
REQUIRED = {"bare_entrypoint", "analyze_project", "slice_record_memory", "bug_fix", "feature", "migration", "security", "incident", "missing_information", "unavailable_tool", "approval_gate", "multi_role", "missing_agent_definition", "model_effort_escalation", "model_effort_independent_selection", "unverified_model_effort", "trusted_workspace_runtime_tools"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenarios", type=Path)
    args = parser.parse_args()
    try:
        scenarios = json.loads(args.scenarios.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: cannot read scenarios: {error}")
        return 1
    found = {item.get("id") for item in scenarios if isinstance(item, dict)}
    errors = ["missing scenarios: " + ", ".join(sorted(REQUIRED - found))] if REQUIRED - found else []
    for item in scenarios:
        if not isinstance(item, dict) or not all(item.get(key) for key in ("id", "expected_status", "expected_route", "evidence")):
            errors.append(f"invalid scenario: {item!r}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {len(scenarios)} no-model-call scenarios cover required orchestration gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
