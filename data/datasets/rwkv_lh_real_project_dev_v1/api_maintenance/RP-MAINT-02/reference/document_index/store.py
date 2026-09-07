from __future__ import annotations
import sqlite3

def existing(database):
    return sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)

def synchronize(database, root, documents):
    with sqlite3.connect(database) as connection:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE IF NOT EXISTS documents (path TEXT PRIMARY KEY, content TEXT NOT NULL, digest TEXT NOT NULL, search TEXT NOT NULL, mtime INTEGER NOT NULL)')
        connection.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        metadata = dict(connection.execute('SELECT key,value FROM metadata'))
        if metadata.get('root', str(root)) != str(root):
            raise ValueError('index belongs to another document root')
        old = dict(connection.execute('SELECT path,digest FROM documents'))
        current = {row['path']: row for row in documents}
        added = set(current) - set(old)
        deleted = set(old) - set(current)
        updated = {name for name in set(current) & set(old) if current[name]['digest'] != old[name]}
        unchanged = len(current) - len(added) - len(updated)
        for name in sorted(added | updated):
            row = current[name]
            connection.execute('INSERT INTO documents(path,content,digest,search,mtime) VALUES (?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET content=excluded.content,digest=excluded.digest,search=excluded.search,mtime=excluded.mtime', (name, row['content'], row['digest'], row['search'], row['mtime']))
        connection.executemany('DELETE FROM documents WHERE path=?', [(name,) for name in sorted(deleted)])
        generation = int(metadata.get('generation', '0')) + int(bool(added or updated or deleted))
        connection.execute("INSERT INTO metadata VALUES ('root',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(root),))
        connection.execute("INSERT INTO metadata VALUES ('generation',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(generation),))
        return {'added': len(added), 'updated': len(updated), 'deleted': len(deleted), 'unchanged': unchanged, 'generation': generation}

def status(database):
    with existing(database) as connection:
        metadata = dict(connection.execute('SELECT key,value FROM metadata'))
        count = connection.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        return {'document_count': count, 'generation': int(metadata['generation']), 'root': metadata['root']}
