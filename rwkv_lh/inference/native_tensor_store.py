"""Bounded process-local Native tensor storage; disk export is opt-in analysis."""
from __future__ import annotations

import os
from typing import Any


class NativeTensorStore:
    def __init__(self, mode: str, capacity_bytes: int = 64 * 1024**3) -> None:
        if mode not in {'memory', 'disk'}:
            raise ValueError('RWKV_NATIVE_TENSOR_STORAGE must be memory or disk')
        if type(capacity_bytes) is not int or capacity_bytes < 1:
            raise ValueError('Native memory State capacity must be positive')
        self.mode = mode
        self.capacity_bytes = capacity_bytes
        self.used_bytes = 0
        self._entries: dict[tuple[int, str], tuple[dict[str, Any], int]] = {}

    @classmethod
    def from_environment(cls) -> NativeTensorStore:
        return cls(os.getenv('RWKV_NATIVE_TENSOR_STORAGE', 'memory'),
                   int(os.getenv('RWKV_NATIVE_MEMORY_STORE_BYTES', str(64 * 1024**3))))

    def put(self, rank: int, key: str, payload: dict[str, Any]) -> None:
        """Never evict a State that an active lane may still need."""
        size = sum(payload[k].numel() * payload[k].element_size()
                   for k in ('shift_state', 'wkv_state'))
        prior = self._entries.get((rank, key))
        used = self.used_bytes - (prior[1] if prior else 0) + size
        if used > self.capacity_bytes:
            raise MemoryError('Native memory State capacity reached; release finished lanes')
        stored = dict(payload)
        for k in ('shift_state', 'wkv_state'):
            stored[k] = payload[k].detach().to(device='cpu', copy=True)
        self._entries[(rank, key)] = (stored, size)
        self.used_bytes = used

    def get(self, rank: int, key: str) -> dict[str, Any]:
        return self._entries[(rank, key)][0]

    def delete(self, rank: int, key: str) -> None:
        prior = self._entries.pop((rank, key), None)
        if prior is not None:
            self.used_bytes -= prior[1]

    def clear(self) -> None:
        self._entries.clear()
        self.used_bytes = 0
