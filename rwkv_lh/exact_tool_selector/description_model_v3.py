"""Description-conditioned 2.9B Hidden+MLP exact-tool scorer."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


DESCRIPTION_SELECTOR_HEAD_SCHEMA = "rwkv-lh.description-conditioned-selector-head.v1"
DESCRIPTION_SELECTOR_FEATURE_PROTOCOL = "rwkv-lh.vllm-rwkv-final-hidden-last.v1"
DESCRIPTION_SELECTOR_FEATURE_PROTOCOLS = frozenset(
    {
        DESCRIPTION_SELECTOR_FEATURE_PROTOCOL,
        "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
    }
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _torch() -> Any:
    import torch

    return torch


class DescriptionConditionedSelectorNetwork:
    """Factory namespace for the shared scorer Torch module."""

    @staticmethod
    def create() -> Any:
        torch = _torch()

        class Network(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.query_projection = torch.nn.Linear(2560, 128)
                self.tool_projection = torch.nn.Linear(2560, 128)
                self.query_norm = torch.nn.LayerNorm(128, eps=1e-5)
                self.tool_norm = torch.nn.LayerNorm(128, eps=1e-5)
                self.pair_hidden = torch.nn.Linear(512, 64)
                self.dropout = torch.nn.Dropout(0.1)
                self.score = torch.nn.Linear(64, 1)

            def forward(self, queries: Any, tools: Any) -> Any:
                if queries.ndim != 2 or queries.shape[-1] != 2560:
                    raise ValueError("description Selector query feature shape mismatch")
                if tuple(tools.shape) != (25, 2560):
                    raise ValueError("description Selector tool feature shape mismatch")
                query_values = torch.nn.functional.layer_norm(queries, (2560,))
                tool_values = torch.nn.functional.layer_norm(tools, (2560,))
                query = self.query_norm(
                    torch.nn.functional.gelu(
                        self.query_projection(query_values), approximate="tanh"
                    )
                )
                tool = self.tool_norm(
                    torch.nn.functional.gelu(
                        self.tool_projection(tool_values), approximate="tanh"
                    )
                )
                query = query.unsqueeze(1).expand(-1, tools.shape[0], -1)
                tool = tool.unsqueeze(0).expand(queries.shape[0], -1, -1)
                pairs = torch.cat(
                    (query, tool, query * tool, (query - tool).abs()), dim=-1
                )
                hidden = torch.nn.functional.gelu(
                    self.pair_hidden(pairs), approximate="tanh"
                )
                return self.score(self.dropout(hidden)).squeeze(-1)

        return Network()


class DescriptionConditionedSelectorHead:
    """Validated raw-logit inference artifact with frozen tool features."""

    def __init__(self, path: Path, expected_sha256: str | None = None) -> None:
        torch = _torch()
        self.path = path.resolve()
        self.file_sha256 = sha256_file(self.path)
        if expected_sha256 is not None and self.file_sha256 != expected_sha256:
            raise ValueError("description Selector head SHA-256 mismatch")
        payload = torch.load(self.path, map_location="cpu", weights_only=True)
        if not isinstance(payload, Mapping) or payload.get("schema_version") != DESCRIPTION_SELECTOR_HEAD_SCHEMA:
            raise ValueError("unsupported description Selector head schema")
        if tuple(payload.get("labels") or ()) != NETWORK_EXACT_TOOL_LABELS:
            raise ValueError("description Selector label order changed")
        feature_protocol = str(payload.get("feature_protocol") or "")
        if feature_protocol not in DESCRIPTION_SELECTOR_FEATURE_PROTOCOLS:
            raise ValueError("description Selector feature protocol changed")
        self.menu_digest = str(payload.get("menu_digest") or "")
        if len(self.menu_digest) != 64:
            raise ValueError("description Selector menu digest is invalid")
        self.head_hash = str(payload.get("head_hash") or "")
        if len(self.head_hash) != 64:
            raise ValueError("description Selector head identity is invalid")
        temperature = float(payload.get("temperature") or 0.0)
        if not 0.0 < temperature < float("inf"):
            raise ValueError("description Selector temperature is invalid")
        self.temperature = temperature
        self.feature_protocol = feature_protocol
        self.feature_dim = 2560
        self.labels = NETWORK_EXACT_TOOL_LABELS
        self.metadata = dict(payload.get("metadata") or {})
        tools = payload.get("tool_features")
        if not isinstance(tools, torch.Tensor) or tuple(tools.shape) != (25, 2560):
            raise ValueError("description Selector tool features are invalid")
        if tools.dtype != torch.float32 or not bool(torch.isfinite(tools).all()):
            raise ValueError("description Selector tool features are non-finite")
        state_dict = payload.get("state_dict")
        if not isinstance(state_dict, Mapping):
            raise ValueError("description Selector state dictionary is missing")
        self.model = DescriptionConditionedSelectorNetwork.create().cpu().eval()
        self.model.load_state_dict(dict(state_dict), strict=True)
        if any(not bool(torch.isfinite(value).all()) for value in self.model.state_dict().values()):
            raise ValueError("description Selector model contains non-finite values")
        self.tool_features = tools.contiguous()

    def raw_logits(self, features: Sequence[float] | Any) -> tuple[float, ...]:
        torch = _torch()
        query = torch.as_tensor(features, dtype=torch.float32, device="cpu")
        if tuple(query.shape) != (2560,) or not bool(torch.isfinite(query).all()):
            raise ValueError("description Selector query feature is invalid")
        with torch.no_grad():
            logits = self.model(query.unsqueeze(0), self.tool_features)[0]
        if tuple(logits.shape) != (25,) or not bool(torch.isfinite(logits).all()):
            raise RuntimeError("description Selector produced invalid logits")
        return tuple(float(item) for item in logits.tolist())


__all__ = [
    "DESCRIPTION_SELECTOR_FEATURE_PROTOCOL",
    "DESCRIPTION_SELECTOR_FEATURE_PROTOCOLS",
    "DESCRIPTION_SELECTOR_HEAD_SCHEMA",
    "DescriptionConditionedSelectorHead",
    "DescriptionConditionedSelectorNetwork",
    "sha256_file",
]
