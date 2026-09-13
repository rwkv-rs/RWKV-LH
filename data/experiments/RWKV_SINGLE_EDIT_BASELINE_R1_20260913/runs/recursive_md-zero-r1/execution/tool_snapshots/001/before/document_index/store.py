from __future__ import annotations
import sqlite3

def existing(database):
    return sqlite3.connect(database)

def synchronize(database, root, documents):
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS documents (path TEXT PRIMARY KEY, content TEXT NOT NULL, digest TEXT NOT NULL, search TEXT NOT NULL, mtime INTEGER NOT NULL)')
        connection.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        metadata = dict(connection.execute('SELECT key,value FROM metadata'))
        old = dict(connection.execute('SELECT path,mtime FROM documents'))
        counts = {'added': 0, 'updated': 0, 'deleted': 0, 'unchanged': 0}
        for row in documents:
            if old.get(row['path']) == row['mtime']:
                counts['unchanged'] += 1
                continue
            counts['updated' if row['path'] in old else 'added'] += 1
            connection.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?)', (row['path'], row['content'], row['digest'], row['search'], row['mtime']))
            connection.commit()
        generation = int(metadata.get('generation', '0')) + 1
        connection.execute("INSERT OR REPLACE INTO metadata VALUES ('root',?)", (str(root),))
        connection.execute("INSERT OR REPLACE INTO metadata VALUES ('generation',?)", (str(generation),))
        return {**counts, 'generation': generation}

def status(database):
    with existing(database) as connection:
        metadata = dict(connection.execute('SELECT key,value FROM metadata'))
        count = connection.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        return {'document_count': count, 'generation': int(metadata['generation']), 'root': metadata['root']}
