"""Non-authoritative Stage-1 Shadow observation for product Controller runs."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import RunState, RunStatus, utc_now
from rwkv_lh.state_router.local_backend import (
    DEFAULT_ROUTER_MODEL,
    DEFAULT_VLLM_RWKV_PYTHON,
    DEFAULT_VLLM_RWKV_REVISION,
    DEFAULT_VLLM_RWKV_ROOT,
)
from rwkv_lh.state_router.http_client import StateRouterHTTPClient
from rwkv_lh.state_router.model import MultiHeadMLPArtifact
from rwkv_lh.state_router.protocol import (
    HEAD_LABELS,
    STATE_PROFILES,
    ContextMode,
    EvidenceState,
    ExecutionPhase,
    NetworkRecommendation,
    PolicyState,
    RouteFamily,
    RouterInput,
    canonical_digest,
    canonical_json,
)
from rwkv_lh.trace_projection import project_run_activity


ROOT = Path(__file__).resolve().parents[2]
SHADOW_POLICY_SCHEMA_VERSION = "rwkv-lh.state-router-runtime-policy.v1"
SHADOW_RECORD_SCHEMA_VERSION = "rwkv-lh.state-router-shadow-record.v1"
SHADOW_PROTOCOL_VERSION = "rwkv-lh.state-router-shadow.v1"
DEFAULT_SHADOW_HEAD = (
    ROOT
    / "data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827"
    / "state_router_head.json"
)
DEFAULT_SHADOW_PROJECTION = DEFAULT_SHADOW_HEAD.with_name("projection.train_only.pt")
_INFLUENCE = {
    "contract_graph": False,
    "controller_state": False,
    "model_input": False,
    "network_gate": False,
    "state_profile": False,
    "tool_arguments": False,
    "tool_execution": False,
    "tool_menu": False,
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shadow_policy(mode: str = "disabled") -> dict[str, str] | None:
    selected = str(mode or "disabled").strip().casefold()
    if selected not in {"disabled", "shadow"}:
        raise ValueError("State Router runtime mode must be disabled or shadow")
    if selected == "disabled":
        return None
    return {
        "schema_version": SHADOW_POLICY_SCHEMA_VERSION,
        "mode": selected,
    }


def shadow_enabled(state: RunState) -> bool:
    value = state.goal.runtime_policy.get("state_router")
    if value is None:
        return False
    if not isinstance(value, Mapping):
        raise ValueError("State Router runtime policy must be an object")
    schema = str(value.get("schema_version") or "")
    mode = str(value.get("mode") or "").strip().casefold()
    if schema != SHADOW_POLICY_SCHEMA_VERSION:
        raise ValueError("unsupported State Router runtime policy schema")
    if mode not in {"disabled", "shadow"}:
        raise ValueError("unsupported State Router runtime policy mode")
    return mode == "shadow"


def shadow_log_path(state_root: str | Path, run_id: str) -> Path:
    digest = hashlib.sha256(str(run_id).encode("utf-8")).hexdigest()[:24]
    return Path(state_root).expanduser().resolve() / "state_router_shadow" / f"run-{digest}.jsonl"


def read_shadow_records(
    state_root: str | Path,
    run_id: str,
    *,
    after: int = 0,
    limit: int = 300,
) -> dict[str, Any]:
    path = shadow_log_path(state_root, run_id)
    if not path.is_file():
        return {"events": [], "next_offset": max(0, int(after)), "total": 0}
    lines = path.read_text(encoding="utf-8").splitlines()
    start = max(0, int(after))
    selected = lines[start : start + max(1, min(int(limit), 1000))]
    records: list[dict[str, Any]] = []
    for line in selected:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            records.append(dict(value))
    return {
        "events": records,
        "next_offset": start + len(selected),
        "total": len(lines),
    }


def _menu_digest(harness: ActionHarness) -> str:
    return canonical_digest(harness.g1i_tool_definitions())


def _router_input(
    state: RunState,
    invocation_id: str,
    *,
    force_continuation: bool = False,
) -> RouterInput:
    activity = project_run_activity(state)
    fresh = (
        not force_continuation
        and state.status is RunStatus.INITIALIZED
        and not activity["actions"]
    )
    retrieval = state.goal.runtime_policy.get("retrieval")
    retrieval_policy = dict(retrieval) if isinstance(retrieval, Mapping) else {}
    policy_state = (
        PolicyState.NETWORK_DENIED
        if str(retrieval_policy.get("mode") or "offline") == "offline"
        else PolicyState.NETWORK_ALLOWED
    )
    if fresh:
        mode = ContextMode.FRESH
        summary = None
        evidence_state = EvidenceState.NONE
    else:
        mode = ContextMode.CONTINUATION
        ordered = activity["actions"]
        successful = sum(item["status"] == "succeeded" for item in ordered)
        failed = sum(
            item["status"] in {"failed", "interrupted"} for item in ordered
        )
        summary = canonical_json(
            {
                "active_action": state.active_action_id or None,
                "failed_actions": failed,
                "final_output_committed": bool(state.final_output),
                "operations": [item["operation"] for item in ordered[-8:]],
                "run_status": state.status.value,
                "successful_actions": successful,
            }
        )
        if state.status is RunStatus.COMPLETED or state.final_output:
            evidence_state = EvidenceState.COMMITTED
        elif state.active_action_id or successful:
            evidence_state = EvidenceState.PARTIAL
        else:
            evidence_state = EvidenceState.MISSING
    return RouterInput(
        mode=mode,
        summary=summary,
        evidence_state=evidence_state,
        policy_state=policy_state,
        request=state.goal.request,
        trace_id=(
            f"RTR-SHADOW-{state.run_id}-{state.revision}-"
            f"{invocation_id.removeprefix('SHADOW-')}"
        ),
    )


def _action_family(harness: ActionHarness, operation: str) -> RouteFamily:
    try:
        definition = harness.definition(operation)
    except Exception:
        return RouteFamily.ABSTAIN
    if definition.network_access == "public_web":
        return RouteFamily.WEB
    if definition.network_access == "structured_source":
        return RouteFamily.CONNECTOR
    if definition.capability_class.startswith("deterministic."):
        return RouteFamily.DETERMINISTIC
    if definition.capability_class.startswith("local."):
        return RouteFamily.LOCAL
    return RouteFamily.ABSTAIN


def observed_main_behavior(state: RunState, harness: ActionHarness) -> dict[str, Any]:
    ordered = project_run_activity(state)["actions"]
    action_rows: list[dict[str, Any]] = []
    families: set[RouteFamily] = set()
    network_rejections = 0
    for action in ordered:
        operation = str(action.get("operation") or "")
        family = _action_family(harness, operation)
        if family is not RouteFamily.ABSTAIN:
            families.add(family)
        if bool(action.get("network_policy_rejected")):
            network_rejections += 1
        action_rows.append(
            {
                "action_id": str(action.get("action_id") or ""),
                "atom_id": str(action.get("atom_id") or ""),
                "family": family.value,
                "operation": operation,
                "origin": str(action.get("origin") or ""),
                "sequence": int(action.get("sequence", 0) or 0),
                "stage_id": str(action.get("stage_id") or ""),
                "status": str(action.get("status") or ""),
            }
        )
    if len(families) > 1:
        route = RouteFamily.MIXED
    elif families:
        route = sorted(families, key=lambda item: item.value)[0]
    elif state.status is RunStatus.COMPLETED:
        route = RouteFamily.FINAL
    else:
        route = RouteFamily.ABSTAIN
    network_attempted = bool(
        families.intersection({RouteFamily.WEB, RouteFamily.CONNECTOR})
    )
    return {
        "actions": action_rows,
        "network_attempted": network_attempted,
        "network_policy_rejections": network_rejections,
        "network_recommendation": (
            NetworkRecommendation.REQUIRED.value
            if network_attempted
            else NetworkRecommendation.NOT_REQUIRED.value
        ),
        "reference_kind": "observed_main_model_behavior_not_ground_truth",
        "route_family": route.value,
        "run_status": state.status.value,
    }


def _validated_router_output(
    value: Mapping[str, Any],
    *,
    router_input: RouterInput,
    artifact: MultiHeadMLPArtifact,
) -> dict[str, Any]:
    output = dict(value)
    if output.get("schema_version") != "rwkv-lh.state-router-output.v1":
        raise RuntimeError("Shadow Router returned an unsupported output schema")
    if output.get("trace_id") != router_input.trace_id:
        raise RuntimeError("Shadow Router trace ID mismatch")
    if output.get("model_hash") != artifact.model_hash:
        raise RuntimeError("Shadow Router model hash mismatch")
    if output.get("head_hash") != artifact.head_hash:
        raise RuntimeError("Shadow Router head hash mismatch")
    ContextMode(str(output.get("context_mode") or ""))
    ExecutionPhase(str(output.get("execution_phase") or ""))
    RouteFamily(str(output.get("route_family") or ""))
    NetworkRecommendation(str(output.get("network_recommendation") or ""))
    if str(output.get("state_profile") or "") not in STATE_PROFILES:
        raise RuntimeError("Shadow Router returned an unknown State Profile")
    confidence = output.get("confidence")
    if not isinstance(confidence, Mapping) or set(confidence) != set(HEAD_LABELS):
        raise RuntimeError("Shadow Router confidence heads mismatch")
    if any(
        not math.isfinite(float(item)) or not 0.0 <= float(item) <= 1.0
        for item in confidence.values()
    ):
        raise RuntimeError("Shadow Router confidence values are invalid")
    return output


RouterRunner = Callable[[RouterInput], Mapping[str, Any]]


@dataclass(frozen=True)
class ShadowPrediction:
    invocation_id: str
    router_input: RouterInput
    router_output: Mapping[str, Any] | None
    menu_digest_before: str
    error: Mapping[str, str] | None = None


class LocalShadowObserver:
    """Run the selected Router out-of-process and append non-authoritative logs."""

    def __init__(
        self,
        state_root: str | Path,
        *,
        head: str | Path = DEFAULT_SHADOW_HEAD,
        projection: str | Path = DEFAULT_SHADOW_PROJECTION,
        timeout_seconds: float = 120.0,
        router_url: str | None = None,
        runner: RouterRunner | None = None,
    ) -> None:
        self.state_root = Path(state_root).expanduser().resolve()
        self.head_path = Path(head).expanduser().resolve()
        self.projection_path = Path(projection).expanduser().resolve()
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        configured_url = (
            str(router_url).strip()
            if router_url is not None
            else os.environ.get("RWKV_STATE_ROUTER_URL", "").strip()
        )
        self.router_url = configured_url.rstrip("/")
        self._injected_runner = runner
        self._artifact: MultiHeadMLPArtifact | None = None

    def _load_artifact(self) -> MultiHeadMLPArtifact:
        if self._artifact is None:
            artifact = MultiHeadMLPArtifact.load(self.head_path)
            if str(artifact.metadata.get("scheme") or "") != "B":
                raise RuntimeError("Shadow mode requires the selected scheme-B head")
            if _file_sha256(self.projection_path) != str(
                artifact.metadata.get("projection_sha256") or ""
            ):
                raise RuntimeError("Shadow projection checksum does not match head")
            self._artifact = artifact
        return self._artifact

    def _subprocess_runner(self, router_input: RouterInput) -> Mapping[str, Any]:
        command = [
            sys.executable,
            "-m",
            "scripts.run_local_state_router",
            "--head",
            str(self.head_path),
            "--projection",
            str(self.projection_path),
            "--model",
            str(DEFAULT_ROUTER_MODEL),
            "--engine-root",
            str(DEFAULT_VLLM_RWKV_ROOT),
            "--engine-revision",
            DEFAULT_VLLM_RWKV_REVISION,
            "--engine-python",
            str(DEFAULT_VLLM_RWKV_PYTHON),
            "--batch-size",
            "1",
            "--input-jsonl",
            "-",
        ]
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(
                json.dumps(router_input.to_dict(), ensure_ascii=False) + "\n",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            raise TimeoutError(
                f"Shadow Router exceeded {self.timeout_seconds:g}s"
            ) from exc
        if process.returncode != 0:
            detail = "\n".join((stdout + "\n" + stderr).splitlines()[-20:])
            raise RuntimeError(f"Shadow Router process failed: {detail}")
        rows = [line for line in stdout.splitlines() if line.strip()]
        if len(rows) != 1:
            raise RuntimeError("Shadow Router must return exactly one JSONL row")
        value = json.loads(rows[0])
        if not isinstance(value, Mapping):
            raise RuntimeError("Shadow Router output must be a JSON object")
        return dict(value)

    def _http_runner(self, router_input: RouterInput) -> Mapping[str, Any]:
        with StateRouterHTTPClient(
            self.router_url,
            timeout_seconds=self.timeout_seconds,
        ) as client:
            return client.route(router_input)

    def _append(self, run_id: str, record: Mapping[str, Any]) -> None:
        path = shadow_log_path(self.state_root, run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.is_symlink():
            raise RuntimeError("Shadow log path must not be a symlink")
        unhashed = dict(record)
        unhashed["record_digest"] = canonical_digest(unhashed)
        line = json.dumps(
            unhashed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        with path.open("a", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def predict(
        self,
        state: RunState,
        harness: ActionHarness,
        *,
        force_continuation: bool = False,
    ) -> ShadowPrediction:
        invocation_id = f"SHADOW-{uuid4().hex}"
        router_input = _router_input(
            state,
            invocation_id,
            force_continuation=force_continuation,
        )
        menu_digest = _menu_digest(harness)
        started = time.perf_counter()
        output: Mapping[str, Any] | None = None
        error: dict[str, str] | None = None
        try:
            artifact = self._load_artifact()
            runner = self._injected_runner
            if runner is None:
                runner = self._http_runner if self.router_url else self._subprocess_runner
            output = _validated_router_output(
                runner(router_input),
                router_input=router_input,
                artifact=artifact,
            )
        except Exception as exc:
            error = {
                "message": str(exc)[:2000],
                "type": type(exc).__name__,
            }
        record = {
            "schema_version": SHADOW_RECORD_SCHEMA_VERSION,
            "protocol_version": SHADOW_PROTOCOL_VERSION,
            "event_type": "prediction" if error is None else "prediction_error",
            "recorded_at": utc_now(),
            "run_id": state.run_id,
            "invocation_id": invocation_id,
            "revision_before": state.revision,
            "goal_digest": state.goal.digest,
            "shadow_only": True,
            "influence": dict(_INFLUENCE),
            "tool_menu_digest_before": menu_digest,
            "router_input": router_input.to_dict(),
            "latency_seconds": time.perf_counter() - started,
        }
        if output is not None:
            record["router_output"] = dict(output)
            record["artifacts"] = {
                "head_path": str(self.head_path),
                "head_sha256": _file_sha256(self.head_path),
                "projection_path": str(self.projection_path),
                "projection_sha256": _file_sha256(self.projection_path),
            }
        if error is not None:
            record["error"] = error
        try:
            self._append(state.run_id, record)
        except Exception:
            pass
        return ShadowPrediction(
            invocation_id=invocation_id,
            router_input=router_input,
            router_output=output,
            menu_digest_before=menu_digest,
            error=error,
        )

    def outcome(
        self,
        prediction: ShadowPrediction,
        state: RunState,
        harness: ActionHarness,
        *,
        controller_error: BaseException | None = None,
    ) -> None:
        try:
            behavior = observed_main_behavior(state, harness)
            menu_after = _menu_digest(harness)
            output = prediction.router_output
            comparison: dict[str, Any] = {
                "reference_is_ground_truth": False,
                "router_available": output is not None,
                "tool_menu_unchanged": menu_after == prediction.menu_digest_before,
            }
            if output is not None:
                predicted_route = str(output["route_family"])
                predicted_network = str(output["network_recommendation"])
                comparison.update(
                    {
                        "eligible_non_abstain": predicted_route != RouteFamily.ABSTAIN.value,
                        "network_behavior_match": (
                            predicted_network == behavior["network_recommendation"]
                        ),
                        "route_behavior_match": (
                            predicted_route == behavior["route_family"]
                        ),
                    }
                )
            record: dict[str, Any] = {
                "schema_version": SHADOW_RECORD_SCHEMA_VERSION,
                "protocol_version": SHADOW_PROTOCOL_VERSION,
                "event_type": "outcome",
                "recorded_at": utc_now(),
                "run_id": state.run_id,
                "invocation_id": prediction.invocation_id,
                "revision_after": state.revision,
                "shadow_only": True,
                "influence": dict(_INFLUENCE),
                "tool_menu_digest_before": prediction.menu_digest_before,
                "tool_menu_digest_after": menu_after,
                "observed_main_behavior": behavior,
                "comparison": comparison,
            }
            if controller_error is not None:
                record["controller_error"] = {
                    "message": str(controller_error)[:2000],
                    "type": type(controller_error).__name__,
                }
            self._append(state.run_id, record)
        except Exception:
            pass

    def prediction_failure(
        self,
        prediction: ShadowPrediction,
        state: RunState,
    ) -> None:
        """Best-effort record for failures outside the normal prediction path."""
        try:
            self._append(
                state.run_id,
                {
                    "schema_version": SHADOW_RECORD_SCHEMA_VERSION,
                    "protocol_version": SHADOW_PROTOCOL_VERSION,
                    "event_type": "prediction_error",
                    "recorded_at": utc_now(),
                    "run_id": state.run_id,
                    "invocation_id": prediction.invocation_id,
                    "revision_before": state.revision,
                    "goal_digest": state.goal.digest,
                    "shadow_only": True,
                    "influence": dict(_INFLUENCE),
                    "tool_menu_digest_before": prediction.menu_digest_before,
                    "router_input": prediction.router_input.to_dict(),
                    "error": dict(prediction.error or {}),
                },
            )
        except Exception:
            pass


class ShadowController:
    """Transparent run/resume wrapper; observer failures never change results."""

    def __init__(self, controller: Any, observer: LocalShadowObserver) -> None:
        self._controller = controller
        self._observer = observer

    def __getattr__(self, name: str) -> Any:
        return getattr(self._controller, name)

    def _call(self, method: str, run_id: str) -> Any:
        state_before = self._controller.store.load(run_id)
        try:
            prediction = self._observer.predict(
                state_before,
                self._controller.harness,
                force_continuation=method == "resume",
            )
        except Exception as exc:
            invocation_id = f"SHADOW-{uuid4().hex}"
            prediction = ShadowPrediction(
                invocation_id=invocation_id,
                router_input=_router_input(
                    state_before,
                    invocation_id,
                    force_continuation=method == "resume",
                ),
                router_output=None,
                menu_digest_before=_menu_digest(self._controller.harness),
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )
            self._observer.prediction_failure(prediction, state_before)
        try:
            result = getattr(self._controller, method)(run_id)
        except BaseException as exc:
            try:
                state_after = self._controller.store.load(run_id)
            except Exception:
                state_after = state_before
            self._observer.outcome(
                prediction,
                state_after,
                self._controller.harness,
                controller_error=exc,
            )
            raise
        self._observer.outcome(
            prediction,
            result.state,
            self._controller.harness,
        )
        return result

    def run(self, run_id: str) -> Any:
        return self._call("run", run_id)

    def resume(self, run_id: str) -> Any:
        return self._call("resume", run_id)


def wrap_controller_for_shadow(
    controller: Any,
    state: RunState,
    *,
    state_root: str | Path,
    observer: LocalShadowObserver | None = None,
) -> Any:
    if not shadow_enabled(state):
        return controller
    return ShadowController(
        controller,
        observer or LocalShadowObserver(state_root),
    )


__all__ = [
    "DEFAULT_SHADOW_HEAD",
    "DEFAULT_SHADOW_PROJECTION",
    "LocalShadowObserver",
    "SHADOW_POLICY_SCHEMA_VERSION",
    "SHADOW_PROTOCOL_VERSION",
    "SHADOW_RECORD_SCHEMA_VERSION",
    "ShadowController",
    "ShadowPrediction",
    "observed_main_behavior",
    "read_shadow_records",
    "shadow_enabled",
    "shadow_log_path",
    "shadow_policy",
    "wrap_controller_for_shadow",
]
