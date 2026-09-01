"""Versioned facts for the RWKV action spine and optional hybrid supervision.

The runtime stores literal input, model calls, exact tool observations and
artifact revisions.  The default R126 path has no online plan or reviewer.  In
hybrid mode, external plans and reviews are attributed causal facts; they do not
become mutable controller-authored task state or gain Harness execution authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

LEGACY_GOAL_SCHEMA_VERSION = "long-horizon.literal-request.v1"
GOAL_SCHEMA_VERSION = "long-horizon.literal-request.v2"
RUN_SCHEMA_VERSION = "long-horizon.run.v18"
CAUSAL_EVENT_SCHEMA_VERSION = "rwkv-lh.causal-event.v2"

CAUSAL_EVENT_PAYLOAD_SCHEMAS: dict[str, str] = {
    "run_created": "rwkv-lh.run-created.v1",
    "run_started": "rwkv-lh.run-started.v1",
    "run_completed": "rwkv-lh.run-terminal.v1",
    "run_interrupted": "rwkv-lh.run-terminal.v1",
    "run_failed": "rwkv-lh.run-terminal.v1",
    "run_yielded": "rwkv-lh.run-yielded.v1",
    "snapshot_recovered": "rwkv-lh.snapshot-recovered.v1",
    "state_saved": "rwkv-lh.state-saved.v1",
    "action_session_started": "rwkv-lh.action-session-started.v1",
    "action_session_rolled_over": "rwkv-lh.action-session-rollover.v1",
    "selector_state_cache_rebuilt": "rwkv-lh.selector-state-cache-rebuilt.v1",
    "model_call_accepted": "rwkv-lh.model-decision.v1",
    "model_call_rejected": "rwkv-lh.model-decision.v1",
    "tool_selection_accepted": "rwkv-lh.tool-selection.v1",
    "tool_selection_rejected": "rwkv-lh.tool-selection.v1",
    "tool_schema_disclosed": "rwkv-lh.tool-schema-disclosed.v1",
    "exact_tool_selection_staged": "rwkv-lh.exact-tool-selection-staged.v1",
    "exact_tool_selection_committed": "rwkv-lh.exact-tool-selection.v1",
    "exact_tool_selection_consumed": "rwkv-lh.exact-tool-selection-consumed.v1",
    "exact_tool_selection_discarded": "rwkv-lh.exact-tool-selection-discarded.v1",
    "exact_tool_selection_rejected": "rwkv-lh.exact-tool-selection-rejected.v1",
    "protocol_rejection_recorded": "rwkv-lh.protocol-rejection.v1",
    "action_started": "rwkv-lh.action-started.v1",
    "action_finished": "rwkv-lh.action-finished.v1",
    "idempotent_mutation_repeat_boundary": (
        "rwkv-lh.idempotent-mutation-repeat-boundary.v1"
    ),
    "action_observation_appended": "rwkv-lh.model-event-appended.v1",
    "goal_plan_patch_committed": "rwkv-lh.goal-plan-patch-committed.v1",
    "strong_planner_call_failed": "rwkv-lh.strong-planner-call-failed.v1",
    "goal_stage_review_committed": "rwkv-lh.goal-stage-review-committed.v1",
    "strong_stage_checker_call_failed": "rwkv-lh.strong-stage-checker-failed.v1",
    "goal_auditor_session_started": "rwkv-lh.goal-auditor-session-started.v1",
    "goal_audit_recorded": "rwkv-lh.goal-audit-recorded.v1",
    "goal_audit_accepted": "rwkv-lh.goal-audit-accepted.v1",
    "goal_audit_rejected": "rwkv-lh.goal-audit-rejected.v1",
    "goal_final_rejected": "rwkv-lh.goal-final-rejected.v1",
    "goal_action_plan_step_assigned": "rwkv-lh.goal-action-plan-step-assignment.v1",
    "goal_action_plan_step_linked": "rwkv-lh.goal-action-plan-step-link.v1",
    "goal_audit_boundary_opened": "rwkv-lh.goal-audit-boundary.v1",
    "goal_audit_boundary_resolved": "rwkv-lh.goal-audit-boundary-resolution.v1",
    "rwkv_contract_review_projected": "rwkv-lh.rwkv-contract-review-projection.v1",
    "stale_active_action_cleared": "rwkv-lh.action-recovery.v1",
    "idempotent_action_recovered": "rwkv-lh.action-recovery.v1",
    "committed_snapshot_action_recovered": "rwkv-lh.action-recovery.v1",
    "model_transport_failure": "rwkv-lh.model-transport-failure.v1",
    "supervisor_plan_committed": "rwkv-lh.supervisor-plan-committed.v1",
    "supervisor_directive_committed": "rwkv-lh.supervisor-directive-committed.v1",
    "supervisor_stage_committed": "rwkv-lh.supervisor-stage-committed.v1",
    "atom_attempt_started": "rwkv-lh.atom-attempt-started.v1",
    "atom_outcome_committed": "rwkv-lh.atom-outcome-committed.v1",
    "attempt_started": "rwkv-lh.atom-action-attempt.v1",
    "action_returned": "rwkv-lh.atom-action-returned.v1",
    "replan_applied": "rwkv-lh.parallel-replan-applied.v1",
    "contract_graph_patch_committed": "rwkv-lh.contract-graph-patch-committed.v1",
    "contract_graph_review_committed": "rwkv-lh.contract-graph-review-committed.v1",
    "contract_final_presentation_review_committed": (
        "rwkv-lh.contract-final-presentation-review-committed.v1"
    ),
    "contract_graph_batch_committed": "rwkv-lh.contract-graph-batch-committed.v1",
    "contract_correction_signature_committed": "rwkv-lh.contract-correction-signature.v1",
    "contract_correction_duplicate_blocked": "rwkv-lh.contract-correction-duplicate.v1",
    "contract_graph_runtime_failed": "rwkv-lh.contract-graph-runtime-failed.v1",
    "supervisor_review_recorded": "rwkv-lh.supervisor-review-recorded.v1",
    "supervisor_call_failed": "rwkv-lh.supervisor-call-failed.v1",
    "supervisor_call_pending": "rwkv-lh.supervisor-call-pending.v1",
    "supervisor_call_resolved": "rwkv-lh.supervisor-call-resolved.v1",
    "supervisor_configuration_missing": "rwkv-lh.supervisor-configuration-missing.v1",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ActionStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class RunStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    BLOCKED = "blocked"
    FAILED = "failed"


class ModelLaneKind(str, Enum):
    ACTION = "action"
    SELECTOR = "selector"
    AUDIT = "audit"


class ModelCheckpointStatus(str, Enum):
    COMMITTED = "committed"
    CANDIDATE = "candidate"
    ROLLED_BACK = "rolled_back"


class ToolSelectionStatus(str, Enum):
    STAGED = "staged"
    # Source compatibility for callers; new serialized records always say staged.
    COMMITTED = "staged"
    CONSUMED = "consumed"
    DISCARDED = "discarded"


@dataclass(frozen=True)
class GoalState:
    """Literal immutable run input; it is never produced or parsed by a model."""

    goal_id: str
    request: str
    constraints: tuple[str, ...]
    workspace_root: str
    created_at: str
    digest: str
    schema_version: str = GOAL_SCHEMA_VERSION
    runtime_policy_json: str = "{}"

    @property
    def runtime_policy(self) -> dict[str, Any]:
        value = json.loads(self.runtime_policy_json)
        return dict(value) if isinstance(value, Mapping) else {}

    @classmethod
    def create(
        cls,
        *,
        request: str,
        constraints: list[str] | tuple[str, ...],
        workspace_root: str | Path,
        goal_id: str = "G1",
        runtime_policy: Mapping[str, Any] | None = None,
    ) -> "GoalState":
        request_text = str(request or "").strip()
        if not request_text:
            raise ValueError("request must be non-empty")
        constraint_values = tuple(
            dict.fromkeys(
                str(item).strip() for item in constraints if str(item).strip()
            )
        )
        immutable = {
            "schema_version": GOAL_SCHEMA_VERSION,
            "goal_id": str(goal_id or "G1").strip(),
            "request": request_text,
            "constraints": list(constraint_values),
            "workspace_root": str(Path(workspace_root).expanduser().resolve()),
            "created_at": utc_now(),
            "runtime_policy": dict(runtime_policy or {}),
        }
        return cls(
            schema_version=immutable["schema_version"],
            goal_id=immutable["goal_id"],
            request=immutable["request"],
            constraints=constraint_values,
            workspace_root=immutable["workspace_root"],
            created_at=immutable["created_at"],
            digest=_canonical_digest(immutable),
            runtime_policy_json=json.dumps(
                immutable["runtime_policy"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def immutable_payload(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "goal_id": self.goal_id,
            "request": self.request,
            "constraints": list(self.constraints),
            "workspace_root": self.workspace_root,
            "created_at": self.created_at,
        }
        if self.schema_version != LEGACY_GOAL_SCHEMA_VERSION:
            payload["runtime_policy"] = dict(self.runtime_policy)
        return payload

    def verify_digest(self) -> bool:
        return self.digest == _canonical_digest(self.immutable_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.immutable_payload(), "digest": self.digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalState":
        literal = cls(
            schema_version=str(value.get("schema_version") or ""),
            goal_id=str(value.get("goal_id") or "G1"),
            request=str(value.get("request") or ""),
            constraints=tuple(str(item) for item in value.get("constraints") or []),
            workspace_root=str(value.get("workspace_root") or ""),
            created_at=str(value.get("created_at") or ""),
            digest=str(value.get("digest") or ""),
            runtime_policy_json=json.dumps(
                dict(value.get("runtime_policy") or {}),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        if literal.schema_version not in {
            LEGACY_GOAL_SCHEMA_VERSION,
            GOAL_SCHEMA_VERSION,
        }:
            raise ValueError(f"unsupported literal request schema: {literal.schema_version}")
        if not literal.request or not literal.verify_digest():
            raise ValueError("literal request digest mismatch")
        return literal


@dataclass
class ValidationSpec:
    """Harness-internal observable contract; never shown as a completion goal."""

    kind: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: bool = True

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationSpec":
        parameters = value.get("parameters")
        if not isinstance(parameters, Mapping):
            raise ValueError("validation parameters must be an object")
        return cls(
            kind=str(value.get("kind") or ""),
            parameters=dict(parameters),
            required=bool(value.get("required", True)),
        )


@dataclass
class TaskAction:
    """Exact executable operation selected by RWKV.

    The historical name remains only at the Harness boundary.  It is an action
    value, not an online Task, plan node, or completion claim.
    """

    action_type: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "TaskAction":
        if not isinstance(value, Mapping) or not isinstance(value.get("arguments"), Mapping):
            raise ValueError("action must contain an arguments object")
        return cls(
            action_type=str(value.get("action_type") or "").strip(),
            arguments=dict(value["arguments"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"action_type": self.action_type, "arguments": dict(self.arguments)}


def action_fingerprint(action: TaskAction) -> str:
    return _canonical_digest(action.to_dict())


@dataclass(frozen=True)
class ModelEvent:
    event_type: str
    event_id: str
    scope_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    content_refs: tuple[str, ...] = ()
    complete: bool = True
    continuation: dict[str, Any] | None = None
    event_version: str = "rwkv-lh.event.v2"

    def __post_init__(self) -> None:
        if not self.event_type.strip() or not self.event_id.strip():
            raise ValueError("model event requires event_type and event_id")
        if not self.complete and not isinstance(self.continuation, Mapping):
            raise ValueError("incomplete model event requires continuation metadata")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "event_id": self.event_id,
            "scope_id": self.scope_id,
            "payload": dict(self.payload),
            "content_refs": list(self.content_refs),
            "complete": self.complete,
        }
        if self.continuation is not None:
            value["continuation"] = dict(self.continuation)
        return value

    def to_model_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "event_type": self.event_type,
            "payload": dict(self.payload),
            "content_refs": list(self.content_refs),
            "complete": self.complete,
        }
        if self.continuation is not None:
            value["continuation"] = dict(self.continuation)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelEvent":
        continuation = value.get("continuation")
        return cls(
            event_type=str(value.get("event_type") or ""),
            event_version=str(value.get("event_version") or "rwkv-lh.event.v2"),
            event_id=str(value.get("event_id") or ""),
            scope_id=str(value.get("scope_id") or ""),
            payload=dict(value.get("payload") or {}),
            content_refs=tuple(str(item) for item in value.get("content_refs") or []),
            complete=bool(value.get("complete", True)),
            continuation=dict(continuation) if isinstance(continuation, Mapping) else None,
        )


@dataclass
class ModelCheckpoint:
    checkpoint_id: str
    lane_id: str
    lane_kind: ModelLaneKind
    parent_checkpoint_id: str | None
    model: str
    transport: str
    transcript: str
    transcript_digest: str
    token_count: int
    event_ids: list[str] = field(default_factory=list)
    native_state_ref: str | None = None
    native_state_digest: str | None = None
    native_state_export: dict[str, Any] | None = None
    native_state_metadata: dict[str, Any] | None = None
    state_profile_id: str = ""
    state_profile_sha256: str = ""
    status: ModelCheckpointStatus = ModelCheckpointStatus.COMMITTED
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["lane_kind"] = self.lane_kind.value
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelCheckpoint":
        return cls(
            checkpoint_id=str(value.get("checkpoint_id") or ""),
            lane_id=str(value.get("lane_id") or ""),
            lane_kind=ModelLaneKind(str(value.get("lane_kind") or "")),
            parent_checkpoint_id=(
                str(value["parent_checkpoint_id"])
                if value.get("parent_checkpoint_id") is not None
                else None
            ),
            model=str(value.get("model") or ""),
            transport=str(value.get("transport") or "prompt_replay"),
            transcript=str(value.get("transcript") or ""),
            transcript_digest=str(value.get("transcript_digest") or ""),
            token_count=max(0, int(value.get("token_count", 0) or 0)),
            event_ids=[str(item) for item in value.get("event_ids") or []],
            native_state_ref=(
                str(value["native_state_ref"])
                if value.get("native_state_ref") is not None
                else None
            ),
            native_state_digest=(
                str(value["native_state_digest"])
                if value.get("native_state_digest") is not None
                else None
            ),
            native_state_export=(
                dict(value["native_state_export"])
                if isinstance(value.get("native_state_export"), Mapping)
                else None
            ),
            native_state_metadata=(
                dict(value["native_state_metadata"])
                if isinstance(value.get("native_state_metadata"), Mapping)
                else None
            ),
            state_profile_id=str(value.get("state_profile_id") or ""),
            state_profile_sha256=str(value.get("state_profile_sha256") or ""),
            status=ModelCheckpointStatus(
                str(value.get("status") or ModelCheckpointStatus.COMMITTED.value)
            ),
            created_at=str(value.get("created_at") or utc_now()),
        )


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    request_id: str
    lane_id: str
    input_checkpoint_id: str
    input_digest: str
    visible_event_ids: tuple[str, ...]
    raw_output: str
    command_digest: str
    output_checkpoint_id: str
    output_digest: str
    sampling: dict[str, Any]
    model: str
    transport: str
    accepted: bool
    error: str = ""
    tool_selection_id: str = ""
    selected_operation: str = ""
    atom_execution_contract_digest: str = ""
    tool_selection_binding_kind: str = ""
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["visible_event_ids"] = list(self.visible_event_ids)
        # Keep historical decision projections byte-for-byte stable.  The exact
        # Selector binding is a new, all-or-none extension used by independent
        # Selector→Executor runs; legacy decisions have no such binding and must
        # retain their original serialized shape so persisted snapshot digests
        # remain recoverable without rewriting history.
        if not (
            self.tool_selection_id
            or self.selected_operation
            or self.atom_execution_contract_digest
            or self.tool_selection_binding_kind
        ):
            value.pop("tool_selection_id")
            value.pop("selected_operation")
            value.pop("atom_execution_contract_digest")
            value.pop("tool_selection_binding_kind")
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DecisionRecord":
        return cls(
            decision_id=str(value.get("decision_id") or ""),
            request_id=str(value.get("request_id") or ""),
            lane_id=str(value.get("lane_id") or ""),
            input_checkpoint_id=str(value.get("input_checkpoint_id") or ""),
            input_digest=str(value.get("input_digest") or ""),
            visible_event_ids=tuple(str(item) for item in value.get("visible_event_ids") or []),
            raw_output=str(value.get("raw_output") or ""),
            command_digest=str(value.get("command_digest") or ""),
            output_checkpoint_id=str(value.get("output_checkpoint_id") or ""),
            output_digest=str(value.get("output_digest") or ""),
            sampling=dict(value.get("sampling") or {}),
            model=str(value.get("model") or ""),
            transport=str(value.get("transport") or "prompt_replay"),
            accepted=bool(value.get("accepted", False)),
            error=str(value.get("error") or ""),
            tool_selection_id=str(value.get("tool_selection_id") or ""),
            selected_operation=str(value.get("selected_operation") or ""),
            atom_execution_contract_digest=str(
                value.get("atom_execution_contract_digest") or ""
            ),
            tool_selection_binding_kind=str(
                value.get("tool_selection_binding_kind") or ""
            ),
            created_at=str(value.get("created_at") or utc_now()),
        )


@dataclass(frozen=True)
class ToolSelectionRecord:
    """Non-authoritative Selector→Executor handoff with immutable bindings."""

    selection_id: str
    status: ToolSelectionStatus
    selected_operation: str
    selector_checkpoint_id: str
    selector_state_ref: str
    selector_state_digest: str
    selector_parent_state_digest: str
    executor_parent_checkpoint_id: str
    executor_parent_digest: str
    input_projection_digest: str
    menu_digest: str
    tool_definition_digest: str
    selector_model: str
    selector_model_sha256: str
    selector_head_sha256: str
    selector_profile_id: str
    selector_profile_sha256: str
    executor_model: str
    executor_model_sha256: str
    executor_profile_id: str
    executor_profile_sha256: str
    raw_selection: dict[str, Any]
    atom_execution_contract_digest: str = ""
    authorizes_execution: bool = False
    consumed_decision_id: str = ""
    created_at: str = field(default_factory=utc_now)
    consumed_at: str = ""
    discarded_at: str = ""
    discard_reason: str = ""

    def __post_init__(self) -> None:
        required = (
            self.selection_id,
            self.selected_operation,
            self.selector_checkpoint_id,
            self.selector_state_ref,
            self.executor_parent_checkpoint_id,
            self.selector_model,
            self.selector_profile_id,
            self.executor_model,
            self.executor_profile_id,
        )
        if any(not str(value).strip() for value in required):
            raise ValueError("tool selection identity fields must be non-empty")
        digests = {
            "selector_state_digest": self.selector_state_digest,
            "executor_parent_digest": self.executor_parent_digest,
            "input_projection_digest": self.input_projection_digest,
            "menu_digest": self.menu_digest,
            "tool_definition_digest": self.tool_definition_digest,
            "selector_model_sha256": self.selector_model_sha256,
            "selector_head_sha256": self.selector_head_sha256,
            "selector_profile_sha256": self.selector_profile_sha256,
            "executor_model_sha256": self.executor_model_sha256,
            "executor_profile_sha256": self.executor_profile_sha256,
        }
        if any(
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in digests.values()
        ):
            raise ValueError("tool selection digest fields must be lowercase SHA-256")
        parent_digest = self.selector_parent_state_digest
        if parent_digest and (
            len(parent_digest) != 64
            or any(character not in "0123456789abcdef" for character in parent_digest)
        ):
            raise ValueError(
                "selector_parent_state_digest must be empty or lowercase SHA-256"
            )
        contract_digest = self.atom_execution_contract_digest
        if contract_digest and (
            len(contract_digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in contract_digest
            )
        ):
            raise ValueError(
                "atom_execution_contract_digest must be empty or lowercase SHA-256"
            )
        if not isinstance(self.raw_selection, Mapping):
            raise TypeError("raw_selection must be an object")
        if self.authorizes_execution is not False:
            raise ValueError("tool selection handoff cannot authorize execution")
        bindings = {
            "selection_id": self.selection_id,
            "selected_operation": self.selected_operation,
            "selector_checkpoint_id": self.selector_checkpoint_id,
            "selector_state_ref": self.selector_state_ref,
            "selector_state_digest": self.selector_state_digest,
            "selector_parent_state_digest": self.selector_parent_state_digest,
            "input_digest": self.input_projection_digest,
            "menu_digest": self.menu_digest,
            "model": self.selector_model,
            "model_sha256": self.selector_model_sha256,
            "head_sha256": self.selector_head_sha256,
            "profile_id": self.selector_profile_id,
            "profile_sha256": self.selector_profile_sha256,
        }
        if any(self.raw_selection.get(key) != value for key, value in bindings.items()):
            raise ValueError("raw Selector output differs from handoff identity")
        if self.status is ToolSelectionStatus.STAGED:
            if (
                self.consumed_decision_id
                or self.consumed_at
                or self.discarded_at
                or self.discard_reason
            ):
                raise ValueError("staged selection cannot carry terminal fields")
        elif self.status is ToolSelectionStatus.CONSUMED:
            if (
                not self.consumed_decision_id
                or not self.consumed_at
                or self.discarded_at
                or self.discard_reason
            ):
                raise ValueError(
                    "consumed selection requires only decision identity and timestamp"
                )
        elif (
            not self.discarded_at
            or not self.discard_reason
            or self.consumed_decision_id
            or self.consumed_at
        ):
            raise ValueError(
                "discarded selection requires only discard reason and timestamp"
            )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ToolSelectionRecord":
        return cls(
            selection_id=str(value.get("selection_id") or ""),
            status=ToolSelectionStatus(
                "staged"
                if str(value.get("status") or "") == "committed"
                else str(value.get("status") or "")
            ),
            selected_operation=str(value.get("selected_operation") or ""),
            selector_checkpoint_id=str(value.get("selector_checkpoint_id") or ""),
            selector_state_ref=str(value.get("selector_state_ref") or ""),
            selector_state_digest=str(value.get("selector_state_digest") or ""),
            selector_parent_state_digest=str(
                value.get("selector_parent_state_digest") or ""
            ),
            executor_parent_checkpoint_id=str(
                value.get("executor_parent_checkpoint_id") or ""
            ),
            executor_parent_digest=str(value.get("executor_parent_digest") or ""),
            input_projection_digest=str(
                value.get("input_projection_digest") or ""
            ),
            menu_digest=str(value.get("menu_digest") or ""),
            tool_definition_digest=str(value.get("tool_definition_digest") or ""),
            selector_model=str(value.get("selector_model") or ""),
            selector_model_sha256=str(value.get("selector_model_sha256") or ""),
            selector_head_sha256=str(value.get("selector_head_sha256") or ""),
            selector_profile_id=str(value.get("selector_profile_id") or ""),
            selector_profile_sha256=str(
                value.get("selector_profile_sha256") or ""
            ),
            executor_model=str(value.get("executor_model") or ""),
            executor_model_sha256=str(value.get("executor_model_sha256") or ""),
            executor_profile_id=str(value.get("executor_profile_id") or ""),
            executor_profile_sha256=str(
                value.get("executor_profile_sha256") or ""
            ),
            raw_selection=dict(value.get("raw_selection") or {}),
            atom_execution_contract_digest=str(
                value.get("atom_execution_contract_digest") or ""
            ),
            authorizes_execution=bool(value.get("authorizes_execution", False)),
            consumed_decision_id=str(value.get("consumed_decision_id") or ""),
            created_at=str(value.get("created_at") or utc_now()),
            consumed_at=str(value.get("consumed_at") or ""),
            discarded_at=str(value.get("discarded_at") or ""),
            discard_reason=str(value.get("discard_reason") or ""),
        )


@dataclass(frozen=True)
class ModelRolloverRecord:
    rollover_id: str
    lane_id: str
    source_checkpoint_id: str
    source_digest: str
    source_token_count: int
    output_checkpoint_id: str
    output_digest: str
    output_token_count: int
    retained_event_ids: tuple[str, ...]
    archived_event_ids: tuple[str, ...]
    input_limit: int
    semantic_request_count: int = 0
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["retained_event_ids"] = list(self.retained_event_ids)
        value["archived_event_ids"] = list(self.archived_event_ids)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelRolloverRecord":
        return cls(
            rollover_id=str(value.get("rollover_id") or ""),
            lane_id=str(value.get("lane_id") or ""),
            source_checkpoint_id=str(value.get("source_checkpoint_id") or ""),
            source_digest=str(value.get("source_digest") or ""),
            source_token_count=int(value.get("source_token_count", 0) or 0),
            output_checkpoint_id=str(value.get("output_checkpoint_id") or ""),
            output_digest=str(value.get("output_digest") or ""),
            output_token_count=int(value.get("output_token_count", 0) or 0),
            retained_event_ids=tuple(str(item) for item in value.get("retained_event_ids") or []),
            archived_event_ids=tuple(str(item) for item in value.get("archived_event_ids") or []),
            input_limit=int(value.get("input_limit", 1) or 1),
            semantic_request_count=int(value.get("semantic_request_count", 0) or 0),
            created_at=str(value.get("created_at") or utc_now()),
        )


@dataclass
class ActionRecord:
    action_id: str
    sequence: int
    status: ActionStatus
    action_type: str
    arguments: dict[str, Any]
    wire_arguments: dict[str, Any]
    action_fingerprint: str
    idempotency_key: str
    decision_id: str
    request_id: str
    started_at: str
    ended_at: str | None = None
    result: dict[str, Any] | None = None
    artifact_refs: list[str] = field(default_factory=list)
    workspace_digest_before: str = ""
    workspace_digest_after: str = ""
    failure_key: str = ""
    observation_fingerprint: str = ""
    error: dict[str, Any] | None = None
    outcome_type: str = "pending"
    atom_execution_contract_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActionRecord":
        return cls(
            action_id=str(value.get("action_id") or ""),
            sequence=max(1, int(value.get("sequence", 1) or 1)),
            status=ActionStatus(str(value.get("status") or ActionStatus.RUNNING.value)),
            action_type=str(value.get("action_type") or ""),
            arguments=dict(value.get("arguments") or {}),
            wire_arguments=dict(value.get("wire_arguments") or {}),
            action_fingerprint=str(value.get("action_fingerprint") or ""),
            idempotency_key=str(value.get("idempotency_key") or ""),
            decision_id=str(value.get("decision_id") or ""),
            request_id=str(value.get("request_id") or ""),
            started_at=str(value.get("started_at") or ""),
            ended_at=str(value["ended_at"]) if value.get("ended_at") else None,
            result=dict(value["result"]) if isinstance(value.get("result"), Mapping) else None,
            artifact_refs=[str(item) for item in value.get("artifact_refs") or []],
            workspace_digest_before=str(value.get("workspace_digest_before") or ""),
            workspace_digest_after=str(value.get("workspace_digest_after") or ""),
            failure_key=str(value.get("failure_key") or ""),
            observation_fingerprint=str(value.get("observation_fingerprint") or ""),
            error=dict(value["error"]) if isinstance(value.get("error"), Mapping) else None,
            outcome_type=str(value.get("outcome_type") or "pending"),
            atom_execution_contract_digest=str(
                value.get("atom_execution_contract_digest") or ""
            ),
        )


@dataclass
class ArtifactRecord:
    artifact_id: str
    action_id: str
    path: str
    sha256: str
    media_type: str = "application/octet-stream"
    size_bytes: int = 0
    summary: str = ""
    observed_at: str = field(default_factory=utc_now)


@dataclass
class ArtifactRevision:
    revision_id: str
    target: str
    artifact_id: str
    action_id: str
    sha256: str
    outcome_type: str
    supersedes_revision_ids: list[str] = field(default_factory=list)
    observed_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class CausalEventDraft:
    """One explicit, typed event submitted by a runtime stage."""

    event_type: str
    payload_schema: str
    payload: dict[str, Any]
    subject_id: str
    cause_id: str | None = None

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        subject_id: str,
        cause_id: str | None = None,
    ) -> "CausalEventDraft":
        name = str(event_type or "")
        payload_schema = CAUSAL_EVENT_PAYLOAD_SCHEMAS.get(name)
        if payload_schema is None:
            raise ValueError(f"unregistered causal event type: {name}")
        subject = str(subject_id or "").strip()
        if not subject:
            raise ValueError("causal event subject_id must be non-empty")
        return cls(
            event_type=name,
            payload_schema=payload_schema,
            payload=dict(payload),
            subject_id=subject,
            cause_id=str(cause_id) if cause_id else None,
        )


@dataclass(frozen=True)
class CausalEvent:
    """The single append-only fact interface shared by every runtime stage."""

    event_id: str
    run_id: str
    sequence: int
    parent_id: str | None
    cause_id: str | None
    subject_id: str
    event_type: str
    payload_schema: str
    payload: dict[str, Any]
    digest: str
    created_at: str
    schema_version: str = CAUSAL_EVENT_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        event_id: str,
        run_id: str,
        sequence: int,
        parent_id: str | None,
        draft: CausalEventDraft,
        created_at: str | None = None,
    ) -> "CausalEvent":
        timestamp = str(created_at or utc_now())
        immutable = {
            "schema_version": CAUSAL_EVENT_SCHEMA_VERSION,
            "event_id": str(event_id),
            "run_id": str(run_id),
            "sequence": int(sequence),
            "parent_id": str(parent_id) if parent_id is not None else None,
            "cause_id": draft.cause_id,
            "subject_id": draft.subject_id,
            "event_type": draft.event_type,
            "payload_schema": draft.payload_schema,
            "payload": dict(draft.payload),
            "created_at": timestamp,
        }
        return cls(**immutable, digest=_canonical_digest(immutable))

    def immutable_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "parent_id": self.parent_id,
            "cause_id": self.cause_id,
            "subject_id": self.subject_id,
            "event_type": self.event_type,
            "payload_schema": self.payload_schema,
            "payload": dict(self.payload),
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.immutable_payload(), "digest": self.digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CausalEvent":
        record = cls(
            schema_version=str(value.get("schema_version") or ""),
            event_id=str(value.get("event_id") or ""),
            run_id=str(value.get("run_id") or ""),
            sequence=int(value.get("sequence", 0) or 0),
            parent_id=(str(value["parent_id"]) if value.get("parent_id") is not None else None),
            cause_id=(str(value["cause_id"]) if value.get("cause_id") is not None else None),
            subject_id=str(value.get("subject_id") or ""),
            event_type=str(value.get("event_type") or ""),
            payload_schema=str(value.get("payload_schema") or ""),
            payload=dict(value.get("payload") or {}),
            digest=str(value.get("digest") or ""),
            created_at=str(value.get("created_at") or ""),
        )
        expected_schema = CAUSAL_EVENT_PAYLOAD_SCHEMAS.get(record.event_type)
        if record.schema_version != CAUSAL_EVENT_SCHEMA_VERSION:
            raise ValueError("unsupported causal event schema")
        if expected_schema is None or record.payload_schema != expected_schema:
            raise ValueError("causal event payload schema mismatch")
        if not record.event_id or not record.run_id or not record.subject_id:
            raise ValueError("causal event identity is incomplete")
        if record.digest != _canonical_digest(record.immutable_payload()):
            raise ValueError("causal event digest mismatch")
        return record


@dataclass
class TempDecision:
    request_id: str
    task_id: str
    request_type: str
    temperature: float
    policy_reason: str
    attempt: int
    started_at: str
    top_p: float = 1.0
    top_k: int = 0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    penalty_decay: float = 0.996
    max_tokens: int = 0
    backend_profile: str = "vllm-rwkv-native"
    seed_supported: bool = False
    ended_at: str | None = None
    outcome: str = "running"
    result_summary: str = ""
    error: str | None = None


@dataclass(frozen=True)
class ChunkDescriptor:
    """Tokenizer cursor utility used by read_file/read_json observations."""

    chunk_id: str
    source_ref: str
    source_sha256: str
    media_type: str
    byte_start: int
    byte_end: int
    core_start: int
    core_end: int
    overlap_before: int
    overlap_after: int
    chunk_sha256: str
    split_strategy_version: str
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None
    complete_source: bool = False
    token_start: int = 0
    token_end: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ChunkDescriptor":
        return cls(**dict(value))


@dataclass
class RunState:
    run_id: str
    goal: GoalState
    revision: int = 0
    status: RunStatus = RunStatus.INITIALIZED
    actions: dict[str, ActionRecord] = field(default_factory=dict)
    active_action_id: str | None = None
    next_action_sequence: int = 1
    artifacts: dict[str, ArtifactRecord] = field(default_factory=dict)
    artifact_revisions: dict[str, list[ArtifactRevision]] = field(default_factory=dict)
    causal_records: dict[str, CausalEvent] = field(default_factory=dict)
    causal_order: list[str] = field(default_factory=list)
    model_states: dict[str, ModelCheckpoint] = field(default_factory=dict)
    action_lane_checkpoint_id: str = ""
    lane_heads: dict[str, str] = field(default_factory=dict)
    model_events: dict[str, ModelEvent] = field(default_factory=dict)
    decisions: dict[str, DecisionRecord] = field(default_factory=dict)
    tool_selections: dict[str, ToolSelectionRecord] = field(default_factory=dict)
    pending_selection_id: str = ""
    rollovers: dict[str, ModelRolloverRecord] = field(default_factory=dict)
    temp_decisions: list[TempDecision] = field(default_factory=list)
    failure_budgets: dict[str, int] = field(default_factory=dict)
    observation_counts: dict[str, int] = field(default_factory=dict)
    protocol_rejections: int = 0
    final_output: str = ""
    final_decision_id: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: str = RUN_SCHEMA_VERSION

    @property
    def atom_execution_contract_digest(self) -> str:
        execution = self.goal.runtime_policy.get("atom_execution")
        if not isinstance(execution, Mapping):
            return ""
        contract = execution.get("contract")
        if not isinstance(contract, Mapping):
            return ""
        return str(contract.get("contract_digest") or "")

    def _validate_atom_execution_contract_digest(self, value: str) -> None:
        if str(value or "") != self.atom_execution_contract_digest:
            raise ValueError(
                "runtime record atom execution contract differs from its Goal"
            )

    def projection_payload(self) -> dict[str, Any]:
        payload = {
            "status": self.status.value,
            "actions": {key: value.to_dict() for key, value in self.actions.items()},
            "active_action_id": self.active_action_id,
            "next_action_sequence": self.next_action_sequence,
            "artifacts": {key: asdict(value) for key, value in self.artifacts.items()},
            "artifact_revisions": {
                key: [asdict(item) for item in revisions]
                for key, revisions in self.artifact_revisions.items()
            },
            "model_events": {key: value.to_dict() for key, value in self.model_events.items()},
            "decisions": {key: value.to_dict() for key, value in self.decisions.items()},
            "rollovers": {key: value.to_dict() for key, value in self.rollovers.items()},
            "temp_decisions": [asdict(value) for value in self.temp_decisions],
            "failure_budgets": dict(self.failure_budgets),
            "observation_counts": dict(self.observation_counts),
            "protocol_rejections": self.protocol_rejections,
            "final_output": self.final_output,
            "final_decision_id": self.final_decision_id,
            "errors": list(self.errors),
        }
        if self.tool_selections or self.pending_selection_id:
            payload["tool_selections"] = {
                key: value.to_dict() for key, value in self.tool_selections.items()
            }
            payload["pending_selection_id"] = self.pending_selection_id
        return payload

    def set_lane_head(self, role: str, checkpoint_id: str) -> None:
        normalized_role = str(role).strip().casefold()
        if normalized_role not in {"selector", "executor", "auditor"}:
            raise ValueError(f"unsupported model lane role: {role!r}")
        if checkpoint_id not in self.model_states:
            raise ValueError("model lane head must reference a stored checkpoint")
        self.lane_heads[normalized_role] = checkpoint_id
        if normalized_role == "executor":
            self.action_lane_checkpoint_id = checkpoint_id

    def lane_head(self, role: str) -> str:
        normalized_role = str(role).strip().casefold()
        checkpoint_id = self.lane_heads.get(normalized_role, "")
        if not checkpoint_id and normalized_role == "executor":
            checkpoint_id = self.action_lane_checkpoint_id
        return checkpoint_id

    def _consume_tool_selection(self, selection: ToolSelectionRecord) -> None:
        if selection.status is not ToolSelectionStatus.CONSUMED:
            raise ValueError("consumed tool selection must have consumed status")
        self._validate_atom_execution_contract_digest(
            selection.atom_execution_contract_digest
        )
        committed = self.tool_selections.get(selection.selection_id)
        if committed is None or committed.status is not ToolSelectionStatus.STAGED:
            raise ValueError("tool selection consumption has no staged parent")
        if self.pending_selection_id != selection.selection_id:
            raise ValueError("tool selection consumption is not the pending handoff")
        immutable_fields = (
            "selection_id",
            "selected_operation",
            "selector_checkpoint_id",
            "selector_state_ref",
            "selector_state_digest",
            "selector_parent_state_digest",
            "executor_parent_checkpoint_id",
            "executor_parent_digest",
            "input_projection_digest",
            "menu_digest",
            "tool_definition_digest",
            "selector_model",
            "selector_model_sha256",
            "selector_head_sha256",
            "selector_profile_id",
            "selector_profile_sha256",
            "executor_model",
            "executor_model_sha256",
            "executor_profile_id",
            "executor_profile_sha256",
            "atom_execution_contract_digest",
            "authorizes_execution",
            "raw_selection",
            "created_at",
        )
        if any(
            getattr(committed, name) != getattr(selection, name)
            for name in immutable_fields
        ):
            raise ValueError("tool selection consumption changed handoff identity")
        self.tool_selections[selection.selection_id] = selection
        self.pending_selection_id = ""

    def _discard_tool_selection(self, selection: ToolSelectionRecord) -> None:
        if selection.status is not ToolSelectionStatus.DISCARDED:
            raise ValueError("discarded tool selection must have discarded status")
        staged = self.tool_selections.get(selection.selection_id)
        if staged is None or staged.status is not ToolSelectionStatus.STAGED:
            raise ValueError("tool selection discard has no staged parent")
        if self.pending_selection_id != selection.selection_id:
            raise ValueError("tool selection discard is not the pending handoff")
        immutable_fields = (
            "selection_id",
            "selected_operation",
            "selector_checkpoint_id",
            "selector_state_ref",
            "selector_state_digest",
            "selector_parent_state_digest",
            "executor_parent_checkpoint_id",
            "executor_parent_digest",
            "input_projection_digest",
            "menu_digest",
            "tool_definition_digest",
            "selector_model",
            "selector_model_sha256",
            "selector_head_sha256",
            "selector_profile_id",
            "selector_profile_sha256",
            "executor_model",
            "executor_model_sha256",
            "executor_profile_id",
            "executor_profile_sha256",
            "atom_execution_contract_digest",
            "authorizes_execution",
            "raw_selection",
            "created_at",
        )
        if any(
            getattr(staged, name) != getattr(selection, name)
            for name in immutable_fields
        ):
            raise ValueError("tool selection discard changed handoff identity")
        self.tool_selections[selection.selection_id] = selection
        self.pending_selection_id = ""

    @property
    def projection_digest(self) -> str:
        return _canonical_digest(self.projection_payload())

    def rebuild_projection(self) -> None:
        """Fold the immutable causal chain into disposable runtime projections."""

        self.status = RunStatus.INITIALIZED
        self.actions = {}
        self.active_action_id = None
        self.next_action_sequence = 1
        self.artifacts = {}
        self.artifact_revisions = {}
        self.model_events = {}
        self.decisions = {}
        self.tool_selections = {}
        self.pending_selection_id = ""
        self.rollovers = {}
        self.temp_decisions = []
        self.failure_budgets = {}
        self.observation_counts = {}
        self.protocol_rejections = 0
        self.final_output = ""
        self.final_decision_id = ""
        self.errors = []

        previous_id: str | None = None
        seen: set[str] = set()
        for expected_sequence, event_id in enumerate(self.causal_order, start=1):
            event = self.causal_records.get(event_id)
            if event is None:
                raise ValueError(f"causal order references missing event: {event_id}")
            if event.event_id != event_id or event.run_id != self.run_id:
                raise ValueError("causal event identity mismatch")
            if event.sequence != expected_sequence or event.parent_id != previous_id:
                raise ValueError("causal event sequence or parent mismatch")
            if event.cause_id is not None and event.cause_id not in seen:
                raise ValueError("causal event cause must reference an earlier event")
            previous_id = event_id
            seen.add(event_id)
            payload = event.payload

            if event.event_type == "run_started":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.RUNNING
            elif event.event_type == "run_completed":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.COMPLETED
                self.final_output = str(payload.get("final_output") or "")
                self.final_decision_id = str(payload.get("decision_id") or "")
            elif event.event_type == "run_interrupted":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.INTERRUPTED
                self.final_output = str(payload.get("final_output") or "")
                self.final_decision_id = str(payload.get("decision_id") or "")
            elif event.event_type == "run_failed":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.FAILED
                self.final_output = str(payload.get("final_output") or "")
                self.final_decision_id = str(payload.get("decision_id") or "")
            elif event.event_type == "run_yielded":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.RUNNING
                self.final_output = ""
                self.final_decision_id = ""
            elif event.event_type == "action_started":
                action_value = payload.get("action")
                if not isinstance(action_value, Mapping):
                    raise ValueError("action_started requires a complete action")
                action = ActionRecord.from_dict(action_value)
                if event.subject_id != action.action_id:
                    raise ValueError("action_started subject mismatch")
                if action.status != ActionStatus.RUNNING:
                    raise ValueError("action_started must carry running status")
                if action.action_id in self.actions:
                    raise ValueError("action id was started more than once")
                if action.sequence != self.next_action_sequence:
                    raise ValueError("action sequence is not contiguous")
                self._validate_atom_execution_contract_digest(
                    action.atom_execution_contract_digest
                )
                decision = self.decisions.get(action.decision_id)
                if decision is None or not decision.accepted:
                    raise ValueError(
                        "action_started must reference an accepted model decision"
                    )
                if decision.request_id != action.request_id:
                    raise ValueError("action/model request identity mismatch")
                if (
                    decision.selected_operation
                    and decision.selected_operation != action.action_type
                ):
                    raise ValueError("action/model selected operation mismatch")
                if (
                    decision.atom_execution_contract_digest
                    and decision.atom_execution_contract_digest
                    != action.atom_execution_contract_digest
                ):
                    raise ValueError("action/model atom contract mismatch")
                if decision.tool_selection_id:
                    selection = self.tool_selections.get(decision.tool_selection_id)
                    common_invalid = (
                        selection is None
                        or selection.status is not ToolSelectionStatus.CONSUMED
                        or selection.authorizes_execution is not False
                        or selection.selected_operation != action.action_type
                        or selection.atom_execution_contract_digest
                        != action.atom_execution_contract_digest
                    )
                    direct_invalid = (
                        decision.tool_selection_binding_kind == "consumed_handoff"
                        and selection is not None
                        and selection.consumed_decision_id != decision.decision_id
                    )
                    lineage_invalid = (
                        decision.tool_selection_binding_kind
                        == "non_authoritative_lineage"
                        and selection is not None
                        and selection.consumed_decision_id == decision.decision_id
                    )
                    if (
                        common_invalid
                        or direct_invalid
                        or lineage_invalid
                        or decision.tool_selection_binding_kind
                        not in {
                            "consumed_handoff",
                            "non_authoritative_lineage",
                        }
                    ):
                        raise ValueError(
                            "action requires a consumed, reauthorized Selector handoff"
                        )
                if self.active_action_id is not None:
                    raise ValueError("more than one action is active")
                self.actions[action.action_id] = action
                self.active_action_id = action.action_id
                self.next_action_sequence += 1
            elif event.event_type == "action_finished":
                action_value = payload.get("action")
                if not isinstance(action_value, Mapping):
                    raise ValueError("action_finished requires a complete action")
                action = ActionRecord.from_dict(action_value)
                if event.subject_id != action.action_id:
                    raise ValueError("action_finished subject mismatch")
                started = self.actions.get(action.action_id)
                if started is None or started.status != ActionStatus.RUNNING:
                    raise ValueError("action_finished has no matching running action")
                immutable_fields = (
                    "action_id", "sequence", "action_type", "arguments", "wire_arguments",
                    "action_fingerprint", "idempotency_key", "decision_id", "request_id",
                    "started_at", "workspace_digest_before",
                    "atom_execution_contract_digest",
                )
                if any(
                    getattr(started, name) != getattr(action, name)
                    for name in immutable_fields
                ):
                    raise ValueError("action_finished changed started action identity")
                if action.status == ActionStatus.RUNNING or action.result is None:
                    raise ValueError("action_finished requires terminal status and result")
                if str(action.result.get("action_type") or "") != action.action_type:
                    raise ValueError("action result operation mismatch")
                result_success = bool(action.result.get("success", False))
                if result_success != (action.status == ActionStatus.SUCCEEDED):
                    raise ValueError("action result success/status mismatch")
                artifact_values = payload.get("artifacts") or []
                artifact_ids = [str(item.get("artifact_id") or "") for item in artifact_values]
                if action.artifact_refs != artifact_ids:
                    raise ValueError("action artifact projection mismatch")
                self.actions[action.action_id] = action
                if self.active_action_id == action.action_id:
                    self.active_action_id = None
                for item in artifact_values:
                    artifact = ArtifactRecord(**dict(item))
                    if artifact.action_id != action.action_id:
                        raise ValueError("artifact action mismatch")
                    self.artifacts[artifact.artifact_id] = artifact
                for item in payload.get("artifact_revisions") or []:
                    revision = ArtifactRevision(**dict(item))
                    if (
                        revision.action_id != action.action_id
                        or revision.artifact_id not in artifact_ids
                    ):
                        raise ValueError("artifact revision action mismatch")
                    self.artifact_revisions.setdefault(revision.target, []).append(revision)
                if action.observation_fingerprint:
                    self.observation_counts[action.observation_fingerprint] = (
                        self.observation_counts.get(action.observation_fingerprint, 0) + 1
                    )
                if action.failure_key:
                    self.failure_budgets[action.failure_key] = (
                        self.failure_budgets.get(action.failure_key, 0) + 1
                    )
            elif event.event_type in {
                "model_call_accepted",
                "model_call_rejected",
                "tool_selection_accepted",
                "tool_selection_rejected",
            }:
                decision_value = payload.get("decision")
                if not isinstance(decision_value, Mapping):
                    raise ValueError("model decision event requires the complete decision")
                decision = DecisionRecord.from_dict(decision_value)
                if event.subject_id != decision.decision_id:
                    raise ValueError("model decision subject mismatch")
                if decision.decision_id in self.decisions:
                    raise ValueError("model decision id was recorded more than once")
                self.decisions[decision.decision_id] = decision
                selection_value = payload.get("selection")
                if isinstance(selection_value, Mapping):
                    selection = ToolSelectionRecord.from_dict(selection_value)
                    self._validate_atom_execution_contract_digest(
                        selection.atom_execution_contract_digest
                    )
                    if selection.consumed_decision_id != decision.decision_id:
                        raise ValueError(
                            "model decision consumed a different tool selection"
                        )
                    if decision.tool_selection_id and (
                        decision.tool_selection_id != selection.selection_id
                        or decision.selected_operation
                        != selection.selected_operation
                        or decision.atom_execution_contract_digest
                        != selection.atom_execution_contract_digest
                    ):
                        raise ValueError(
                            "model decision changed its exact tool selection binding"
                        )
                    if decision.tool_selection_binding_kind != "consumed_handoff":
                        raise ValueError(
                            "direct selection consumption requires consumed_handoff binding"
                        )
                    self._consume_tool_selection(selection)
                elif decision.tool_selection_id:
                    inherited = self.tool_selections.get(
                        decision.tool_selection_id
                    )
                    if (
                        inherited is None
                        or inherited.status is not ToolSelectionStatus.CONSUMED
                        or decision.selected_operation
                        != inherited.selected_operation
                        or decision.atom_execution_contract_digest
                        != inherited.atom_execution_contract_digest
                    ):
                        raise ValueError(
                            "model decision inherited an invalid tool selection binding"
                        )
                    inheritance = payload.get("selection_inheritance")
                    if (
                        decision.tool_selection_binding_kind
                        != "non_authoritative_lineage"
                        or not isinstance(inheritance, Mapping)
                        or inheritance.get("selection_id") != inherited.selection_id
                        or inheritance.get("selected_operation")
                        != inherited.selected_operation
                        or inheritance.get("tool_definition_digest")
                        != inherited.tool_definition_digest
                    ):
                        raise ValueError(
                            "model decision selection lineage is not explicitly audited"
                        )
                temp_value = payload.get("temp_decision")
                if isinstance(temp_value, Mapping):
                    self.temp_decisions.append(TempDecision(**dict(temp_value)))
            elif event.event_type in {
                "exact_tool_selection_staged",
                "exact_tool_selection_committed",
            }:
                selection_value = payload.get("selection")
                if not isinstance(selection_value, Mapping):
                    raise ValueError(
                        "exact tool selection staging requires a complete selection"
                    )
                selection = ToolSelectionRecord.from_dict(selection_value)
                if event.subject_id != selection.selection_id:
                    raise ValueError("tool selection subject mismatch")
                if selection.status is not ToolSelectionStatus.STAGED:
                    raise ValueError("new tool selection must be staged")
                self._validate_atom_execution_contract_digest(
                    selection.atom_execution_contract_digest
                )
                if selection.selection_id in self.tool_selections:
                    raise ValueError("tool selection id was committed more than once")
                if self.pending_selection_id:
                    raise ValueError(
                        "a new tool selection cannot replace an unconsumed selection"
                    )
                self.tool_selections[selection.selection_id] = selection
                self.pending_selection_id = selection.selection_id
            elif event.event_type == "exact_tool_selection_consumed":
                selection_value = payload.get("selection")
                if not isinstance(selection_value, Mapping):
                    raise ValueError(
                        "exact_tool_selection_consumed requires a complete selection"
                    )
                selection = ToolSelectionRecord.from_dict(selection_value)
                self._validate_atom_execution_contract_digest(
                    selection.atom_execution_contract_digest
                )
                if event.subject_id != selection.selection_id:
                    raise ValueError("tool selection consumption subject mismatch")
                self._consume_tool_selection(selection)
            elif event.event_type == "exact_tool_selection_discarded":
                selection_value = payload.get("selection")
                if not isinstance(selection_value, Mapping):
                    raise ValueError(
                        "exact_tool_selection_discarded requires a complete selection"
                    )
                selection = ToolSelectionRecord.from_dict(selection_value)
                if event.subject_id != selection.selection_id:
                    raise ValueError("tool selection discard subject mismatch")
                self._discard_tool_selection(selection)
            elif event.event_type == "action_observation_appended":
                model_event_value = payload.get("model_event")
                if not isinstance(model_event_value, Mapping):
                    raise ValueError("observation append requires the complete model event")
                model_event = ModelEvent.from_dict(model_event_value)
                if event.subject_id != model_event.event_id:
                    raise ValueError("model event subject mismatch")
                if model_event.event_id in self.model_events:
                    raise ValueError("model event id was recorded more than once")
                self.model_events[model_event.event_id] = model_event
            elif event.event_type == "action_session_rolled_over":
                rollover_value = payload.get("rollover")
                if not isinstance(rollover_value, Mapping):
                    raise ValueError("rollover event requires the complete rollover")
                rollover = ModelRolloverRecord.from_dict(rollover_value)
                self.rollovers[rollover.rollover_id] = rollover
            elif event.event_type == "protocol_rejection_recorded":
                self.protocol_rejections += 1
                error_record = payload.get("error_record")
                if isinstance(error_record, Mapping):
                    self.errors.append(dict(error_record))

        for selection in self.tool_selections.values():
            selector_checkpoint = self.model_states.get(
                selection.selector_checkpoint_id
            )
            executor_checkpoint = self.model_states.get(
                selection.executor_parent_checkpoint_id
            )
            if selector_checkpoint is None or executor_checkpoint is None:
                raise ValueError("tool selection references a missing model checkpoint")
            if (
                selector_checkpoint.lane_kind is not ModelLaneKind.SELECTOR
                or selector_checkpoint.model != selection.selector_model
                or selector_checkpoint.native_state_ref != selection.selector_state_ref
                or selector_checkpoint.native_state_digest
                != selection.selector_state_digest
                or selector_checkpoint.state_profile_id
                != selection.selector_profile_id
                or selector_checkpoint.state_profile_sha256
                != selection.selector_profile_sha256
            ):
                raise ValueError("tool selection Selector checkpoint identity mismatch")
            selector_metadata = selector_checkpoint.native_state_metadata or {}
            if (
                selector_metadata.get("model_sha256")
                != selection.selector_model_sha256
                or selector_metadata.get("head_sha256")
                != selection.selector_head_sha256
            ):
                raise ValueError("tool selection Selector artifact identity mismatch")
            if (
                executor_checkpoint.lane_kind is not ModelLaneKind.ACTION
                or executor_checkpoint.model != selection.executor_model
                or executor_checkpoint.transcript_digest
                != selection.executor_parent_digest
                or executor_checkpoint.state_profile_id
                != selection.executor_profile_id
                or executor_checkpoint.state_profile_sha256
                != selection.executor_profile_sha256
            ):
                raise ValueError("tool selection Executor checkpoint identity mismatch")
            executor_metadata = executor_checkpoint.native_state_metadata or {}
            if (
                executor_metadata.get("model_sha256")
                != selection.executor_model_sha256
            ):
                raise ValueError("tool selection Executor artifact identity mismatch")

        if len(seen) != len(self.causal_records):
            raise ValueError("causal record set contains unordered events")

    def to_dict(self, *, include_projections: bool = True) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "revision": self.revision,
            "goal": self.goal.to_dict(),
            "causal_records": {
                key: value.to_dict() for key, value in self.causal_records.items()
            },
            "causal_order": list(self.causal_order),
            "model_states": {key: value.to_dict() for key, value in self.model_states.items()},
            "action_lane_checkpoint_id": self.action_lane_checkpoint_id,
            "lane_heads": dict(self.lane_heads),
            "projection_digest": self.projection_digest,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_projections:
            value.update(self.projection_payload())
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunState":
        schema_version = str(value.get("schema_version") or "")
        if schema_version != RUN_SCHEMA_VERSION:
            raise ValueError(f"unsupported run schema: {schema_version}")
        action_lane_checkpoint_id = str(
            value.get("action_lane_checkpoint_id") or ""
        )
        lane_heads = {
            str(key): str(item)
            for key, item in (value.get("lane_heads") or {}).items()
        }
        if action_lane_checkpoint_id and "executor" not in lane_heads:
            lane_heads["executor"] = action_lane_checkpoint_id
        state = cls(
            schema_version=schema_version,
            run_id=str(value.get("run_id") or ""),
            revision=int(value.get("revision", 0) or 0),
            goal=GoalState.from_dict(value.get("goal") or {}),
            causal_records={
                str(key): CausalEvent.from_dict(item)
                for key, item in (value.get("causal_records") or {}).items()
                if isinstance(item, Mapping)
            },
            causal_order=[str(item) for item in value.get("causal_order") or []],
            model_states={
                str(key): ModelCheckpoint.from_dict(item)
                for key, item in (value.get("model_states") or {}).items()
                if isinstance(item, Mapping)
            },
            action_lane_checkpoint_id=action_lane_checkpoint_id,
            lane_heads=lane_heads,
            created_at=str(value.get("created_at") or ""),
            updated_at=str(value.get("updated_at") or ""),
        )
        for role, checkpoint_id in state.lane_heads.items():
            if role not in {"selector", "executor", "auditor"}:
                raise ValueError(f"unsupported stored model lane role: {role!r}")
            if checkpoint_id not in state.model_states:
                raise ValueError("stored model lane head references a missing checkpoint")
        state.rebuild_projection()
        expected_projection_digest = str(value.get("projection_digest") or "")
        if expected_projection_digest and expected_projection_digest != state.projection_digest:
            raise ValueError("run projection digest mismatch")
        return state


__all__ = [
    "CAUSAL_EVENT_PAYLOAD_SCHEMAS",
    "CAUSAL_EVENT_SCHEMA_VERSION",
    "GOAL_SCHEMA_VERSION",
    "RUN_SCHEMA_VERSION",
    "ActionRecord",
    "ActionStatus",
    "ArtifactRecord",
    "ArtifactRevision",
    "CausalEvent",
    "CausalEventDraft",
    "ChunkDescriptor",
    "DecisionRecord",
    "GoalState",
    "ModelCheckpoint",
    "ModelCheckpointStatus",
    "ModelEvent",
    "ModelLaneKind",
    "ModelRolloverRecord",
    "RunState",
    "RunStatus",
    "TaskAction",
    "TempDecision",
    "ToolSelectionRecord",
    "ToolSelectionStatus",
    "ValidationSpec",
    "action_fingerprint",
    "utc_now",
]
