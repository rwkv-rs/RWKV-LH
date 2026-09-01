"""Stateful local 2.9B Hidden+MLP Selector service with no text generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
from collections.abc import Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol

from rwkv_lh.exact_tool_selector.input_protocol import (
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.model_v2 import (
    NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
    NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
    NetworkSelectorMLPArtifact,
)
from rwkv_lh.exact_tool_selector.model_v3 import (
    NETWORK_SELECTOR_SOFT_MOE_HEAD_SCHEMA_VERSION,
    NetworkSelectorSoftMoEArtifact,
)
from rwkv_lh.exact_tool_selector.network_client import (
    NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA,
    NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkExactToolSelection,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest
from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
from rwkv_lh.state_router.local_backend import LocalVLLMRWKVSettings


_STATE_REF_PATTERN = re.compile(r"^NST-[0-9a-f]{32}\.pth$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_KEYS = {
    "schema_version", "run_id", "trace_id", "input_digest", "menu_digest",
    "eligible_labels", "bootstrap", "step", "parent", "expected_identity",
}
_PARENT_KEYS = {"checkpoint_id", "state_ref", "state_digest", "token_position"}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class NetworkSelectorServiceError(ValueError):
    """A request or persisted selector state violated the service contract."""


class _StatefulExtractor(Protocol):
    def advance_hidden_last(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]: ...

    def advance_hidden_feature(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        feature_protocol: str,
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]: ...

    def advance_hidden_views(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
    ) -> tuple[Mapping[str, Any], list[Any], int, Mapping[str, Any]]: ...


class _NetworkSelectorHead(Protocol):
    artifact: Any
    file_sha256: str

    @property
    def head_hash(self) -> str: ...

    @property
    def feature_protocol(self) -> str: ...

    @property
    def temperature(self) -> float: ...

    def raw_logits(self, features: Any) -> tuple[float, ...]: ...


class _TorchMLPReplay:
    """Tensor replay for one validated v1 MLP expert."""

    def __init__(self, artifact: NetworkSelectorMLPArtifact) -> None:
        import torch

        self.artifact = artifact
        self.feature_mean = torch.tensor(
            artifact.feature_mean, dtype=torch.float32
        )
        self.feature_std = torch.tensor(artifact.feature_std, dtype=torch.float32)
        self.shared_weight = torch.tensor(
            artifact.shared_weight, dtype=torch.float32
        )
        self.shared_bias = torch.tensor(artifact.shared_bias, dtype=torch.float32)
        self.layer_norm_weight = torch.tensor(
            artifact.layer_norm_weight, dtype=torch.float32
        )
        self.layer_norm_bias = torch.tensor(
            artifact.layer_norm_bias, dtype=torch.float32
        )
        self.head_weight = torch.tensor(artifact.head_weight, dtype=torch.float32)
        self.head_bias = torch.tensor(artifact.head_bias, dtype=torch.float32)

    def raw_logits_tensor(self, features: Any) -> Any:
        import torch

        values = torch.as_tensor(features, dtype=torch.float32, device="cpu")
        if tuple(values.shape) != (self.artifact.feature_dim,):
            raise ValueError("network Selector service feature dimension mismatch")
        if not bool(torch.isfinite(values).all()):
            raise ValueError("network Selector service features are non-finite")
        normalized = (values - self.feature_mean) / self.feature_std
        hidden = torch.nn.functional.gelu(
            torch.nn.functional.linear(
                normalized, self.shared_weight, self.shared_bias
            ),
            approximate="tanh",
        )
        hidden = torch.nn.functional.layer_norm(
            hidden,
            (self.artifact.hidden_dim,),
            self.layer_norm_weight,
            self.layer_norm_bias,
            1e-5,
        )
        logits = torch.nn.functional.linear(
            hidden, self.head_weight, self.head_bias
        )
        if not bool(torch.isfinite(logits).all()):
            raise RuntimeError("network Selector service logits are non-finite")
        return logits


class TorchNetworkSelectorHead:
    """Torch replay of the frozen MLP artifact; logits are returned unmodified."""

    def __init__(self, path: Path, expected_sha256: str) -> None:
        if _sha256_file(path) != expected_sha256:
            raise ValueError("network Selector head file SHA-256 mismatch")
        artifact = NetworkSelectorMLPArtifact.load(path)
        self.artifact = artifact
        self.file_sha256 = expected_sha256
        self._replay = _TorchMLPReplay(artifact)

    @property
    def head_hash(self) -> str:
        return self.artifact.head_hash

    @property
    def feature_protocol(self) -> str:
        return self.artifact.feature_protocol

    @property
    def temperature(self) -> float:
        return self.artifact.temperature

    def raw_logits(self, features: Any) -> tuple[float, ...]:
        logits = self._replay.raw_logits_tensor(features)
        return tuple(float(item) for item in logits.tolist())


class TorchNetworkSelectorSoftMoEHead:
    """Torch replay of the frozen Soft-MoE architecture and its raw logits."""

    def __init__(self, path: Path, expected_sha256: str) -> None:
        if _sha256_file(path) != expected_sha256:
            raise ValueError("network Selector Soft-MoE head file SHA-256 mismatch")
        artifact = NetworkSelectorSoftMoEArtifact.load(path)
        import torch

        self.artifact = artifact
        self.file_sha256 = expected_sha256
        self._old = _TorchMLPReplay(artifact.old_artifact)
        self._continuation = _TorchMLPReplay(artifact.continuation_artifact)
        self.feature_mean = torch.tensor(
            artifact.feature_mean, dtype=torch.float32
        )
        self.feature_std = torch.tensor(artifact.feature_std, dtype=torch.float32)
        self.gate_shared_weight = torch.tensor(
            artifact.gate_shared_weight, dtype=torch.float32
        )
        self.gate_shared_bias = torch.tensor(
            artifact.gate_shared_bias, dtype=torch.float32
        )
        self.gate_layer_norm_weight = torch.tensor(
            artifact.gate_layer_norm_weight, dtype=torch.float32
        )
        self.gate_layer_norm_bias = torch.tensor(
            artifact.gate_layer_norm_bias, dtype=torch.float32
        )
        self.gate_head_weight = torch.tensor(
            artifact.gate_head_weight, dtype=torch.float32
        )
        self.gate_head_bias = torch.tensor(
            artifact.gate_head_bias, dtype=torch.float32
        )

    @property
    def head_hash(self) -> str:
        return self.artifact.head_hash

    @property
    def feature_protocol(self) -> str:
        return self.artifact.feature_protocol

    @property
    def temperature(self) -> float:
        return self.artifact.temperature

    def raw_logits(self, features: Any) -> tuple[float, ...]:
        import torch

        values = torch.as_tensor(features, dtype=torch.float32, device="cpu")
        if tuple(values.shape) != (self.artifact.feature_dim,):
            raise ValueError("network Selector service feature dimension mismatch")
        if not bool(torch.isfinite(values).all()):
            raise ValueError("network Selector service features are non-finite")
        normalized = (values - self.feature_mean) / self.feature_std
        hidden = torch.nn.functional.gelu(
            torch.nn.functional.linear(
                normalized,
                self.gate_shared_weight,
                self.gate_shared_bias,
            ),
            approximate="tanh",
        )
        hidden = torch.nn.functional.layer_norm(
            hidden,
            (self.artifact.gate_hidden_dim,),
            self.gate_layer_norm_weight,
            self.gate_layer_norm_bias,
            1e-5,
        )
        gate_logit = torch.nn.functional.linear(
            hidden, self.gate_head_weight, self.gate_head_bias
        ).squeeze(0)
        gate = torch.sigmoid(gate_logit)
        old_logits = self._old.raw_logits_tensor(values)
        continuation_logits = self._continuation.raw_logits_tensor(values)
        logits = old_logits + gate * (continuation_logits - old_logits)
        if not bool(torch.isfinite(logits).all()):
            raise RuntimeError(
                "network Selector Soft-MoE service logits are non-finite"
            )
        return tuple(float(item) for item in logits.tolist())


def load_torch_network_selector_head(
    path: Path, expected_sha256: str
) -> _NetworkSelectorHead:
    """Fail closed while dispatching a frozen Selector artifact by schema."""

    if _sha256_file(path) != expected_sha256:
        raise ValueError("network Selector head file SHA-256 mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("network Selector head artifact must be a JSON object")
    schema_version = value.get("schema_version")
    if schema_version == NETWORK_SELECTOR_HEAD_SCHEMA_VERSION:
        return TorchNetworkSelectorHead(path, expected_sha256)
    if schema_version == NETWORK_SELECTOR_SOFT_MOE_HEAD_SCHEMA_VERSION:
        return TorchNetworkSelectorSoftMoEHead(path, expected_sha256)
    raise ValueError("unsupported network Selector head schema")


class NetworkSelectorStateStore:
    """Append-only dynamic recurrent states; learned profiles live elsewhere."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _paths(self, state_ref: str) -> tuple[Path, Path]:
        if not _STATE_REF_PATTERN.fullmatch(state_ref):
            raise NetworkSelectorServiceError("invalid network Selector state reference")
        state_path = self.root / state_ref
        metadata_path = self.root / f"{state_ref}.json"
        return state_path, metadata_path

    def save(
        self,
        state: Sequence[Any],
        *,
        request_digest: str,
        run_id: str,
        checkpoint_id: str,
        parent_state_digest: str,
        token_position: int,
        bootstrap_payload: Mapping[str, Any],
    ) -> tuple[str, str]:
        import torch

        if not _SHA256_PATTERN.fullmatch(request_digest):
            raise NetworkSelectorServiceError("invalid network Selector request digest")
        if len(state) != 3 or token_position < 1:
            raise NetworkSelectorServiceError("invalid network Selector recurrent state")
        state_ref = f"NST-{request_digest[:32]}.pth"
        state_path, metadata_path = self._paths(state_ref)
        if state_path.exists() or metadata_path.exists():
            if not state_path.is_file() or not metadata_path.is_file():
                raise NetworkSelectorServiceError(
                    "partial network Selector state commit exists"
                )
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("request_digest") != request_digest:
                raise NetworkSelectorServiceError("network Selector state ref collision")
            actual = _sha256_file(state_path)
            if metadata.get("state_digest") != actual:
                raise NetworkSelectorServiceError(
                    "persisted network Selector state digest mismatch"
                )
            return state_ref, actual
        payload = {
            "shift_state": state[0].detach().cpu().contiguous(),
            "wkv_state": state[1].detach().cpu().contiguous(),
            "elapsed": state[2].detach().cpu().contiguous(),
        }
        if any(not isinstance(value, torch.Tensor) for value in payload.values()):
            raise TypeError("network Selector state values must be tensors")
        temporary = state_path.with_name(f".{state_path.name}.tmp-{os.getpid()}")
        try:
            torch.save(payload, temporary)
            os.replace(temporary, state_path)
        finally:
            if temporary.exists():
                temporary.unlink()
        state_digest = _sha256_file(state_path)
        metadata = {
            "schema_version": "rwkv-lh.network-selector-dynamic-state.v1",
            "state_ref": state_ref,
            "state_digest": state_digest,
            "request_digest": request_digest,
            "run_id": run_id,
            "checkpoint_id": checkpoint_id,
            "parent_state_digest": parent_state_digest,
            "token_position": token_position,
            "bootstrap_payload": dict(bootstrap_payload),
            "tensor_contract": {
                name: {"shape": list(value.shape), "dtype": str(value.dtype)}
                for name, value in payload.items()
            },
        }
        _atomic_json(metadata_path, metadata)
        return state_ref, state_digest

    def load(
        self,
        state_ref: str,
        state_digest: str,
        *,
        run_id: str,
        checkpoint_id: str,
        token_position: int,
    ) -> tuple[list[Any], dict[str, Any]]:
        import torch

        state_path, metadata_path = self._paths(state_ref)
        if not state_path.is_file() or not metadata_path.is_file():
            raise NetworkSelectorServiceError("network Selector parent state is missing")
        if _sha256_file(state_path) != state_digest:
            raise NetworkSelectorServiceError("network Selector parent SHA-256 mismatch")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected = {
            "state_ref": state_ref,
            "state_digest": state_digest,
            "run_id": run_id,
            "checkpoint_id": checkpoint_id,
            "token_position": token_position,
        }
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise NetworkSelectorServiceError(
                "network Selector parent metadata mismatch"
            )
        payload = torch.load(state_path, map_location="cpu", weights_only=True)
        if not isinstance(payload, Mapping) or set(payload) != {
            "shift_state", "wkv_state", "elapsed"
        }:
            raise NetworkSelectorServiceError(
                "network Selector parent tensor container mismatch"
            )
        state = [payload["shift_state"], payload["wkv_state"], payload["elapsed"]]
        contract = metadata.get("tensor_contract")
        if not isinstance(contract, Mapping):
            raise NetworkSelectorServiceError("network Selector tensor contract missing")
        for name, value in zip(("shift_state", "wkv_state", "elapsed"), state):
            expected_tensor = contract.get(name)
            if not isinstance(value, torch.Tensor) or not isinstance(
                expected_tensor, Mapping
            ):
                raise NetworkSelectorServiceError(
                    "network Selector parent tensor type mismatch"
                )
            if list(value.shape) != expected_tensor.get("shape") or str(
                value.dtype
            ) != expected_tensor.get("dtype"):
                raise NetworkSelectorServiceError(
                    "network Selector parent tensor identity mismatch"
                )
            if value.is_floating_point() and not bool(torch.isfinite(value).all()):
                raise NetworkSelectorServiceError(
                    "network Selector parent tensor is non-finite"
                )
        return state, metadata

    def response(self, request_digest: str) -> dict[str, Any] | None:
        path = self.root / f"response-{request_digest}.json"
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("request_digest") != request_digest or not isinstance(
            value.get("response"), Mapping
        ):
            raise NetworkSelectorServiceError(
                "network Selector response journal mismatch"
            )
        return dict(value["response"])

    def save_response(
        self, request_digest: str, response: Mapping[str, Any]
    ) -> None:
        path = self.root / f"response-{request_digest}.json"
        value = {"request_digest": request_digest, "response": dict(response)}
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != value:
                raise NetworkSelectorServiceError(
                    "network Selector response journal collision"
                )
            return
        _atomic_json(path, value)


