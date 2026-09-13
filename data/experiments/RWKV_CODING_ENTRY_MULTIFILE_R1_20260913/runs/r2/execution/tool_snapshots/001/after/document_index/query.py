from __future__ import annotations
from .documents import normalize
from .store import existing

def query(database, text):
    if not text.strip():
        raise ValueError('query must be nonempty')
    with existing(database) as connection:
        rows = connection.execute('SELECT path FROM documents WHERE instr(search,?) > 0 ORDER BY path', (normalize(text),)).fetchall()
    matches = [{'path': row[0]} for row in rows]
    return {'count': len(matches), 'matches': matches}
