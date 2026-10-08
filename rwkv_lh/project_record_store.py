"""Immutable exact JSON content for the Project event log.

Events identify a root, not another embedded copy of the entire history. Changed
paths add new nodes; existing input, output, token blocks and text are reused by
content identity. This storage encoding is never sent to a model.
"""
from collections import OrderedDict
import sys
import hashlib
import json

PROTOCOL = 'rwkv-lh.project-record-store.v1'
_TEXT_BLOCK = 2048
_LIST_BLOCK = 128
_NODE_CACHE_BYTE_LIMIT = 64 * 1024 * 1024


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def _digest(body):
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


class _VerifiedNodeCache:
    """Keep validated immutable nodes within this store's byte allowance.

    Expanded caller values are never cached. The allowance accounts for each
    retained node's object graph, key and conservative entry overhead; it is
    not a bound on SQLite buffers, returned histories or process RSS.
    """

    def __init__(self, load, byte_limit):
        self.load = load
        self.byte_limit = byte_limit
        self.entries = OrderedDict()
        self.retained_bytes = 0

    def _charge(self, key, node):
        total = sys.getsizeof(key) + 256
        pending, seen = [node], set()
        while pending and total <= self.byte_limit:
            value = pending.pop()
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            total += sys.getsizeof(value)
            if isinstance(value, list):
                pending.extend(value)
        return total

    def __call__(self, key):
        if key in self.entries:
            self.entries.move_to_end(key)
            return self.entries[key][0]
        # Load validates the digest and complete node shape before admission.
        node = self.load(key)
        charge = self._charge(key, node)
        if charge <= self.byte_limit:
            while self.retained_bytes + charge > self.byte_limit:
                _, (_, removed) = self.entries.popitem(last=False)
                self.retained_bytes -= removed
            self.entries[key] = (node, charge)
            self.retained_bytes += charge
        return node


class RecordStore:
    def __init__(self, connection):
        self.connection = connection
        # One transaction owns its verified-node cache. Bound retained memory
        # by bytes, so a small shared history does not thrash a node-count cap.
        self._node = _VerifiedNodeCache(self._load, _NODE_CACHE_BYTE_LIMIT)

    @staticmethod
    def create(connection):
        connection.execute('CREATE TABLE objects (digest TEXT PRIMARY KEY, body TEXT NOT NULL)')

    def _put(self, node):
        body = _json(node)
        key = _digest(body)
        cursor = self.connection.execute('INSERT OR IGNORE INTO objects VALUES (?,?)', (key, body))
        if not cursor.rowcount:
            actual = self.connection.execute('SELECT body FROM objects WHERE digest=?', (key,)).fetchone()
            if actual is None or actual[0] != body:
                raise ValueError('project record object digest mismatch')
        return key

    def _pack(self, value):
        if isinstance(value, dict):
            if any(not isinstance(key, str) for key in value):
                raise ValueError('project record keys must be strings')
            # Order is preserved, including the receipt insertion order.
            return [1, self._put(['map', [[key, self._pack(item)] for key, item in value.items()]])]
        if isinstance(value, list):
            blocks = [self._put(['block', [self._pack(item) for item in value[start:start + _LIST_BLOCK]]])
                      for start in range(0, len(value), _LIST_BLOCK)]
            return [1, self._put(['list', blocks])]
        if isinstance(value, str) and len(value) > _TEXT_BLOCK:
            blocks = [self._put(['string', value[start:start + _TEXT_BLOCK]])
                      for start in range(0, len(value), _TEXT_BLOCK)]
            return [1, self._put(['text', blocks])]
        if value is not None and type(value) not in (str, int, float, bool):
            raise ValueError('project records require JSON values')
        return [0, value]

    def write(self, value):
        packed = self._pack(value)
        key = packed[1] if packed[0] == 1 else self._put(['value', packed[1]])
        return {'protocol': PROTOCOL, 'root': key}

    @staticmethod
    def root(reference):
        if (not isinstance(reference, dict) or set(reference) != {'protocol', 'root'}
                or reference['protocol'] != PROTOCOL):
            raise ValueError('unsupported project ledger protocol or record root')
        return reference['root']

    @staticmethod
    def _reference(key):
        if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('invalid project record object digest')
        return key

    def _load(self, key):
        self._reference(key)
        row = self.connection.execute('SELECT body FROM objects WHERE digest=?', (key,)).fetchone()
        if row is None:
            raise ValueError('missing project record object digest: ' + key)
        if _digest(row[0]) != key:
            raise ValueError('project record object digest mismatch')
        node = json.loads(row[0])
        self._children(node)  # Validate before interpretation, even on direct current reads.
        return node

    @classmethod
    def _packed_child(cls, packed):
        if not isinstance(packed, list) or len(packed) != 2 or type(packed[0]) is not int:
            raise ValueError('invalid project record value')
        if packed[0] == 1:
            return [cls._reference(packed[1])]
        if packed[0] != 0 or (packed[1] is not None and type(packed[1]) not in (str, int, float, bool)):
            raise ValueError('invalid project record literal')
        _json(packed[1])  # Reject nonfinite scalars from tampered JSON too.
        return []

    @classmethod
    def _children(cls, node):
        if not isinstance(node, list) or len(node) != 2:
            raise ValueError('invalid project record node')
        kind, value = node
        if kind in ('list', 'text') and isinstance(value, list):
            return [cls._reference(key) for key in value]
        if kind == 'map' and isinstance(value, list):
            seen, children = set(), []
            for pair in value:
                if (not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], str)
                        or pair[0] in seen):
                    raise ValueError('invalid project record mapping')
                seen.add(pair[0]); children.extend(cls._packed_child(pair[1]))
            return children
        if kind == 'block' and isinstance(value, list) and len(value) <= _LIST_BLOCK:
            return [key for packed in value for key in cls._packed_child(packed)]
        if kind == 'string' and isinstance(value, str) and len(value) <= _TEXT_BLOCK:
            return []
        if kind == 'value':
            return cls._packed_child([0, value])
        raise ValueError('invalid project record node type')

    def verify(self, reference, seen):
        """Verify every reachable immutable node once in this read transaction."""
        def visit(key):
            if key in seen:
                return
            for child in self._children(self._node(key)):
                visit(child)
            seen.add(key)
        visit(self.root(reference))

    def read(self, reference):
        def unpack(packed):
            return expand(packed[1]) if packed[0] == 1 else packed[1]
        def expand(key):
            kind, value = self._node(key)
            if kind == 'map':
                return {name: unpack(item) for name, item in value}
            if kind == 'block':
                return [unpack(item) for item in value]
            if kind == 'list':
                if any(self._node(item)[0] != 'block' for item in value):
                    raise ValueError('invalid project record list block')
                return [item for block in value for item in expand(block)]
            if kind == 'text':
                if any(self._node(item)[0] != 'string' for item in value):
                    raise ValueError('invalid project record text block')
                return ''.join(expand(item) for item in value)
            return value
        return expand(self.root(reference))
