"""Project-owned inference-side adapters for separately deployed RWKV services."""

from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor


__all__ = ["PersistentVLLMRWKVExtractor"]
