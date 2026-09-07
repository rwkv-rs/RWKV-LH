"""Persistent UTC time ledger with atomic idempotent imports."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.microsecond:
        raise ValueError('timestamps require an offset and whole seconds')
    return int(parsed.timestamp())


def record(value):
    if not isinstance(value, dict) or set(value) != {'id', 'project', 'start', 'end'}:
        raise ValueError('invalid event fields')
    if any(not isinstance(value[key], str) or not value[key].strip() for key in value):
        raise ValueError('event fields must be nonempty strings')
    start, end = instant(value['start']), instant(value['end'])
    if end <= start:
        raise ValueError('end must follow start')
    return value['id'], value['project'], start, end


def connect(path):
    database = sqlite3.connect(path)
    database.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, project TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL)')
    database.commit()
    return database


def import_events(database, values):
    if not isinstance(values, list):
        raise ValueError('import document must be an array')
    rows = [record(value) for value in values]
    inserted, duplicates = 0, 0
    with database:
        for event in rows:
            prior = database.execute('SELECT project,start,end FROM events WHERE id=?', (event[0],)).fetchone()
            if prior is not None:
                if prior != event[1:]:
                    raise ValueError('conflicting duplicate id')
                duplicates += 1
            else:
                database.execute('INSERT INTO events VALUES (?,?,?,?)', event)
                inserted += 1
    return {'inserted': inserted, 'duplicates': duplicates}


def stats(database, begin_date, end_date):
    begin_day, end_day = date.fromisoformat(begin_date), date.fromisoformat(end_date)
    if begin_day >= end_day:
        raise ValueError('range must be nonempty')
    begin = int(datetime.combine(begin_day, time(), timezone.utc).timestamp())
    finish = int(datetime.combine(end_day, time(), timezone.utc).timestamp())
    days = {}
    for project, start, end in database.execute('SELECT project,start,end FROM events WHERE end>? AND start<?', (begin, finish)):
        current = datetime.fromtimestamp(max(start, begin), timezone.utc).date()
        while current < end_day:
            day_start = int(datetime.combine(current, time(), timezone.utc).timestamp())
            left, right = max(start, day_start, begin), min(end, day_start + 86400, finish)
            if right > left:
                projects = days.setdefault(current.isoformat(), {})
                projects[project] = projects.get(project, 0) + right - left
            if day_start + 86400 >= end:
                break
            current += timedelta(days=1)
    output = [{'date': day, 'projects': dict(sorted(projects.items())), 'total_seconds': sum(projects.values())}
              for day, projects in sorted(days.items())]
    return {'days': output, 'total_seconds': sum(item['total_seconds'] for item in output)}


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('database')
    for name in ('id', 'project', 'start', 'end'):
        add.add_argument('--' + name, required=True)
    load = commands.add_parser('import')
    load.add_argument('database')
    load.add_argument('input')
    query = commands.add_parser('stats')
    query.add_argument('database')
    query.add_argument('--from', dest='begin', required=True)
    query.add_argument('--to', dest='finish', required=True)
    args = parser.parse_args()
    try:
        with connect(args.database) as database:
            if args.command == 'add':
                result = import_events(database, [{key: getattr(args, key) for key in ('id', 'project', 'start', 'end')}])
            elif args.command == 'import':
                result = import_events(database, json.loads(Path(args.input).read_text(encoding='utf-8')))
            else:
                result = stats(database, args.begin, args.finish)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
