"""Compatibility namespace for the irwkv feature backend."""

from rwkv_lh.state_router.local_backend import (
    LocalIRWKVExtractor,
    LocalIRWKVSettings,
)

__all__ = [
    "LocalIRWKVExtractor",
    "LocalIRWKVSettings",
]
