from __future__ import annotations
import hashlib
import os
import unicodedata

def normalize(value):
    return unicodedata.normalize('NFC', value).casefold()

def collect(root):
    if not root.is_dir():
        raise ValueError('document root is not a directory')
    rows = []
    for directory, names, files in os.walk(root, followlinks=False):
        from pathlib import Path
        base = Path(directory)
        names[:] = sorted(name for name in names if not (base / name).is_symlink())
        for name in sorted(files):
            path = base / name
            if path.is_symlink() or path.suffix.lower() not in ('.txt', '.md'):
                continue
            content = path.read_bytes()
            text = content.decode('utf-8')
            rows.append({'path': path.relative_to(root).as_posix(), 'content': text,
                         'digest': hashlib.sha256(content).hexdigest(),
                         'search': normalize(text), 'mtime': path.stat().st_mtime_ns})
    return sorted(rows, key=lambda row: row['path'])
