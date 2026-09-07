from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from document_index.documents import collect
from document_index.store import synchronize, status
from document_index.query import query

def main():
    parser = argparse.ArgumentParser(description='Incremental Unicode document index')
    commands = parser.add_subparsers(dest='command', required=True)
    sync = commands.add_parser('sync'); sync.add_argument('--root', required=True); sync.add_argument('--db', required=True)
    find = commands.add_parser('query'); find.add_argument('--db', required=True); find.add_argument('--text', required=True)
    info = commands.add_parser('status'); info.add_argument('--db', required=True)
    arguments = parser.parse_args()
    try:
        database = Path(arguments.db)
        if arguments.command == 'sync':
            root = Path(arguments.root).resolve()
            result = synchronize(database, root, collect(root))
        elif arguments.command == 'query':
            result = query(database, arguments.text)
        else:
            result = status(database)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as error:
        print(json.dumps({'error': type(error).__name__ + ': ' + str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
