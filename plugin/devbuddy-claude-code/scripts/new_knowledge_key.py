#!/usr/bin/env python3
"""Generate a collision-resistant immutable DevBuddy knowledge key."""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone


PREFIX = re.compile(r"^[A-Z][A-Z0-9]{1,15}$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, help="uppercase entity prefix, for example BR or INC")
    parser.add_argument("--json", action="store_true", help="emit a JSON object")
    args = parser.parse_args()
    prefix = args.prefix.upper()
    if not PREFIX.fullmatch(prefix):
        print("ERROR: --prefix must be 2..16 uppercase letters or digits and start with a letter")
        return 1
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"{prefix}-{timestamp}-{uuid.uuid4().hex.upper()}"
    if args.json:
        print(json.dumps({"key": key, "prefix": prefix}, sort_keys=True))
    else:
        print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