class NetworkSelectorService:
    """Validate, advance, classify, and durably commit one Selector step."""

    def __init__(
        self,
        settings: NetworkExactToolSelectorSettings,
        extractor: _StatefulExtractor,
        head: _NetworkSelectorHead,
        store: NetworkSelectorStateStore,
    ) -> None:
        if head.head_hash != settings.head_hash:
            raise ValueError("network Selector head hash mismatch")
        if head.file_sha256 != settings.head_sha256:
            raise ValueError("network Selector head file identity mismatch")
        if head.feature_protocol != settings.feature_protocol:
            raise ValueError("network Selector head feature identity mismatch")
        self.input_protocol = network_selector_input_protocol(
            settings.input_protocol
        )
        self._portable_feature_identity: dict[str, Any] | None = None
        if settings.feature_protocol == NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL:
            metadata = getattr(head.artifact, "metadata", None)
            portable = (
                metadata.get("portable_feature_identity")
                if isinstance(metadata, Mapping)
                else None
            )
            expected = {
                "batch_size": 1,
                "compact_input_schema_version": (
                    settings.input_protocol
                ),
                "feature_dim": head.artifact.feature_dim,
                "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
                "model_weights_sha256": settings.model_sha256,
                "persistent_history_replayed": True,
                "state_profile": {
                    "id": settings.state_profile_id,
                    "sha256": settings.state_profile_sha256,
                },
                "wkv_mode": "fp16",
            }
            if not isinstance(portable, Mapping) or any(
                portable.get(key) != value for key, value in expected.items()
            ):
                raise ValueError(
                    "network Selector fused head portable identity mismatch"
                )
            engine_revision = str(portable.get("engine_revision") or "")
            if len(engine_revision) != 40:
                raise ValueError(
                    "network Selector fused head engine revision is invalid"
                )
            self._portable_feature_identity = dict(portable)
        self.settings = settings
        self.extractor = extractor
        self.head = head
        self.store = store
        self._lock = threading.Lock()

    @staticmethod
    def _parse_prefixed_json(text: str, prefix: str) -> dict[str, Any]:
        if not text.startswith(prefix):
            raise NetworkSelectorServiceError(
                f"network Selector input lacks {prefix.rstrip()!r}"
            )
        try:
            value = json.loads(text[len(prefix) :])
        except json.JSONDecodeError as exc:
            raise NetworkSelectorServiceError(
                "network Selector rendered input is invalid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise NetworkSelectorServiceError(
                "network Selector rendered payload must be an object"
            )
        return value

    def _parse_compact_bootstrap(self, text: str) -> dict[str, Any]:
        marker = self.input_protocol.task_marker
        if text.count(marker) != 1:
            raise NetworkSelectorServiceError(
                "network Selector bootstrap must contain one menu and task"
            )
        menu_text, task_json = text.split(marker, 1)
        menu = self._parse_prefixed_json(
            menu_text, self.input_protocol.menu_prefix
        )
        task = self._parse_prefixed_json(
            self.input_protocol.task_prefix + task_json,
            self.input_protocol.task_prefix,
        )
        expected_task_fields = (
            {"schema_version"}
            if self.input_protocol.frontier_only_in_step
            else
            {"schema_version", "task_request_sha256"}
            if (
                self.input_protocol.current_requirement_in_step
                or self.input_protocol.current_question_in_step
            )
            else {"schema_version", "task_request"}
        )
        if set(task) != expected_task_fields or task.get(
            "schema_version"
        ) != self.settings.input_protocol:
            raise NetworkSelectorServiceError(
                "network Selector task fields changed"
            )
        return {**menu, **task}

    def _input_and_parent(
        self, request: Mapping[str, Any]
    ) -> tuple[NetworkSelectorInput, list[Any] | None, dict[str, Any] | None]:
        run_id = str(request["run_id"])
        step_text = str(request["step"])
        step = self._parse_prefixed_json(
            step_text, self.input_protocol.step_prefix
        )
        progress_value = step.get("progress")
        if not isinstance(progress_value, Mapping):
            raise NetworkSelectorServiceError("network Selector progress is missing")
        progress = NetworkSelectorProgress(
            completed_stage_count=int(progress_value.get("completed_stage_count", -1)),
            action_index=int(progress_value.get("action_index", -1)),
            succeeded_operations=tuple(progress_value.get("succeeded_operations") or ()),
            failed_operations=tuple(progress_value.get("failed_operations") or ()),
            protocol_rejection_count=int(
                progress_value.get("protocol_rejection_count", -1)
            ),
        )
        parent_value = request.get("parent")
        parent_state = None
        parent_metadata = None
        if parent_value is None:
            bootstrap_text = str(request["bootstrap"])
            bootstrap = self._parse_compact_bootstrap(bootstrap_text)
        else:
            if not isinstance(parent_value, Mapping) or set(parent_value) != _PARENT_KEYS:
                raise NetworkSelectorServiceError(
                    "network Selector parent contract mismatch"
                )
            if request["bootstrap"] != "":
                raise NetworkSelectorServiceError(
                    "network Selector continuation repeated bootstrap"
                )
            parent_state, parent_metadata = self.store.load(
                str(parent_value["state_ref"]),
                str(parent_value["state_digest"]),
                run_id=run_id,
                checkpoint_id=str(parent_value["checkpoint_id"]),
                token_position=int(parent_value["token_position"]),
            )
            bootstrap = parent_metadata.get("bootstrap_payload")
            if not isinstance(bootstrap, Mapping):
                raise NetworkSelectorServiceError(
                    "network Selector parent bootstrap is missing"
                )
        if self.input_protocol.frontier_only_in_step:
            current_question = str(step.get("current_question") or "")
            marker = "Current requirement: "
            if marker not in current_question:
                raise NetworkSelectorServiceError(
                    "network Selector frontier question is missing its requirement"
                )
            stage_objective = current_question.rsplit(marker, 1)[1].strip()
            if not stage_objective:
                raise NetworkSelectorServiceError(
                    "network Selector frontier requirement is empty"
                )
            # V8 deliberately carries no complete Goal semantics. This local
            # value exists only to satisfy the common immutable input object;
            # the v8 bootstrap renderer ignores it.
            task_request = stage_objective
        elif self.input_protocol.current_question_in_step:
            current_question = step.get("current_question")
            if not isinstance(current_question, Mapping) or set(current_question) != {
                "complete_requirement",
                "current_stage",
                "question",
            }:
                raise NetworkSelectorServiceError(
                    "network Selector current question fields changed"
                )
            task_request = str(current_question.get("complete_requirement") or "")
            stage_objective = str(current_question.get("current_stage") or "")
            if not str(current_question.get("question") or "").strip():
                raise NetworkSelectorServiceError(
                    "network Selector current question is missing"
                )
        else:
            task_request = str(
                (
                    step.get("current_requirement")
                    if self.input_protocol.current_requirement_in_step
                    else bootstrap.get("task_request")
                )
                or ""
            )
            stage_objective = str(step.get("stage_objective") or "")
        if (
            self.input_protocol.current_requirement_in_step
            or self.input_protocol.current_question_in_step
        ) and not self.input_protocol.frontier_only_in_step and hashlib.sha256(
            task_request.encode("utf-8")
        ).hexdigest() != bootstrap.get("task_request_sha256"):
            raise NetworkSelectorServiceError(
                "network Selector current requirement identity mismatch"
            )
        selector_input = NetworkSelectorInput.create(
            task_request=task_request,
            stage_objective=stage_objective,
            stage_role=str(step.get("stage_role") or ""),
            progress=progress,
            eligible_labels=tuple(request.get("eligible_labels") or ()),
        )
        if self.input_protocol.bootstrap_payload(selector_input) != dict(bootstrap):
            raise NetworkSelectorServiceError(
                "network Selector persisted bootstrap is not canonical"
            )
        if parent_value is None and (
            self.input_protocol.render_bootstrap(selector_input)
            != request["bootstrap"]
        ):
            raise NetworkSelectorServiceError(
                "network Selector bootstrap is not canonical"
            )
        if self.input_protocol.render_step(selector_input) != step_text:
            raise NetworkSelectorServiceError("network Selector step is not canonical")
        if self.input_protocol.menu_digest() != request["menu_digest"]:
            raise NetworkSelectorServiceError("network Selector menu digest mismatch")
        if self.input_protocol.input_digest(selector_input) != request["input_digest"]:
            raise NetworkSelectorServiceError("network Selector input digest mismatch")
        return selector_input, parent_state, parent_metadata

    def select(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if set(request) != _REQUEST_KEYS:
            raise NetworkSelectorServiceError("network Selector request fields mismatch")
        if request.get("schema_version") != NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA:
            raise NetworkSelectorServiceError(
                "unsupported network Selector request schema"
            )
        if request.get("expected_identity") != self.settings.runtime_identity():
            raise NetworkSelectorServiceError(
                "network Selector expected runtime identity mismatch"
            )
        if not str(request.get("run_id") or "").strip() or not str(
            request.get("trace_id") or ""
        ).strip():
            raise NetworkSelectorServiceError(
                "network Selector run/trace identity is missing"
            )
        request_digest = canonical_digest(dict(request))
        with self._lock:
            replay = self.store.response(request_digest)
            if replay is not None:
                return replay
            selector_input, parent_state, parent_metadata = self._input_and_parent(
                request
            )
            continuation = parent_state is not None
            step_segment = "\n" + self.input_protocol.render_step(selector_input)
            advance_feature = getattr(self.extractor, "advance_hidden_feature", None)
            advance_views = getattr(self.extractor, "advance_hidden_views", None)
            bootstrap_identity: Mapping[str, Any] | None = None
            if self.settings.feature_protocol == NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL:
                if not callable(advance_feature) or not callable(advance_views):
                    raise NetworkSelectorServiceError(
                        "extractor does not support same-forward fused features"
                    )
                consumed_tokens = 0
                if continuation:
                    views, next_state, step_tokens, views_identity = (
                        advance_views(
                            step_segment,
                            parent_state=parent_state,
                            continuation=True,
                        )
                    )
                    consumed_tokens += step_tokens
                else:
                    (
                        _bootstrap_feature,
                        bootstrap_state,
                        bootstrap_tokens,
                        bootstrap_identity,
                    ) = (
                        advance_feature(
                            self.input_protocol.render_bootstrap(selector_input),
                            parent_state=None,
                            continuation=False,
                            feature_protocol=(
                                "rwkv-lh.vllm-rwkv-final-hidden-last.v1"
                            ),
                        )
                    )
                    views, next_state, step_tokens, views_identity = (
                        advance_views(
                            step_segment,
                            parent_state=bootstrap_state,
                            continuation=True,
                        )
                    )
                    consumed_tokens += bootstrap_tokens + step_tokens
                if (
                    not isinstance(views, Mapping)
                    or set(views) != {"mean", "last"}
                    or views_identity.get("feature_protocols")
                    != {
                        "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                        "last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                    }
                ):
                    raise NetworkSelectorServiceError(
                        "network Selector fused-view extractor identity mismatch"
                    )
                import torch

                mean = torch.as_tensor(views["mean"], dtype=torch.float32).flatten()
                last = torch.as_tensor(views["last"], dtype=torch.float32).flatten()
                if (
                    len(mean) + len(last) != self.head.artifact.feature_dim
                    or len(mean) != len(last)
                ):
                    raise NetworkSelectorServiceError(
                        "network Selector fused-view dimensions mismatch"
                    )
                features = torch.cat((mean, last), dim=0)
                feature_identity = {
                    **dict(views_identity),
                    "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
                    "source_feature_protocols": dict(
                        views_identity["feature_protocols"]
                    ),
                    "same_current_forward_for_both_views": True,
                }
            elif callable(advance_feature):
                consumed_tokens = 0
                if continuation:
                    features, next_state, step_tokens, feature_identity = (
                        advance_feature(
                            step_segment,
                            parent_state=parent_state,
                            continuation=True,
                            feature_protocol=self.settings.feature_protocol,
                        )
                    )
                    consumed_tokens += step_tokens
                else:
                    (
                        _bootstrap_feature,
                        bootstrap_state,
                        bootstrap_tokens,
                        bootstrap_identity,
                    ) = (
                        advance_feature(
                            self.input_protocol.render_bootstrap(selector_input),
                            parent_state=None,
                            continuation=False,
                            feature_protocol=(
                                "rwkv-lh.vllm-rwkv-final-hidden-last.v1"
                            ),
                        )
                    )
                    features, next_state, step_tokens, feature_identity = (
                        advance_feature(
                            step_segment,
                            parent_state=bootstrap_state,
                            continuation=True,
                            feature_protocol=self.settings.feature_protocol,
                        )
                    )
                    consumed_tokens += bootstrap_tokens + step_tokens
            else:
                if self.settings.feature_protocol != (
                    "rwkv-lh.vllm-rwkv-final-hidden-last.v1"
                ):
                    raise NetworkSelectorServiceError(
                        "extractor does not support the configured feature protocol"
                    )
                text = (
                    step_segment
                    if continuation
                    else self.input_protocol.render_bootstrap(selector_input)
                    + step_segment
                )
                features, next_state, consumed_tokens, feature_identity = (
                    self.extractor.advance_hidden_last(
                        text,
                        parent_state=parent_state,
                        continuation=continuation,
                    )
                )
            if bootstrap_identity is not None and (
                bootstrap_identity.get("generated_rwkv_text") is not False
                or bootstrap_identity.get("sampling_invoked") is not False
            ):
                raise NetworkSelectorServiceError(
                    "network Selector bootstrap extractor invoked text generation"
                )
            if feature_identity.get("feature_protocol") != self.settings.feature_protocol:
                raise NetworkSelectorServiceError(
                    "network Selector extractor feature protocol mismatch"
                )
            if self._portable_feature_identity is not None and (
                feature_identity.get("model_weights_sha256")
                != self._portable_feature_identity["model_weights_sha256"]
                or feature_identity.get("engine_revision")
                != self._portable_feature_identity["engine_revision"]
                or feature_identity.get("wkv_mode")
                != self._portable_feature_identity["wkv_mode"]
            ):
                raise NetworkSelectorServiceError(
                    "network Selector extractor portable identity mismatch"
                )
            if feature_identity.get("generated_rwkv_text") is not False or feature_identity.get(
                "sampling_invoked"
            ) is not False:
                raise NetworkSelectorServiceError(
                    "network Selector extractor invoked text generation"
                )
            logits = self.head.raw_logits(features)
            selected_index = max(
                (
                    index
                    for index, label in enumerate(NETWORK_EXACT_TOOL_LABELS)
                    if label in set(selector_input.eligible_labels)
                ),
                key=lambda index: (logits[index], -index),
            )
            parent_value = request.get("parent")
            parent_digest = (
                "" if parent_value is None else str(parent_value["state_digest"])
            )
            parent_tokens = (
                0 if parent_value is None else int(parent_value["token_position"])
            )
            token_position = parent_tokens + consumed_tokens
            suffix = request_digest[:24]
            checkpoint_id = f"NSCP-{suffix}"
            state_ref, state_digest = self.store.save(
                next_state,
                request_digest=request_digest,
                run_id=str(request["run_id"]),
                checkpoint_id=checkpoint_id,
                parent_state_digest=parent_digest,
                token_position=token_position,
                bootstrap_payload=self.input_protocol.bootstrap_payload(
                    selector_input
                ),
            )
            selection = NetworkExactToolSelection(
                selection_id=f"NSEL-{suffix}",
                trace_id=str(request["trace_id"]),
                selected_operation=NETWORK_EXACT_TOOL_LABELS[selected_index],
                logits=logits,
                temperature=self.head.temperature,
                input_digest=str(request["input_digest"]),
                menu_digest=str(request["menu_digest"]),
                selector_checkpoint_id=checkpoint_id,
                selector_state_ref=state_ref,
                selector_state_digest=state_digest,
                selector_parent_state_digest=parent_digest,
                token_position=token_position,
                model=self.settings.model,
                model_sha256=self.settings.model_sha256,
                head_sha256=self.settings.head_sha256,
                profile_id=self.settings.state_profile_id,
                profile_sha256=self.settings.state_profile_sha256,
                eligible_labels=selector_input.eligible_labels,
            )
            response = {
                "schema_version": NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "runtime_identity": self.settings.runtime_identity(),
                "selection": selection.raw_record(),
            }
            self.store.save_response(request_digest, response)
            return response


def _handler(service: NetworkSelectorService):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, value: Mapping[str, Any]) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/healthz":
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"status": "ok", "runtime_identity": service.settings.runtime_identity()})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != service.input_protocol.endpoint:
                self._json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
                if length < 2 or length > 2_000_000:
                    raise NetworkSelectorServiceError("invalid request body size")
                value = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(value, Mapping):
                    raise NetworkSelectorServiceError("request body must be an object")
                response = service.select(value)
            except (NetworkSelectorServiceError, TypeError, ValueError) as exc:
                self._json(400, {"error": type(exc).__name__, "message": str(exc)[:2000]})
                return
            except Exception as exc:  # fail closed without exposing trace internals
                self._json(500, {"error": type(exc).__name__, "message": str(exc)[:1000]})
                return
            self._json(200, response)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def _extractor_state_profile_settings(
    *,
    profile_manifest: Path | None,
    profile_manifest_sha256: str,
    profile_id: str,
    profile_sha256: str,
) -> dict[str, object]:
    """Keep zero-State deployments independent of trained State manifests."""

    zero_sha256 = "0" * 64
    if profile_manifest is None:
        if (
            profile_manifest_sha256 != zero_sha256
            or profile_id != "zero"
            or profile_sha256 != zero_sha256
        ):
            raise ValueError(
                "a manifest-free Selector must use the exact zero-State identity"
            )
        return {
            "state_profile_manifest": None,
            "state_profile_manifest_sha256": "",
            "state_profile_id": "",
            "state_profile_sha256": "",
        }
    return {
        "state_profile_manifest": profile_manifest,
        "state_profile_manifest_sha256": profile_manifest_sha256,
        "state_profile_id": profile_id,
        "state_profile_sha256": profile_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=29621)
    parser.add_argument("--engine-root", type=Path, required=True)
    parser.add_argument("--engine-revision", required=True)
    parser.add_argument("--engine-python", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--head-sha256", required=True)
    parser.add_argument("--head-hash", required=True)
    parser.add_argument(
        "--input-protocol",
        default="rwkv-lh.exact-tool-selector-input.v3",
    )
    parser.add_argument("--profile-manifest", type=Path)
    parser.add_argument("--profile-manifest-sha256", default="0" * 64)
    parser.add_argument("--profile-id", default="zero")
    parser.add_argument("--profile-sha256", default="0" * 64)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--runtime-temp", type=Path, required=True)
    args = parser.parse_args()
    head = load_torch_network_selector_head(args.head, args.head_sha256)
    settings = NetworkExactToolSelectorSettings(
        base_url=f"http://{args.host}:{args.port}",
        model=args.model_name,
        model_sha256=args.model_sha256,
        head_sha256=args.head_sha256,
        head_hash=args.head_hash,
        feature_protocol=head.feature_protocol,
        state_profile_id=args.profile_id,
        state_profile_sha256=args.profile_sha256,
        state_profile_manifest_sha256=args.profile_manifest_sha256,
        input_protocol=args.input_protocol,
    )
    extractor_profile_settings = _extractor_state_profile_settings(
        profile_manifest=args.profile_manifest,
        profile_manifest_sha256=args.profile_manifest_sha256,
        profile_id=args.profile_id,
        profile_sha256=args.profile_sha256,
    )
    extractor = PersistentVLLMRWKVExtractor(
        LocalVLLMRWKVSettings(
            engine_root=args.engine_root,
            engine_revision=args.engine_revision,
            engine_python=args.engine_python,
            model=args.model_artifact,
            batch_size=1,
            max_tokens=2048,
            wkv_mode="fp16",
            runtime_temp=args.runtime_temp,
            compatibility_sha256="0" * 64,
            **extractor_profile_settings,
        )
    )
    service = NetworkSelectorService(
        settings,
        extractor,
        head,
        NetworkSelectorStateStore(args.state_dir),
    )
    extractor.load()
    server = ThreadingHTTPServer((args.host, args.port), _handler(service))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "NetworkSelectorService",
    "NetworkSelectorServiceError",
    "NetworkSelectorStateStore",
    "TorchNetworkSelectorHead",
    "TorchNetworkSelectorSoftMoEHead",
    "load_torch_network_selector_head",
]
