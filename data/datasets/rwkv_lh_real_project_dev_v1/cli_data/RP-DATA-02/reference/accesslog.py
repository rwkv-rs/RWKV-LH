"""Restart-safe JSONL ingestion with event deduplication and prefix validation."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.microsecond:
        raise ValueError('invalid timestamp')
    return int(parsed.timestamp())


def event(value):
    if not isinstance(value, dict) or set(value) != {'id','timestamp','path','status','bytes'}:
        raise ValueError('invalid event')
    if not isinstance(value['id'], str) or not value['id'].strip():
        raise ValueError('invalid id')
    if not isinstance(value['path'], str) or not value['path'].startswith('/'):
        raise ValueError('invalid path')
    if type(value['status']) is not int or not 100 <= value['status'] <= 599:
        raise ValueError('invalid status')
    if type(value['bytes']) is not int or value['bytes'] < 0:
        raise ValueError('invalid byte count')
    return value['id'], timestamp(value['timestamp']), value['path'], value['status'], value['bytes']


def connect(path):
    connection = sqlite3.connect(path)
    connection.executescript('''
      CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, timestamp INTEGER, path TEXT, status INTEGER, bytes INTEGER);
      CREATE TABLE IF NOT EXISTS sources (path TEXT PRIMARY KEY, offset INTEGER, digest TEXT);
      CREATE TABLE IF NOT EXISTS rejected (source TEXT, offset INTEGER, reason TEXT, PRIMARY KEY(source,offset));
    ''')
    return connection


def ingest(connection, source):
    source = Path(source).resolve()
    data = source.read_bytes()
    previous = connection.execute('SELECT offset,digest FROM sources WHERE path=?', (str(source),)).fetchone()
    offset = previous[0] if previous else 0
    if previous and (len(data) < offset or hashlib.sha256(data[:offset]).hexdigest() != previous[1]):
        raise ValueError('previously consumed source was truncated or rewritten')
    result = {'inserted':0,'duplicates':0,'rejected':0,'offset':offset}
    with connection:
        while True:
            end = data.find(b'\n', offset)
            if end < 0:
                break
            line = data[offset:end]
            reason = None
            try:
                value = json.loads(line.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                reason = 'invalid_json'
            if reason is None:
                try:
                    item = event(value)
                except (TypeError, ValueError, AttributeError, OverflowError):
                    reason = 'invalid_event'
            if reason is None:
                existing = connection.execute('SELECT timestamp,path,status,bytes FROM events WHERE id=?', (item[0],)).fetchone()
                if existing is not None:
                    if existing == item[1:]:
                        result['duplicates'] += 1
                    else:
                        reason = 'conflicting_id'
                else:
                    connection.execute('INSERT INTO events VALUES (?,?,?,?,?)', item)
                    result['inserted'] += 1
            if reason is not None:
                connection.execute('INSERT INTO rejected VALUES (?,?,?)', (str(source), offset, reason))
                result['rejected'] += 1
            offset = end+1
        connection.execute('INSERT INTO sources VALUES (?,?,?) ON CONFLICT(path) DO UPDATE SET offset=excluded.offset,digest=excluded.digest',
                           (str(source), offset, hashlib.sha256(data[:offset]).hexdigest()))
    result['offset'] = offset
    return result


def query(connection, begin, finish, minimum, prefix):
    start, end = timestamp(begin), timestamp(finish)
    if start >= end or not 100 <= minimum <= 599:
        raise ValueError('invalid query range')
    output = {'count':0,'bytes':0,'by_status':{},'by_path':{}}
    for path, status, byte_count in connection.execute('SELECT path,status,bytes FROM events WHERE timestamp>=? AND timestamp<? AND status>=?', (start,end,minimum)):
        if not path.startswith(prefix):
            continue
        output['count'] += 1
        output['bytes'] += byte_count
        output['by_status'][str(status)] = output['by_status'].get(str(status), 0)+1
        path_total = output['by_path'].setdefault(path, {'count':0,'bytes':0})
        path_total['count'] += 1
        path_total['bytes'] += byte_count
    return output


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    load = commands.add_parser('ingest')
    load.add_argument('database')
    load.add_argument('source')
    stats = commands.add_parser('query')
    stats.add_argument('database')
    stats.add_argument('--from', dest='begin', required=True)
    stats.add_argument('--to', dest='finish', required=True)
    stats.add_argument('--status-min', type=int, default=100)
    stats.add_argument('--prefix', default='/')
    rejects = commands.add_parser('rejections')
    rejects.add_argument('database')
    args = parser.parse_args()
    try:
        with connect(args.database) as connection:
            if args.command == 'ingest':
                result = ingest(connection,args.source)
            elif args.command == 'query':
                result = query(connection,args.begin,args.finish,args.status_min,args.prefix)
            else:
                rows = [{'source':source,'offset':offset,'reason':reason} for source,offset,reason in connection.execute('SELECT source,offset,reason FROM rejected ORDER BY source,offset')]
                result = {'rejected':len(rows),'rows':rows}
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
