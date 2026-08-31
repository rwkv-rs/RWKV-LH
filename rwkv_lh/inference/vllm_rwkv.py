"""Persistent direct-model adapter for the pinned local vllm-rwkv runtime.

This module is imported by the dedicated Router process, not by the Harness
process.  All vLLM and CUDA imports remain lazy so the product runtime keeps a
small dependency boundary and a separate GPU/process lifecycle.
"""

from __future__ import annotations

import os
import threading
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from rwkv_lh.state_router.local_backend import (
    LocalVLLMRWKVExtractor,
    LocalVLLMRWKVSettings,
)
from rwkv_lh.state_router.model import HiddenFeatures


class PersistentVLLMRWKVExtractor(LocalVLLMRWKVExtractor):
    """Load one 0.4B model once and serve serialized feature extraction calls."""

    def __init__(self, settings: LocalVLLMRWKVSettings | None = None) -> None:
        super().__init__(settings)
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._runtime: dict[str, Any] | None = None
        self._initial_wkv_state: Any | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
        """Validate the frozen identity and eagerly place the model on CUDA."""

        if self._model is not None:
            return
        base = self._load_base_identity()
        engine_root = self.settings.engine_root.resolve()
        os.environ.setdefault("VLLM_ALLOW_INSECURE_SERIALIZATION", "1")
        os.environ.setdefault("VLLM_USE_V2_MODEL_RUNNER", "1")
        os.environ["VLLM_RWKV7_WKV_MODE"] = self.settings.wkv_mode

        import torch
        import transformers
        import vllm
        import vllm.rwkv7_ops  # noqa: F401
        from vllm.tokenizers.rwkv import RWKVTokenizer

        module_path = Path(vllm.__file__).resolve()
        if not module_path.is_relative_to(engine_root):
            raise RuntimeError(
                f"vllm resolved outside the pinned source tree: {module_path}"
            )
        tokenizer = RWKVTokenizer.from_pretrained(self.settings.model.resolve())
        model = self._load_direct_model(self.settings.model.resolve())
        initial_wkv_state = self._load_initial_wkv_state(model)
        profile = model.execution_profile
        runtime = {
            "model_class": type(model).__name__,
            "hidden_size": int(model.hidden_size),
            "num_hidden_layers": int(model.total_num_layers),
            "head_size": int(model.head_size),
            "vocab_size": int(model.vocab_size),
            "wkv_mode": str(profile.wkv_mode),
            "wkv_state_dtype": str(profile.wkv_state_dtype),
            "gemm_accumulation_policy": str(profile.gemm_accumulation_policy),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "device": torch.cuda.get_device_name(),
            "vllm_module": str(module_path),
            "vllm_version": vllm.__version__,
            "transformers_version": transformers.__version__,
            "runtime_temp": str(self.settings.runtime_temp.resolve()),
            "runtime_compute_dtype": str(model.z["blocks.0.att.key.weight"].dtype),
        }
        tokenizer_values = {
            "tokenizer_class": type(tokenizer).__name__,
            "tokenizer_vocab_size": int(tokenizer.vocab_size),
            "bos_token_id": int(tokenizer.bos_token_id),
            "eos_token_id": int(tokenizer.eos_token_id),
            "pad_token_id": int(tokenizer.pad_token_id),
            "truncation_side": str(tokenizer.truncation_side),
        }
        comparisons = {
            "vllm_module": runtime["vllm_module"],
            "vllm_version": runtime["vllm_version"],
            "engine_torch_version": runtime["torch_version"],
            "engine_transformers_version": runtime["transformers_version"],
            "hidden_size": runtime["hidden_size"],
            "num_hidden_layers": runtime["num_hidden_layers"],
            "head_size": runtime["head_size"],
            "vocab_size": runtime["vocab_size"],
            "wkv_mode": runtime["wkv_mode"],
            **tokenizer_values,
        }
        mismatches = {
            key: {"expected": base[key], "actual": value}
            for key, value in comparisons.items()
            if base[key] != value
        }
        if mismatches:
            raise RuntimeError(f"persistent vllm-rwkv identity mismatch: {mismatches}")
        self._model = model
        self._tokenizer = tokenizer
        self._runtime = runtime
        self._initial_wkv_state = initial_wkv_state

    def _load_initial_wkv_state(self, model: Any) -> Any | None:
        """Load one explicitly pinned selector state without changing model weights."""

        manifest = self.settings.state_profile_manifest
        if manifest is None:
            return None
        from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
            RWKV7InitialStateProfiles,
        )

        profiles = RWKV7InitialStateProfiles.load(
            str(manifest.resolve()),
            self.settings.state_profile_manifest_sha256,
            model_artifact=str(self.settings.model.resolve()),
            model_revision=self.settings.model_artifact_engine_revision,
            total_num_layers=int(model.total_num_layers),
            total_num_heads=int(model.num_attention_heads),
            layer_offset=0,
            num_layers=int(model.total_num_layers),
            tp_size=1,
            tp_rank=0,
            num_heads=int(model.num_attention_heads),
            head_size=int(model.head_size),
            device=model.z["blocks.0.att.key.weight"].device,
            dtype=model.wkv_state_dtype,
        )
        profile = profiles.resolve(self.settings.state_profile_id)
        if profile.state_sha256 != self.settings.state_profile_sha256:
            raise ValueError("local RWKV state-profile SHA-256 mismatch")
        if profile.wkv_state is None:
            if profile.profile_id != "zero" or profile.state_sha256 != "0" * 64:
                raise ValueError("local RWKV state profile has invalid zero identity")
            return None
        return profile.wkv_state

    def _new_state(self, batch_size: int) -> Any:
        assert self._model is not None
        state = self._model.zero_state(batch_size)
        if self._initial_wkv_state is not None:
            initial = self._initial_wkv_state.unsqueeze(1).expand(
                -1, batch_size, -1, -1, -1
            )
            state[1].copy_(initial)
        return state

    def _state_for_advance(
        self,
        parent_state: Sequence[Any] | None,
        torch_module: Any,
    ) -> Any:
        """Create one authoritative mutable CUDA state from an immutable parent."""

        if parent_state is None:
            return self._new_state(1)
        if len(parent_state) != 3:
            raise ValueError("persistent vllm-rwkv parent state must have 3 tensors")
        assert self._model is not None
        state = self._model.zero_state(1)
        for index, (source, destination) in enumerate(zip(parent_state, state)):
            if not isinstance(source, torch_module.Tensor):
                raise TypeError(
                    f"persistent vllm-rwkv parent state {index} is not a tensor"
                )
            if tuple(source.shape) != tuple(destination.shape):
                raise ValueError(
                    f"persistent vllm-rwkv parent state {index} shape mismatch"
                )
            if source.dtype != destination.dtype:
                raise ValueError(
                    f"persistent vllm-rwkv parent state {index} dtype mismatch"
                )
            if source.is_floating_point() and not bool(
                torch_module.isfinite(source).all()
            ):
                raise ValueError(
                    f"persistent vllm-rwkv parent state {index} is non-finite"
                )
            destination.copy_(source.to(device=destination.device))
        return state

    def _stateful_token_ids(self, text: str, *, continuation: bool) -> list[int]:
        assert self._tokenizer is not None
        token_ids = self._tokenizer.encode(
            str(text),
            truncation=False,
            add_special_tokens=not continuation,
        )
        if not token_ids or len(token_ids) > self.settings.max_tokens:
            raise ValueError("persistent vllm-rwkv state advance token count is invalid")
        return token_ids

    def advance_hidden_feature(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        feature_protocol: str = "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]:
        """Advance one durable Selector lane and expose one unmodified hidden view."""

        if not str(text):
            raise ValueError("persistent vllm-rwkv state advance text must be non-empty")
        if feature_protocol not in {
            "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
            "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        }:
            raise ValueError("unsupported stateful hidden feature protocol")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent vllm-rwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            token_ids = self._stateful_token_ids(text, continuation=continuation)
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor(
                [token_ids], dtype=torch.long, device="cuda"
            )
            hidden = self._model.forward_all_hidden(tokens, state)
            feature = (
                hidden[0, -1]
                if feature_protocol.endswith("-last.v1")
                else hidden[0].float().mean(dim=0)
            ).detach().float().cpu()
            exported_state = [
                value.detach().cpu().contiguous().clone() for value in state
            ]
            if not bool(torch.isfinite(feature).all()):
                raise RuntimeError(
                    "persistent vllm-rwkv returned non-finite stateful hidden features"
                )
            identity = {
                **self._load_base_identity(),
                "feature_protocol": feature_protocol,
                "extraction": (
                    "causal-lane-final-layer-last-real-token"
                    if feature_protocol.endswith("-last.v1")
                    else "causal-lane-current-segment-real-token-mean"
                ),
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return feature, exported_state, len(token_ids), identity

    def advance_hidden_last(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]:
        """Compatibility wrapper for the registered last-hidden protocol."""

        return self.advance_hidden_feature(
            text,
            parent_state=parent_state,
            continuation=continuation,
            feature_protocol="rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        )

    def advance_hidden_views(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Mapping[str, Any], list[Any], int, Mapping[str, Any]]:
        """Advance once and expose unchanged mean and last hidden views.

        This is an extraction-only optimization for fixed ablations. It does
        not generate, sample, mutate model weights, or advance the supplied
        parent state twice.
        """

        if not str(text):
            raise ValueError("persistent vllm-rwkv state advance text must be non-empty")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent vllm-rwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            token_ids = self._stateful_token_ids(text, continuation=continuation)
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor([token_ids], dtype=torch.long, device="cuda")
            hidden = self._model.forward_all_hidden(tokens, state)
            features = {
                "mean": hidden[0].float().mean(dim=0).detach().float().cpu(),
                "last": hidden[0, -1].detach().float().cpu(),
            }
            if any(not bool(torch.isfinite(value).all()) for value in features.values()):
                raise RuntimeError(
                    "persistent vllm-rwkv returned non-finite stateful hidden views"
                )
            exported_state = [
                value.detach().cpu().contiguous().clone() for value in state
            ]
            identity = {
                **self._load_base_identity(),
                "feature_protocols": {
                    "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                    "last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                },
                "extraction": "one-forward-current-segment-real-token-mean-and-last",
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return features, exported_state, len(token_ids), identity

    def advance_hidden_suffix_views(
        self,
        text: str,
        *,
        suffix_start: int,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Mapping[str, Any], list[Any], int, int, int, Mapping[str, Any]]:
        """Advance once and pool unchanged hidden rows from an exact text suffix.

        The caller supplies a character boundary, but the method accepts it only
        when separately tokenizing the prefix and suffix reproduces the exact
        one-piece token sequence.  This exposes request-tail features without
        adding an artificial recurrent-state boundary.
        """

        if not str(text):
            raise ValueError("persistent vllm-rwkv state advance text must be non-empty")
        if not 0 < int(suffix_start) < len(str(text)):
            raise ValueError("persistent vllm-rwkv suffix boundary is invalid")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent vllm-rwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            value = str(text)
            token_ids = self._stateful_token_ids(value, continuation=continuation)
            prefix_ids = self._tokenizer.encode(
                value[:suffix_start],
                truncation=False,
                add_special_tokens=not continuation,
            )
            suffix_ids = self._tokenizer.encode(
                value[suffix_start:],
                truncation=False,
                add_special_tokens=False,
            )
            if not prefix_ids or not suffix_ids or token_ids != prefix_ids + suffix_ids:
                raise ValueError(
                    "persistent vllm-rwkv suffix boundary is not token additive"
                )
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor([token_ids], dtype=torch.long, device="cuda")
            hidden = self._model.forward_all_hidden(tokens, state)
            suffix_hidden = hidden[0, len(prefix_ids) :]
            features = {
                "mean": suffix_hidden.float().mean(dim=0).detach().float().cpu(),
                "last": suffix_hidden[-1].detach().float().cpu(),
            }
            if any(not bool(torch.isfinite(item).all()) for item in features.values()):
                raise RuntimeError(
                    "persistent vllm-rwkv returned non-finite suffix hidden views"
                )
            exported_state = [
                item.detach().cpu().contiguous().clone() for item in state
            ]
            identity = {
                **self._load_base_identity(),
                "feature_protocols": {
                    "mean": "rwkv-lh.vllm-rwkv-final-hidden-suffix-mean.v1",
                    "last": "rwkv-lh.vllm-rwkv-final-hidden-suffix-last.v1",
                },
                "extraction": "one-forward-exact-additive-suffix-mean-and-last",
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "one_forward": True,
                "token_sequence_exact": True,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return (
                features,
                exported_state,
                len(token_ids),
                len(prefix_ids),
                len(suffix_ids),
                identity,
            )

    def advance_hidden_global_suffix_views(
        self,
        text: str,
        *,
        suffix_start: int,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Mapping[str, Any], list[Any], int, int, int, Mapping[str, Any]]:
        """Advance once and expose global, exact-suffix, and final hidden views.

        The exact additive suffix check is identical to
        :meth:`advance_hidden_suffix_views`.  All returned tensors are direct
        reductions or copies of the same unmodified ``forward_all_hidden``
        result, so the authoritative recurrent state advances exactly once.
        """

        if not str(text):
            raise ValueError("persistent vllm-rwkv state advance text must be non-empty")
        if not 0 < int(suffix_start) < len(str(text)):
            raise ValueError("persistent vllm-rwkv suffix boundary is invalid")
        if continuation != (parent_state is not None):
            raise ValueError(
                "persistent vllm-rwkv continuation and parent state must agree"
            )
        import torch

        with self._lock, torch.inference_mode():
            self.load()
            assert self._tokenizer is not None and self._model is not None
            value = str(text)
            token_ids = self._stateful_token_ids(value, continuation=continuation)
            prefix_ids = self._tokenizer.encode(
                value[:suffix_start],
                truncation=False,
                add_special_tokens=not continuation,
            )
            suffix_ids = self._tokenizer.encode(
                value[suffix_start:],
                truncation=False,
                add_special_tokens=False,
            )
            if not prefix_ids or not suffix_ids or token_ids != prefix_ids + suffix_ids:
                raise ValueError(
                    "persistent vllm-rwkv suffix boundary is not token additive"
                )
            state = self._state_for_advance(parent_state, torch)
            tokens = torch.tensor([token_ids], dtype=torch.long, device="cuda")
            hidden = self._model.forward_all_hidden(tokens, state)
            suffix_hidden = hidden[0, len(prefix_ids) :]
            features = {
                "global_mean": hidden[0].float().mean(dim=0).detach().float().cpu(),
                "suffix_mean": suffix_hidden.float()
                .mean(dim=0)
                .detach()
                .float()
                .cpu(),
                "final_last": hidden[0, -1].detach().float().cpu(),
            }
            if any(not bool(torch.isfinite(item).all()) for item in features.values()):
                raise RuntimeError(
                    "persistent vllm-rwkv returned non-finite global/suffix hidden views"
                )
            exported_state = [
                item.detach().cpu().contiguous().clone() for item in state
            ]
            identity = {
                **self._load_base_identity(),
                "feature_protocols": {
                    "global_mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                    "suffix_mean": (
                        "rwkv-lh.vllm-rwkv-final-hidden-suffix-mean.v1"
                    ),
                    "final_last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                },
                "extraction": (
                    "one-forward-global-mean-exact-additive-suffix-mean-and-final-last"
                ),
                "runtime": dict(self._runtime or {}),
                "persistent_process": True,
                "continuation": continuation,
                "one_forward": True,
                "token_sequence_exact": True,
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            }
            self._last_identity = identity
            return (
                features,
                exported_state,
                len(token_ids),
                len(prefix_ids),
                len(suffix_ids),
                identity,
            )

    @staticmethod
    def _load_direct_model(model_path: Path) -> Any:
        import json

        import torch
        from safetensors import safe_open
        from vllm.config.compilation import CompilationConfig, CompilationMode
        from vllm.config.vllm import set_current_vllm_config
        from vllm.model_executor.models import rwkv7
        from vllm.model_executor.models.rwkv7 import RWKV7ForCausalLM
        from vllm.transformers_utils.configs.rwkv7 import RWKV7Config

        config_values = json.loads(
            (model_path / "config.json").read_text(encoding="utf-8")
        )
        config = RWKV7Config(**config_values)
        dtype_name = str(config_values.get("torch_dtype") or "float16").removeprefix(
            "torch."
        )
        dtype_by_name = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }
        if dtype_name not in dtype_by_name:
            raise ValueError(f"unsupported direct RWKV7 dtype: {dtype_name}")
        rwkv7.get_tensor_model_parallel_world_size = lambda: 1
        rwkv7.get_tensor_model_parallel_rank = lambda: 0
        model_config = SimpleNamespace(
            hf_config=config,
            enforce_eager=True,
            dtype=dtype_by_name[dtype_name],
            head_dtype=None,
        )
        vllm_config = SimpleNamespace(
            compilation_config=CompilationConfig(mode=CompilationMode.NONE),
            model_config=model_config,
            quant_config=None,
            parallel_config=None,
        )
        with set_current_vllm_config(vllm_config):
            model = RWKV7ForCausalLM(vllm_config=vllm_config)
        weights_path = model_path / "model.safetensors"
        with safe_open(weights_path, framework="pt", device="cpu") as weights:
            loaded = model.load_weights(
                (name, weights.get_tensor(name)) for name in weights.keys()
            )
        manifest = json.loads((model_path / "manifest.json").read_text(encoding="utf-8"))
        expected = int((manifest.get("generation") or {}).get("weight_count") or 0)
        if expected < 1 or len(loaded) != expected:
            raise RuntimeError(
                f"persistent vllm-rwkv loaded {len(loaded)} weights, expected {expected}"
            )
        model.eval()
        return model

    def _token_rows(self, texts: Sequence[str]) -> list[list[int]]:
        self.load()
        assert self._tokenizer is not None
        rows = [
            self._tokenizer.encode(
                str(text),
                truncation=True,
                max_length=self.settings.max_tokens,
                add_special_tokens=True,
            )
            for text in texts
        ]
        if not rows or any(not row for row in rows):
            raise ValueError("persistent vllm-rwkv token rows must be non-empty")
        return rows

    def _extract_matrix(
        self,
        operation: str,
        texts: Sequence[str],
        *,
        codes: Sequence[str] = (),
        layer_index: int = -1,
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        if not texts or any(not str(text).strip() for text in texts):
            raise ValueError("persistent vllm-rwkv texts must be non-empty")
        import torch

        with self._lock, torch.inference_mode():
            token_rows = self._token_rows(texts)
            assert self._model is not None
            model = self._model
            layer_count = int(model.total_num_layers)
            resolved_layer = layer_index if layer_index >= 0 else layer_count + layer_index
            if not 0 <= resolved_layer < layer_count:
                raise ValueError("WKV layer index is outside the local model")
            code_token_ids: list[int] = []
            if codes:
                assert self._tokenizer is not None
                for code in codes:
                    encoded = self._tokenizer.encode(
                        f" {code}", add_special_tokens=False
                    )
                    if len(encoded) != 1:
                        raise ValueError(
                            f"constrained code is not one RWKV token: {code!r}"
                        )
                    code_token_ids.append(int(encoded[0]))
            buckets: dict[int, list[int]] = defaultdict(list)
            for index, row in enumerate(token_rows):
                buckets[len(row)].append(index)
            result_rows: list[Any | None] = [None] * len(token_rows)
            if operation in {"hidden_mean", "hidden_last"}:
                ordered = sorted(range(len(token_rows)), key=lambda index: len(token_rows[index]))
                for start in range(0, len(ordered), self.settings.batch_size):
                    batch_indices = ordered[start : start + self.settings.batch_size]
                    maximum = max(len(token_rows[index]) for index in batch_indices)
                    tokens = torch.full(
                        (len(batch_indices), maximum),
                        int(self._tokenizer.pad_token_id),
                        dtype=torch.long,
                        device="cuda",
                    )
                    for local_index, source_index in enumerate(batch_indices):
                        row = token_rows[source_index]
                        tokens[local_index, : len(row)] = torch.tensor(
                            row, dtype=torch.long, device="cuda"
                        )
                    state = self._new_state(len(batch_indices))
                    hidden = model.forward_all_hidden(tokens, state)
                    for local_index, source_index in enumerate(batch_indices):
                        token_count = len(token_rows[source_index])
                        if operation == "hidden_mean":
                            value = hidden[local_index, :token_count].float().mean(dim=0)
                        else:
                            value = hidden[local_index, token_count - 1].float()
                        result_rows[source_index] = value.detach().cpu()
                matrix = torch.stack(result_rows)
                if not bool(torch.isfinite(matrix).all()):
                    raise RuntimeError(
                        "persistent vllm-rwkv returned non-finite hidden features"
                    )
                protocols = {
                    "hidden_mean": (
                        "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                        "final-layer-all-real-token-mean",
                    ),
                    "hidden_last": (
                        "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                        "final-layer-last-real-token",
                    ),
                }
                feature_protocol, extraction = protocols[operation]
                identity = {
                    **self._load_base_identity(),
                    "feature_protocol": feature_protocol,
                    "extraction": extraction,
                    "runtime": dict(self._runtime or {}),
                    "persistent_process": True,
                    "batch_padding": "right-pad-excluded-from-feature-pooling",
                }
                self._last_identity = identity
                return matrix, [len(row) for row in token_rows], identity
            for token_count in sorted(buckets):
                indices = buckets[token_count]
                for start in range(0, len(indices), self.settings.batch_size):
                    batch_indices = indices[start : start + self.settings.batch_size]
                    tokens = torch.tensor(
                        [token_rows[index] for index in batch_indices],
                        dtype=torch.long,
                        device="cuda",
                    )
                    state = self._new_state(len(batch_indices))
                    hidden = model.forward_all_hidden(tokens, state)
                    if operation == "wkv_statistics":
                        recurrent = state[1][resolved_layer].float()
                        values = torch.cat(
                            (
                                recurrent.mean(dim=-1).flatten(1),
                                recurrent.mean(dim=-2).flatten(1),
                                recurrent.diagonal(dim1=-2, dim2=-1).flatten(1),
                                recurrent.square().mean(dim=-1).sqrt().flatten(1),
                            ),
                            dim=1,
                        )
                    elif operation == "code_logits":
                        logits = model.project_logits_fp32(hidden[:, -1, :])
                        code_index = torch.tensor(
                            code_token_ids,
                            dtype=torch.long,
                            device=logits.device,
                        )
                        values = logits.index_select(1, code_index).float()
                    else:
                        raise ValueError(
                            f"unsupported persistent vllm-rwkv operation: {operation}"
                        )
                    values = values.detach().float().cpu()
                    for local_index, source_index in enumerate(batch_indices):
                        result_rows[source_index] = values[local_index]
            if any(row is None for row in result_rows):
                raise RuntimeError("persistent extraction left unfilled rows")
            matrix = torch.stack(result_rows)
            if not bool(torch.isfinite(matrix).all()):
                raise RuntimeError("persistent vllm-rwkv returned non-finite features")
        protocols = {
            "hidden_mean": (
                "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                "final-layer-all-real-token-mean",
            ),
            "hidden_last": (
                "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                "final-layer-last-real-token",
            ),
            "wkv_statistics": (
                "rwkv-lh.vllm-rwkv-final-wkv-statistics.v1",
                "last-layer-row-column-diagonal-rms",
            ),
            "code_logits": (
                "rwkv-lh.vllm-rwkv-constrained-code-logits.v1",
                "last-token-fp32-lm-head-selected-codes",
            ),
        }
        feature_protocol, extraction = protocols[operation]
        identity = {
            **self._load_base_identity(),
            "feature_protocol": feature_protocol,
            "extraction": extraction,
            "runtime": dict(self._runtime or {}),
            "persistent_process": True,
        }
        self._last_identity = identity
        return matrix, [len(row) for row in token_rows], identity

    def extract(self, texts: Sequence[str]) -> list[HiddenFeatures]:
        matrix, token_counts, _ = self._extract_matrix("hidden_mean", texts)
        return [
            HiddenFeatures(
                values=tuple(float(value) for value in row.tolist()),
                model_hash=self.model_hash,
                token_count=token_count,
            )
            for row, token_count in zip(matrix, token_counts, strict=True)
        ]

    def extract_wkv_statistics(
        self,
        texts: Sequence[str],
        *,
        layer_index: int = -1,
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        return self._extract_matrix(
            "wkv_statistics", texts, layer_index=layer_index
        )

    def extract_last_hidden(
        self,
        texts: Sequence[str],
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        """Return final-layer last-real-token hidden vectors as FP32."""

        return self._extract_matrix("hidden_last", texts)

    def extract_hidden_pair(
        self,
        texts: Sequence[str],
    ) -> tuple[Any, Any, list[int], Mapping[str, Any]]:
        """Extract last-token and real-token-mean features from one forward."""

        if not texts or any(not str(text).strip() for text in texts):
            raise ValueError("persistent vllm-rwkv texts must be non-empty")
        import torch

        with self._lock, torch.inference_mode():
            token_rows = self._token_rows(texts)
            assert self._model is not None
            assert self._tokenizer is not None
            model = self._model
            ordered = sorted(
                range(len(token_rows)), key=lambda index: len(token_rows[index])
            )
            last_rows: list[Any | None] = [None] * len(token_rows)
            mean_rows: list[Any | None] = [None] * len(token_rows)
            for start in range(0, len(ordered), self.settings.batch_size):
                batch_indices = ordered[start : start + self.settings.batch_size]
                maximum = max(len(token_rows[index]) for index in batch_indices)
                tokens = torch.full(
                    (len(batch_indices), maximum),
                    int(self._tokenizer.pad_token_id),
                    dtype=torch.long,
                    device="cuda",
                )
                for local_index, source_index in enumerate(batch_indices):
                    row = token_rows[source_index]
                    tokens[local_index, : len(row)] = torch.tensor(
                        row, dtype=torch.long, device="cuda"
                    )
                # Fresh feature extraction must honor the explicitly pinned
                # immutable profile just like every other non-continuation
                # path.  Calling ``model.zero_state`` here silently bypasses
                # ``_initial_wkv_state`` and makes tuned/zero pair features
                # indistinguishable regardless of the registered profile.
                state = self._new_state(len(batch_indices))
                hidden = model.forward_all_hidden(tokens, state)
                for local_index, source_index in enumerate(batch_indices):
                    token_count = len(token_rows[source_index])
                    last_rows[source_index] = (
                        hidden[local_index, token_count - 1].float().detach().cpu()
                    )
                    mean_rows[source_index] = (
                        hidden[local_index, :token_count]
                        .float()
                        .mean(dim=0)
                        .detach()
                        .cpu()
                    )
            last = torch.stack(last_rows)
            mean = torch.stack(mean_rows)
            if not bool(torch.isfinite(last).all() and torch.isfinite(mean).all()):
                raise RuntimeError(
                    "persistent vllm-rwkv returned non-finite hidden features"
                )
        identity = {
            **self._load_base_identity(),
            "feature_protocols": {
                "last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
            },
            "extraction": "one-forward-last-and-real-token-mean",
            "runtime": dict(self._runtime or {}),
            "persistent_process": True,
            "batch_padding": "right-pad-excluded-from-feature-pooling",
        }
        self._last_identity = identity
        return last, mean, [len(row) for row in token_rows], identity

    def extract_hidden_prefix_mean_pair(
        self,
        texts: Sequence[str],
        prefixes: Sequence[str],
    ) -> tuple[Any, Any, list[int], list[int], Mapping[str, Any]]:
        """Extract full and causal-prefix means from the same RWKV forward."""

        if (
            not texts
            or len(texts) != len(prefixes)
            or any(not str(text).strip() for text in texts)
            or any(not str(prefix).strip() for prefix in prefixes)
        ):
            raise ValueError("persistent vllm-rwkv text/prefix rows must align")
        import torch

        with self._lock, torch.inference_mode():
            token_rows = self._token_rows(texts)
            assert self._model is not None
            assert self._tokenizer is not None
            prefix_counts = []
            for text, prefix, full_tokens in zip(texts, prefixes, token_rows):
                if not str(text).startswith(str(prefix)):
                    raise ValueError("hidden prefix must be an exact text prefix")
                prefix_tokens = self._tokenizer.encode(
                    str(prefix),
                    truncation=False,
                    add_special_tokens=True,
                )
                common = 0
                for left, right in zip(prefix_tokens, full_tokens):
                    if left != right:
                        break
                    common += 1
                if common < 4 or common > len(full_tokens):
                    raise ValueError("hidden prefix token alignment is too short")
                prefix_counts.append(common)
            model = self._model
            ordered = sorted(
                range(len(token_rows)), key=lambda index: len(token_rows[index])
            )
            full_mean_rows: list[Any | None] = [None] * len(token_rows)
            prefix_mean_rows: list[Any | None] = [None] * len(token_rows)
            for start in range(0, len(ordered), self.settings.batch_size):
                batch_indices = ordered[start : start + self.settings.batch_size]
                maximum = max(len(token_rows[index]) for index in batch_indices)
                tokens = torch.full(
                    (len(batch_indices), maximum),
                    int(self._tokenizer.pad_token_id),
                    dtype=torch.long,
                    device="cuda",
                )
                for local_index, source_index in enumerate(batch_indices):
                    row = token_rows[source_index]
                    tokens[local_index, : len(row)] = torch.tensor(
                        row, dtype=torch.long, device="cuda"
                    )
                state = self._new_state(len(batch_indices))
                hidden = model.forward_all_hidden(tokens, state)
                for local_index, source_index in enumerate(batch_indices):
                    token_count = len(token_rows[source_index])
                    prefix_count = prefix_counts[source_index]
                    full_mean_rows[source_index] = (
                        hidden[local_index, :token_count]
                        .float()
                        .mean(dim=0)
                        .detach()
                        .cpu()
                    )
                    prefix_mean_rows[source_index] = (
                        hidden[local_index, :prefix_count]
                        .float()
                        .mean(dim=0)
                        .detach()
                        .cpu()
                    )
            full_mean = torch.stack(full_mean_rows)
            prefix_mean = torch.stack(prefix_mean_rows)
            if not bool(
                torch.isfinite(full_mean).all() and torch.isfinite(prefix_mean).all()
            ):
                raise RuntimeError(
                    "persistent vllm-rwkv returned non-finite prefix features"
                )
        identity = {
            **self._load_base_identity(),
            "feature_protocols": {
                "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                "prefix_mean": "rwkv-lh.vllm-rwkv-causal-prefix-hidden-mean-lcp.v1",
            },
            "extraction": "one-forward-full-and-causal-prefix-token-mean",
            "runtime": dict(self._runtime or {}),
            "persistent_process": True,
            "batch_padding": "right-pad-excluded-from-feature-pooling",
            "prefix_alignment": "longest-common-token-prefix",
        }
        self._last_identity = identity
        return (
            full_mean,
            prefix_mean,
            [len(row) for row in token_rows],
            prefix_counts,
            identity,
        )

    def score_single_token_codes(
        self,
        prompts: Sequence[str],
        codes: Sequence[str],
    ) -> Any:
        if not codes or len(set(codes)) != len(codes):
            raise ValueError("constrained Router codes must be unique and non-empty")
        matrix, _, _ = self._extract_matrix("code_logits", prompts, codes=codes)
        return matrix


__all__ = ["PersistentVLLMRWKVExtractor"]
