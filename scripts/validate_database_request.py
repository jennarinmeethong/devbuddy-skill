#!/usr/bin/env python3
"""Fail-closed validation for DevBuddy database adapter requests.

This is a policy gate, not a replacement for a restricted database principal.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

DENIED_SQL = re.compile(r"\b(insert|update|delete|merge|create|alter|drop|truncate|exec(?:ute)?|call|grant|revoke|commit|rollback|begin|declare|use|into|lock|copy|load|outfile|dblink|prepare|deallocate)\b", re.I)
ALLOWED_REDIS = {"GET", "MGET", "HGET", "HMGET", "HGETALL", "LRANGE", "SCARD", "SMEMBERS", "ZRANGE", "TTL", "EXISTS", "TYPE", "STRLEN"}
ALLOWED_MONGO_STAGES = {"$match", "$project", "$limit", "$skip", "$sort", "$group", "$unwind", "$lookup", "$addFields", "$set", "$count", "$facet"}
DENIED_MONGO_OPERATORS = {"$where", "$function", "$accumulator"}


def common_limits(payload: dict[str, object]) -> str | None:
    if not isinstance(payload.get("max_rows"), int) or not 1 <= payload["max_rows"] <= 5000:
        return "max_rows is required and must be 1..5000"
    if not isinstance(payload.get("max_result_bytes"), int) or not 1024 <= payload["max_result_bytes"] <= 10 * 1024 * 1024:
        return "max_result_bytes is required and must be 1024..10485760"
    if not isinstance(payload.get("timeout_seconds"), int) or not 1 <= payload["timeout_seconds"] <= 120:
        return "timeout_seconds is required and must be 1..120"
    return None


def relational(payload: dict[str, object]) -> str | None:
    sql = payload.get("sql")
    if not isinstance(sql, str) or not sql.strip(): return "sql is required"
    compact = re.sub(r"--[^\n]*|/\*.*?\*/", "", sql, flags=re.S).strip()
    if ";" in compact.rstrip(";"): return "only one statement is allowed"
    if not re.match(r"^(select|with)\b", compact, re.I): return "only SELECT or CTE queries are allowed"
    if DENIED_SQL.search(compact): return "unsafe SQL operation is not allowed"
    if re.search(r"\b(select\s+.*\s+into|for\s+(update|share)|nolock)\b", compact, re.I | re.S): return "locking or temporary-object syntax is not allowed"
    if re.search(r"\b(?:pg_sleep|sleep|benchmark|load_file|xp_[a-z0-9_]+|sys\.)\s*\(", compact, re.I): return "unsafe SQL function is not allowed"
    if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b", compact): return "cross-database access is not allowed"
    return None


def mongodb(payload: dict[str, object]) -> str | None:
    operation = payload.get("operation")
    if operation not in {"find", "aggregate", "count", "distinct"}: return "MongoDB operation is not allowlisted"
    if not isinstance(payload.get("limit"), int) or not 1 <= payload["limit"] <= payload["max_rows"]: return "MongoDB limit is required and must not exceed max_rows"
    raw = json.dumps(payload, sort_keys=True)
    if "$where" in raw or "mapReduce" in raw or "javascript" in raw.lower(): return "MongoDB JavaScript is not allowed"
    for stage in payload.get("pipeline", []):
        if not isinstance(stage, dict) or len(stage) != 1 or any(key not in ALLOWED_MONGO_STAGES for key in stage): return "MongoDB aggregation stage is not allowlisted"
        if any(operator in json.dumps(stage) for operator in DENIED_MONGO_OPERATORS): return "MongoDB JavaScript-like operator is not allowed"
    return None


def redis(payload: dict[str, object]) -> str | None:
    command, key, prefix = payload.get("command"), payload.get("key"), payload.get("key_prefix")
    if not isinstance(command, str) or command.upper() not in ALLOWED_REDIS: return "Redis command is not allowlisted"
    if not isinstance(key, str) or not isinstance(prefix, str) or not prefix or not key.startswith(prefix): return "Redis key must use the approved key prefix"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("sqlserver", "postgresql", "mariadb", "oracle", "mongodb", "redis"))
    parser.add_argument("request", help="JSON request object")
    args = parser.parse_args()
    try: payload = json.loads(args.request)
    except json.JSONDecodeError as error: print(json.dumps({"allowed": False, "error": "invalid request JSON", "detail": error.msg})); return 1
    if not isinstance(payload, dict) or not isinstance(payload.get("database_id"), str) or not payload["database_id"]:
        print(json.dumps({"allowed": False, "error": "database_id is required"})); return 1
    error = common_limits(payload) or (relational(payload) if args.engine in {"sqlserver", "postgresql", "mariadb", "oracle"} else mongodb(payload) if args.engine == "mongodb" else redis(payload))
    if error: print(json.dumps({"allowed": False, "error": error})); return 1
    print(json.dumps({"allowed": True, "database_id": payload["database_id"], "engine": args.engine, "untrusted_result": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
