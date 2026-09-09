"""RWKV7 tensor geometry shared by artifact and StateTune adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RWKV7Layout:
    layers: int
    width: int
    heads: int
    head_size: int
    intermediate: int
    vocab: int
    decay_rank: int
    a_rank: int
    v_rank: int
    gate_rank: int
    dtype: str

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if name != "dtype" and (type(value) is not int or value <= 0):
                raise ValueError(f"RWKV7 {name} must be a positive integer")
        if self.width != self.heads * self.head_size:
            raise ValueError("RWKV7 head geometry differs from hidden width")
        if self.dtype not in {"float32", "float16", "bfloat16"}:
            raise ValueError("unsupported RWKV7 parameter dtype")

    @property
    def portable_state_shape(self) -> tuple[int, int, int, int]:
        """Layer, head, value, key; recurrent kernels use key, value instead."""
        return self.layers, self.heads, self.head_size, self.head_size

    @classmethod
    def from_native_weights(cls, weights: Mapping[str, Any]) -> "RWKV7Layout":
        def shape(name: str) -> tuple[int, ...]:
            if name not in weights:
                raise ValueError(f"RWKV7 layout is missing {name}")
            return tuple(int(size) for size in weights[name].shape)

        layers = sorted({int(name.split(".")[1]) for name in weights if name.startswith("blocks.")})
        if not layers or layers != list(range(len(layers))):
            raise ValueError("RWKV7 layer identities must be contiguous from zero")
        embedding = shape("emb.weight")
        if len(embedding) != 2 or shape("head.weight") != embedding:
            raise ValueError("RWKV7 embedding/output dimensions disagree")
        vocab, width = embedding
        heads = shape("blocks.0.att.r_k")
        ffn = shape("blocks.0.ffn.key.weight")
        if len(heads) != 2 or len(ffn) != 2 or ffn[1] != width:
            raise ValueError("RWKV7 head/FFN tensor geometry is invalid")

        def rank(layer: int, name: str) -> int:
            dimensions = shape(f"blocks.{layer}.att.{name}1")
            if len(dimensions) != 2 or dimensions[0] != width:
                raise ValueError(f"RWKV7 {name} rank tensor differs from hidden width")
            return dimensions[1]

        return cls(len(layers), width, heads[0], heads[1], ffn[0], vocab,
            rank(0, "w"), rank(0, "a"), rank(1 if len(layers) > 1 else 0, "v"),
            rank(0, "g"), str(weights["emb.weight"].dtype).removeprefix("torch."))

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "RWKV7Layout":
        return cls(config["num_hidden_layers"], config["hidden_size"], config["num_attention_heads"],
            config["head_size"], config["intermediate_size"], config["vocab_size"],
            config["decay_low_rank_dim"], config["a_low_rank_dim"], config["v_low_rank_dim"],
            config["gate_low_rank_dim"], config["torch_dtype"])

    def artifact_config(self, *, context_length: int, source_sha256: str,
                        bos_token_id: int = 0, eos_token_id: int = 0) -> dict[str, Any]:
        if type(context_length) is not int or context_length < 1:
            raise ValueError("RWKV7 context length must be explicitly positive")
        if len(source_sha256) != 64 or any(char not in "0123456789abcdef" for char in source_sha256):
            raise ValueError("RWKV7 source SHA-256 is invalid")
        if any(type(token) is not int or not 0 <= token < self.vocab for token in (bos_token_id, eos_token_id)):
            raise ValueError("RWKV7 special token is outside the actual vocabulary")
        return {
            "architectures": ["Rwkv7ForCausalLM"], "model_type": "rwkv7",
            "num_hidden_layers": self.layers, "hidden_size": self.width,
            "num_attention_heads": self.heads, "head_size": self.head_size,
            "intermediate_size": self.intermediate, "vocab_size": self.vocab,
            "decay_low_rank_dim": self.decay_rank, "a_low_rank_dim": self.a_rank,
            "v_low_rank_dim": self.v_rank, "gate_low_rank_dim": self.gate_rank,
            "torch_dtype": self.dtype, "context_length": context_length,
            "max_position_embeddings": context_length, "bos_token_id": bos_token_id,
            "eos_token_id": eos_token_id, "pad_token_id": eos_token_id,
            "embedding_layer_norm_fused": False, "tie_word_embeddings": False,
            "rwkv_source_sha256": source_sha256,
        }
