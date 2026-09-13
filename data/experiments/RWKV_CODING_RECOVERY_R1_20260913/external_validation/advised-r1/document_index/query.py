from __future__ import annotations
from typing import Optional

from .documents import normalize
from .store import existing

def query(database, text: str, limit: Optional[int] = None) -> dict:
    if not text.strip():
        raise ValueError('query must be nonempty')
    if limit is not None and (limit <= 0 or not isinstance(limit, int)):
        raise ValueError('limit must be a positive integer')
    with existing(database) as connection:
        rows = connection.execute('SELECT path FROM documents WHERE instr(search,?) > 0 ORDER BY path', (normalize(text),)).fetchmany(limit or None)
    matches = [{'path': row[0]} for row in rows]
    return {'count': len(matches), 'matches': matches}
