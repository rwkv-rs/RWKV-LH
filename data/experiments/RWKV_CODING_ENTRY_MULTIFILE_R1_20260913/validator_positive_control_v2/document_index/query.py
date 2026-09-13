from __future__ import annotations
from .documents import normalize
from .store import existing

def query(database, text, limit=None):
    if limit is not None and limit <= 0: raise ValueError('positive limit required')
    if not text.strip():
        raise ValueError('query must be nonempty')
    with existing(database) as connection:
        rows = connection.execute('SELECT path FROM documents WHERE instr(search,?) > 0 ORDER BY path', (normalize(text),)).fetchall()
    matches = [{'path': row[0]} for row in rows]
    matches = matches if limit is None else matches[:limit]
    return {'count': len(matches), 'matches': matches}
