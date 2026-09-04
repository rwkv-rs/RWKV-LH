"""Local 2.9B fresh-state Hidden+MLP Selector service without generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
from collections.abc import Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol

from rwkv_lh.exact_tool_selector.head import (
    NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
    NetworkSelectorMLPArtifact,
)
from rwkv_lh.exact_tool_selector.input_protocol import (
    G1J_SELECTOR_INTENT_HEAD_ID,
    G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
    G1J_SELECTOR_TRAINING_TRAJECTORY_MODE,
    network_selector_input_protocol,
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
)
from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
from rwkv_lh.model_io import canonical_digest
from rwkv_lh.state_router.local_backend import LocalVLLMRWKVSettings


_REQUEST_KEYS = {
    "schema_version",
    "run_id",
    "trace_id",
    "input_digest",
    "menu_digest",
    "menu_order_id",
    "eligible_labels",
    "bootstrap",
    "step",
    "expected_identity",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class NetworkSelectorServiceError(ValueError):
    """A Selector request violated the frozen service contract."""


class _StatefulExtractor(Protocol):
    def advance_hidden_last(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        export_state: bool = True,
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]: ...

    def advance_hidden_feature(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        feature_protocol: str,
        export_state: bool = True,
    ) -> tuple[Any, list[Any], int, Mapping[str, Any]]: ...

    def advance_hidden_views(
        self,
        text: str,
        *,
        parent_state: Sequence[Any] | None = None,
        continuation: bool = False,
        export_state: bool = True,
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
    """Tensor replay for one validated MLP expert."""

    def __init__(self, artifact: NetworkSelectorMLPArtifact) -> None:
        import torch

        self.artifact = artifact
        self.feature_mean = torch.tensor(artifact.feature_mean, dtype=torch.float32)
        self.feature_std = torch.tensor(artifact.feature_std, dtype=torch.float32)
        self.shared_weight = torch.tensor(artifact.shared_weight, dtype=torch.float32)
        self.shared_bias = torch.tensor(artifact.shared_bias, dtype=torch.float32)
        self.layer_norm_weight = torch.tensor(
            artifact.layer_norm_weight, dtype=torch.float32
        )
        self.layer_norm_bias = torch.tensor(artifact.layer_norm_bias, dtype=torch.float32)
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
        logits = torch.nn.functional.linear(hidden, self.head_weight, self.head_bias)
        if not bool(torch.isfinite(logits).all()):
            raise RuntimeError("network Selector service logits are non-finite")
        return logits


class TorchNetworkSelectorHead:
    """Torch replay of the frozen MLP artifact; logits remain unmodified."""

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
        return tuple(float(item) for item in self._replay.raw_logits_tensor(features).tolist())


def load_torch_network_selector_head(
    path: Path, expected_sha256: str
) -> _NetworkSelectorHead:
    """Load the sole supported 23-class MLP artifact."""

    return TorchNetworkSelectorHead(path, expected_sha256)


class NetworkSelectorService:
    """Validate and classify one current subtask from a fresh initial state."""

    def __init__(
        self,
        settings: NetworkExactToolSelectorSettings,
        extractor: _StatefulExtractor,
        head: _NetworkSelectorHead,
    ) -> None:
        if head.head_hash != settings.head_hash:
            raise ValueError("network Selector head hash mismatch")
        if head.file_sha256 != settings.head_sha256:
            raise ValueError("network Selector head file identity mismatch")
        if head.feature_protocol != settings.feature_protocol:
            raise ValueError("network Selector head feature identity mismatch")
        self.input_protocol = network_selector_input_protocol(settings.input_protocol)
        metadata = getattr(head.artifact, "metadata", None)
        expected_head_identity = {
            "head_id": G1J_SELECTOR_INTENT_HEAD_ID,
            "compact_input_schema_version": settings.input_protocol,
            "model_weights_sha256": settings.model_sha256,
            "feature_protocol": settings.feature_protocol,
            "labels": list(NETWORK_EXACT_TOOL_LABELS),
            "training_trajectory_mode": G1J_SELECTOR_TRAINING_TRAJECTORY_MODE,
        }
        if not isinstance(metadata, Mapping) or any(
            metadata.get(key) != value for key, value in expected_head_identity.items()
        ):
            raise ValueError(
                "G1J Selector-Intent Head identity mismatch; retired Heads cannot be loaded"
            )
        self._portable_feature_identity: dict[str, Any] | None = None
        if settings.feature_protocol == NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL:
            portable = metadata.get("portable_feature_identity")
            expected = {
                "batch_size": 1,
                "compact_input_schema_version": settings.input_protocol,
                "feature_dim": head.artifact.feature_dim,
                "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
                "model_weights_sha256": settings.model_sha256,
                "fresh_initial_state_each_evaluation": True,
                "state_profile": {
                    "id": settings.state_profile_id,
                    "sha256": settings.state_profile_sha256,
                },
                "training_trajectory_mode": G1J_SELECTOR_TRAINING_TRAJECTORY_MODE,
                "wkv_mode": "fp16",
            }
            if not isinstance(portable, Mapping) or any(
                portable.get(key) != value for key, value in expected.items()
            ):
                raise ValueError("network Selector fused head portable identity mismatch")
            if len(str(portable.get("engine_revision") or "")) != 40:
                raise ValueError("network Selector fused head engine revision is invalid")
            self._portable_feature_identity = dict(portable)
        self.settings = settings
        self.extractor = extractor
        self.head = head
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

    def _parse_bootstrap(self, text: str) -> dict[str, Any]:
        marker = self.input_protocol.task_marker
        if text.count(marker) != 1:
            raise NetworkSelectorServiceError(
                "network Selector bootstrap must contain one menu and role"
            )
        menu_text, role_json = text.split(marker, 1)
        menu = self._parse_prefixed_json(menu_text, self.input_protocol.menu_prefix)
        role = self._parse_prefixed_json(
            self.input_protocol.task_prefix + role_json,
            self.input_protocol.task_prefix,
        )
        if set(role) != {"schema_version"} or role.get("schema_version") != (
            G1J_SELECTOR_INTENT_INPUT_PROTOCOL
        ):
            raise NetworkSelectorServiceError("network Selector role fields changed")
        return menu

    def _input(self, request: Mapping[str, Any]) -> NetworkSelectorInput:
        step_text = str(request["step"])
        step = self._parse_prefixed_json(step_text, self.input_protocol.step_prefix)
        if set(step) != {
            "schema_version",
            "role",
            "eligible_labels",
            "current_subtask",
            "current_question",
        }:
            raise NetworkSelectorServiceError(
                "G1J Selector-Intent prompt fields changed"
            )
        if (
            step.get("schema_version") != G1J_SELECTOR_INTENT_INPUT_PROTOCOL
            or step.get("role") != "selector_intent"
            or list(step.get("eligible_labels") or ())
            != list(request.get("eligible_labels") or ())
            or not isinstance(step.get("current_subtask"), Mapping)
        ):
            raise NetworkSelectorServiceError(
                "G1J Selector-Intent prompt identity changed"
            )
        selector_input = NetworkSelectorInput.create(
            current_subtask=dict(step["current_subtask"]),
            eligible_labels=tuple(request.get("eligible_labels") or ()),
            menu_order_id=str(request.get("menu_order_id") or ""),
        )
        bootstrap = self._parse_bootstrap(str(request["bootstrap"]))
        if self.input_protocol.bootstrap_payload(selector_input) != bootstrap:
            raise NetworkSelectorServiceError(
                "network Selector bootstrap payload is not canonical"
            )
        if self.input_protocol.render_bootstrap(selector_input) != request["bootstrap"]:
            raise NetworkSelectorServiceError(
                "network Selector bootstrap is not canonical"
            )
        if self.input_protocol.render_step(selector_input) != step_text:
            raise NetworkSelectorServiceError("network Selector step is not canonical")
        if self.input_protocol.menu_digest(selector_input) != request["menu_digest"]:
            raise NetworkSelectorServiceError("network Selector menu digest mismatch")
        if self.input_protocol.input_digest(selector_input) != request["input_digest"]:
            raise NetworkSelectorServiceError("network Selector input digest mismatch")
        return selector_input

    def _extract_features(self, full_text: str) -> tuple[Any, int, Mapping[str, Any]]:
        advance_feature = getattr(self.extractor, "advance_hidden_feature", None)
        advance_views = getattr(self.extractor, "advance_hidden_views", None)
        if self.settings.feature_protocol == NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL:
            if not callable(advance_views):
                raise NetworkSelectorServiceError(
                    "extractor does not support same-forward fused features"
                )
            views, _discarded_state, tokens, identity = advance_views(
                full_text,
                parent_state=None,
                continuation=False,
                export_state=False,
            )
            if (
                not isinstance(views, Mapping)
                or set(views) != {"mean", "last"}
                or identity.get("feature_protocols")
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
            if len(mean) != len(last) or len(mean) + len(last) != (
                self.head.artifact.feature_dim
            ):
                raise NetworkSelectorServiceError(
                    "network Selector fused-view dimensions mismatch"
                )
            features = torch.cat((mean, last), dim=0)
            feature_identity = {
                **dict(identity),
                "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
                "source_feature_protocols": dict(identity["feature_protocols"]),
                "same_current_forward_for_both_views": True,
            }
            return features, tokens, feature_identity
        if callable(advance_feature):
            features, _discarded_state, tokens, identity = advance_feature(
                full_text,
                parent_state=None,
                continuation=False,
                feature_protocol=self.settings.feature_protocol,
                export_state=False,
            )
            return features, tokens, identity
        if self.settings.feature_protocol != "rwkv-lh.vllm-rwkv-final-hidden-last.v1":
            raise NetworkSelectorServiceError(
                "extractor does not support the configured feature protocol"
            )
        features, _discarded_state, tokens, identity = self.extractor.advance_hidden_last(
            full_text,
            parent_state=None,
            continuation=False,
            export_state=False,
        )
        return features, tokens, identity

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
            selector_input = self._input(request)
            full_text = (
                self.input_protocol.render_bootstrap(selector_input)
                + "\n"
                + self.input_protocol.render_step(selector_input)
            )
            features, consumed_tokens, feature_identity = self._extract_features(full_text)
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
            if (
                feature_identity.get("generated_rwkv_text") is not False
                or feature_identity.get("sampling_invoked") is not False
                or feature_identity.get("state_exported") is not False
            ):
                raise NetworkSelectorServiceError(
                    "network Selector extractor generated text or exported transient state"
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
            suffix = request_digest[:24]
            selection = NetworkExactToolSelection(
                selection_id=f"NSEL-{suffix}",
                trace_id=str(request["trace_id"]),
                selected_operation=NETWORK_EXACT_TOOL_LABELS[selected_index],
                logits=logits,
                temperature=self.head.temperature,
                input_digest=str(request["input_digest"]),
                menu_digest=str(request["menu_digest"]),
                selector_checkpoint_id=f"NSCP-{suffix}",
                input_token_count=consumed_tokens,
                model=self.settings.model,
                model_sha256=self.settings.model_sha256,
                head_sha256=self.settings.head_sha256,
                profile_id=self.settings.state_profile_id,
                profile_sha256=self.settings.state_profile_sha256,
                eligible_labels=selector_input.eligible_labels,
            )
            return {
                "schema_version": NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "runtime_identity": self.settings.runtime_identity(),
                "selection": selection.raw_record(),
            }


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
            self._json(
                200,
                {"status": "ok", "runtime_identity": service.settings.runtime_identity()},
            )

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
                self._json(
                    400,
                    {"error": type(exc).__name__, "message": str(exc)[:2000]},
                )
                return
            except Exception as exc:
                self._json(
                    500,
                    {"error": type(exc).__name__, "message": str(exc)[:1000]},
                )
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
    parser.add_argument("--input-protocol", default=G1J_SELECTOR_INTENT_INPUT_PROTOCOL)
    parser.add_argument("--profile-manifest", type=Path)
    parser.add_argument("--profile-manifest-sha256", default="0" * 64)
    parser.add_argument("--profile-id", default="zero")
    parser.add_argument("--profile-sha256", default="0" * 64)
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
            max_tokens=4096,
            wkv_mode="fp16",
            runtime_temp=args.runtime_temp,
            compatibility_sha256="0" * 64,
            **extractor_profile_settings,
        )
    )
    service = NetworkSelectorService(settings, extractor, head)
    extractor.load()
    server = ThreadingHTTPServer((args.host, args.port), _handler(service))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "NetworkSelectorService",
    "NetworkSelectorServiceError",
    "TorchNetworkSelectorHead",
    "load_torch_network_selector_head",
]
