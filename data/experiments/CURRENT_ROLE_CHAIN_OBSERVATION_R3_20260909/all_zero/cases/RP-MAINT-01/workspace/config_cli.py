from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from config_store.migrations import migrate, restore
from config_store.values import read_values

def main():
    parser = argparse.ArgumentParser(description='Versioned SQLite configuration maintenance')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('migrate', 'restore'):
        sub = commands.add_parser(name)
        sub.add_argument('--db', required=True)
        sub.add_argument('--backup', required=True)
    for name in ('get', 'list'):
        sub = commands.add_parser(name)
        sub.add_argument('--db', required=True)
        if name == 'get':
            sub.add_argument('--key', required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command == 'migrate':
            result = migrate(Path(arguments.db), Path(arguments.backup))
        elif arguments.command == 'restore':
            result = restore(Path(arguments.db), Path(arguments.backup))
        else:
            result = read_values(Path(arguments.db))
            if arguments.command == 'get':
                result = next((item for item in result['settings'] if item['key'] == arguments.key), None)
                if result is None:
                    raise ValueError('unknown key')
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({'error': type(error).__name__ + ': ' + str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
