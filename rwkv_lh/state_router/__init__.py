"""Compatibility namespace for the vllm-rwkv feature backend."""

from rwkv_lh.state_router.local_backend import (
    LocalVLLMRWKVExtractor,
    LocalVLLMRWKVSettings,
)

__all__ = [
    "LocalVLLMRWKVExtractor",
    "LocalVLLMRWKVSettings",
]
