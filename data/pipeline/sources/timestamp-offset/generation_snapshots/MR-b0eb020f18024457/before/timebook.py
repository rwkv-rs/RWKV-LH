#!/usr/bin/env python3
"""Team timebook CLI - add subcommand only (this round)."""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

ISO_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def parse_timestamp(value):
    """Parse ISO 8601 with explicit offset/Z, whole-second precision."""
    if not isinstance(value, str) or not ISO_RE.match(value):
        raise ValueError("invalid timestamp: %r" % (value,))
    if "." in value:
        frac = value.split(".", 1)[1]
        digits = ""
        for ch in frac:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits.strip("0"):
            raise ValueError("timestamp must be whole-second precision: %r" % (value,))
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.microsecond != 0:
        raise ValueError("timestamp must be whole-second precision: %r" % (value,))
    if dt.tzinfo is None:
        raise ValueError("timestamp requires explicit UTC offset: %r" % (value,))
    return dt.astimezone(timezone.utc)


def validate_event(event_id, project, start, end):
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("id must be a nonempty, non-whitespace string")
    if not isinstance(project, str) or not project.strip():
        raise ValueError("project must be a nonempty, non-whitespace string")
    start_dt = parse_timestamp(start)
    end_dt = parse_timestamp(end)
    if not end_dt > start_dt:
        raise ValueError("end must be strictly after start")
    return start_dt, end_dt


def normalize_iso(dt):
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def open_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            start_utc TEXT NOT NULL,
            end_utc TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def add_event(conn, event_id, project, start, end):
    start_dt, end_dt = validate_event(event_id, project, start, end)
    start_utc = normalize_iso(start_dt)
    end_utc = normalize_iso(end_dt)
    cur = conn.execute("SELECT project, start_utc, end_utc FROM events WHERE id = ?", (event_id,))
    row = cur.fetchone()
    if row is not None:
        if row[0] == project and row[1] == start_utc and row[2] == end_utc:
            return {"inserted": 0, "duplicates": 1}
        raise ValueError("conflicting ID: %s" % (event_id,))
    conn.execute(
        "INSERT INTO events (id, project, start_utc, end_utc) VALUES (?, ?, ?, ?)",
        (event_id, project, start_utc, end_utc),
    )
    conn.commit()
    return {"inserted": 1, "duplicates": 0}


def cmd_add(args):
    conn = open_db(args.db)
    try:
        result = add_event(conn, args.id, args.project, args.start, args.end)
    finally:
        conn.close()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Team timebook")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("db")
    p_add.add_argument("--id", required=True)
    p_add.add_argument("--project", required=True)
    p_add.add_argument("--start", required=True)
    p_add.add_argument("--end", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "add":
            result = cmd_add(args)
        else:
            raise ValueError("unsupported command")
    except ValueError as exc:
        sys.stderr.write("error: %s\n" % (exc,))
        return 1

    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
