from __future__ import annotations
import hashlib

def normalize(value):
    return value.lower()

def collect(root):
    rows = []
    for path in sorted(root.glob('*.md')):
        content = path.read_bytes()
        text = content.decode('utf-8', errors='replace')
        rows.append({'path': path.name, 'content': text,
                     'digest': hashlib.sha256(content).hexdigest(),
                     'search': normalize(text), 'mtime': path.stat().st_mtime_ns})
    return rows
