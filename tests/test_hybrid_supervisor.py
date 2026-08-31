from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import RunStatus
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.trace_projection import unresolved_supervisor_pending
from rwkv_lh.supervisor import (
    DirectiveDisposition,
    DirectiveReviewStatus,
    ReviewDisposition,
    SupervisorDirective,
    SupervisorDirectiveRequest,
    SupervisorPlan,
    SupervisorPlanRequest,
    SupervisorPolicy,
    SupervisorReview,
    SupervisorReviewRequest,
)


@dataclass
class Response:
    content: str
    finish_reason: str = "stop"


class QueueClient:
    model_name = "test-rwkv"

    def __init__(self, calls: list[dict]):
        self.outputs = [json.dumps(item, separators=(",", ":")) for item in calls]
        self.prompts: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        if not self.outputs:
            raise AssertionError("unexpected RWKV request")
        return Response(self.outputs.pop(0))


class FakeSupervisor:
    provider_name = "test-provider"
    model_name = "test-strong-model"

    def __init__(self, reviews: list[SupervisorReview]):
        self.reviews = list(reviews)
        self.plan_requests: list[SupervisorPlanRequest] = []
        self.review_requests: list[SupervisorReviewRequest] = []

    def create_plan(self, request: SupervisorPlanRequest) -> SupervisorPlan:
        self.plan_requests.append(request)
        return SupervisorPlan.create(
            objective="Make the requested workspace change.",
            constraints=request.constraints,
            steps=("Inspect current state.", "Apply the smallest correct change."),
            completion_checks=("Verify the requested result from workspace evidence.",),
            risks=("Do not report completion before observing the result.",),
        )

    def review_final(self, request: SupervisorReviewRequest) -> SupervisorReview:
        self.review_requests.append(request)
        if not self.reviews:
            raise AssertionError("unexpected supervisor review")
        return self.reviews.pop(0)

    def next_directive(
        self, request: SupervisorDirectiveRequest
    ) -> SupervisorDirective:
        raise AssertionError("unexpected online supervisor directive")


class OnlineFakeSupervisor(FakeSupervisor):
    def __init__(self, directives: list[dict]):
        super().__init__([])
        self.directives = list(directives)
        self.directive_requests: list[SupervisorDirectiveRequest] = []

    def create_plan(self, request: SupervisorPlanRequest) -> SupervisorPlan:
        raise AssertionError("online supervisor must not create a static plan")

    def next_directive(
        self, request: SupervisorDirectiveRequest
    ) -> SupervisorDirective:
        self.directive_requests.append(request)
        if not self.directives:
            raise AssertionError("unexpected online supervisor directive")
        value = self.directives.pop(0)
        return SupervisorDirective.create(
            directive_index=request.directive_index,
            outcome_ref=request.outcome_ref,
            **value,
        )


class FailingPlanSupervisor(FakeSupervisor):
    def create_plan(self, request: SupervisorPlanRequest) -> SupervisorPlan:
        self.plan_requests.append(request)
        raise RuntimeError("provider unavailable")


class RecoveringPlanSupervisor(FakeSupervisor):
    def __init__(self, reviews: list[SupervisorReview]):
        super().__init__(reviews)
        self.fail_once = True

    def create_plan(self, request: SupervisorPlanRequest) -> SupervisorPlan:
        if self.fail_once:
            self.fail_once = False
            self.plan_requests.append(request)
            raise RuntimeError("transient provider outage")
        return super().create_plan(request)


class ProcessLossDuringReviewSupervisor(FakeSupervisor):
    def __init__(self, reviews: list[SupervisorReview]):
        super().__init__(reviews)
        self.lose_process_once = True

    def review_final(self, request: SupervisorReviewRequest) -> SupervisorReview:
        self.review_requests.append(request)
        if self.lose_process_once:
            self.lose_process_once = False
            raise SystemExit("simulated process loss before review commit")
        if not self.reviews:
            raise AssertionError("unexpected supervisor review")
        return self.reviews.pop(0)


def call(operation: str, **arguments):
    return {"function": operation, "params": arguments}


def settings(*, tool_disclosure_mode: str = "full") -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode=tool_disclosure_mode,
    )


def build(
    tmp_path: Path,
    calls: list[dict],
    supervisor: FakeSupervisor,
    *,
    policy: SupervisorPolicy | None = None,
    tool_disclosure_mode: str = "full",
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    client = QueueClient(calls)
    model = LongHorizonModel(
        ModelSession(
            client,
            settings=settings(tool_disclosure_mode=tool_disclosure_mode),
        ),
        harness=harness,
    )
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal(
        "Create hello.txt containing hello.",
        str(workspace),
        constraints=["Operate only inside the workspace"],
    )
    store.create_run(goal, "RUN")
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=policy,
        max_transitions=20,
    )
    return controller, store, workspace, client


def test_supervisor_guidance_preserves_progressive_select_then_call_protocol(
    tmp_path: Path,
) -> None:
    passed = SupervisorReview.create(
        ReviewDisposition.PASS,
        summary="The write and read-back support completion.",
    )
    supervisor = FakeSupervisor([passed])
    controller, _, workspace, client = build(
        tmp_path,
        [
            call("select_tool", name="write_file"),
            call("write_file", path="hello.txt", content="hello"),
            call("select_tool", name="read_file"),
            call("read_file", path="hello.txt"),
            call("select_tool", name="final_answer"),
            call("final_answer", text="Created and verified hello.txt."),
        ],
        supervisor,
        tool_disclosure_mode="progressive",
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(client.prompts) == 6
    assert '"function":"select_tool"' in client.prompts[0]
    assert "when it asks for select_tool" in client.prompts[0]
    assert "selected_operation" in client.prompts[1]


def test_supervisor_plan_and_pass_wrap_rwkv_without_rewriting_output(
    tmp_path: Path,
) -> None:
    passed = SupervisorReview.create(
        ReviewDisposition.PASS,
        summary="The candidate is supported by the observed workspace state.",
    )
    supervisor = FakeSupervisor([passed])
    controller, store, _, client = build(
        tmp_path,
        [call("final_answer", text="Nothing else was required.")],
        supervisor,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Nothing else was required."
    assert len(supervisor.plan_requests) == 1
    assert len(supervisor.review_requests) == 1
    assert supervisor.review_requests[0].candidate_output == result.final_output
    assert "supervisor_plan" in client.prompts[0]
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("supervisor_plan_committed") == 1
    assert event_types.count("supervisor_review_recorded") == 1
    completed = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_completed"
    ][0]
    assert completed.payload["output_source"] == "rwkv_explicit_final_answer_text"
    assert completed.payload["controller_rewritten"] is False
    assert store.load("RUN").final_output == result.final_output


def test_online_supervisor_reviews_rwkv_action_wave_instead_of_each_tool_call(
    tmp_path: Path,
) -> None:
    supervisor = OnlineFakeSupervisor(
        [
            {
                "disposition": DirectiveDisposition.CONTINUE,
                "review_status": DirectiveReviewStatus.INITIAL,
                "review_summary": "Start with one bounded artifact microtask.",
                "microtask_objective": "Create and verify hello.txt.",
                "completion_checks": ("hello.txt contains hello.",),
                "constraints": ("Use observed workspace evidence.",),
            },
            {
                "disposition": DirectiveDisposition.ACCEPT_FINAL,
                "review_status": DirectiveReviewStatus.SATISFIED,
                "review_summary": "The RWKV actions and exact candidate support completion.",
            },
        ]
    )
    controller, _, workspace, client = build(
        tmp_path,
        [
            call("write_file", path="hello.txt", content="hello"),
            call("read_file", path="hello.txt"),
            call("final_answer", text="Created and verified hello.txt."),
        ],
        supervisor,
        policy=SupervisorPolicy(
            mode="online_microtask",
            max_online_directives=8,
            online_actions_per_directive=6,
        ),
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created and verified hello.txt."
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(client.prompts) == 3
    assert len(supervisor.directive_requests) == 2
    assert supervisor.plan_requests == []
    final_request = supervisor.directive_requests[-1]
    assert final_request.worker_outcome is not None
    assert final_request.worker_outcome["type"] == "microtask_report"
    assert final_request.worker_outcome["action_ids"] == ["A00001", "A00002"]
    assert final_request.action_count == 2
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("supervisor_directive_committed") == 2
    assert "supervisor_plan_committed" not in event_types


def test_online_supervisor_reviews_early_after_repeated_zero_progress_action(
    tmp_path: Path,
) -> None:
    supervisor = OnlineFakeSupervisor(
        [
            {
                "disposition": "continue",
                "review_status": "initial",
                "review_summary": "Start the requested change.",
                "microtask_objective": "Create hello.txt.",
                "completion_checks": ("hello.txt exists with the requested content.",),
            },
            {
                "disposition": "continue",
                "review_status": "needs_correction",
                "review_summary": "Two identical reads made no workspace progress.",
                "issues": ("Stop repeating the failed read and create the requested file.",),
                "microtask_objective": "Create hello.txt now, then report the result.",
                "completion_checks": ("A write changes the workspace digest.",),
            },
            {
                "disposition": "accept_final",
                "review_status": "satisfied",
                "review_summary": "The corrective write supports the exact RWKV Final.",
            },
        ]
    )
    controller, _, workspace, _ = build(
        tmp_path,
        [
            call("read_file", path="hello.txt"),
            call("read_file", path="hello.txt"),
            call("write_file", path="hello.txt", content="hello"),
            call("final_answer", text="Created hello.txt."),
        ],
        supervisor,
        policy=SupervisorPolicy(
            mode="online_microtask",
            max_online_directives=8,
            online_actions_per_directive=6,
        ),
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(supervisor.directive_requests) == 3
    correction = supervisor.directive_requests[1]
    assert correction.worker_outcome is not None
    assert correction.worker_outcome["type"] == "action_batch"
    assert correction.worker_outcome["action_ids"] == ["A00001", "A00002"]
    assert correction.action_count == 2
    final = supervisor.directive_requests[2]
    assert final.worker_outcome is not None
    assert final.worker_outcome["action_ids"] == ["A00003"]


def test_online_correction_remains_reachable_after_legacy_failure_budget(
    tmp_path: Path,
) -> None:
    supervisor = OnlineFakeSupervisor(
        [
            {
                "disposition": "continue",
                "review_status": "initial",
                "review_summary": "Start the requested change.",
                "microtask_objective": "Create hello.txt.",
                "completion_checks": ("hello.txt exists with hello content.",),
            },
            {
                "disposition": "continue",
                "review_status": "needs_correction",
                "review_summary": "The repeated read failed and made no progress.",
                "issues": ("Use a side-effecting operation to create the file.",),
                "microtask_objective": "Create hello.txt instead of rereading it.",
                "completion_checks": ("The workspace digest changes after creation.",),
            },
            {
                "disposition": "continue",
                "review_status": "needs_correction",
                "review_summary": "The worker has still not applied the correction.",
                "issues": ("Stop the failed read loop and write the file.",),
                "microtask_objective": "Write hello.txt now.",
                "completion_checks": ("hello.txt contains hello.",),
            },
            {
                "disposition": "accept_final",
                "review_status": "satisfied",
                "review_summary": "The later RWKV write and exact Final satisfy the goal.",
            },
        ]
    )
    controller, _, workspace, _ = build(
        tmp_path,
        [
            call("read_file", path="hello.txt"),
            call("read_file", path="hello.txt"),
            call("read_file", path="hello.txt"),
            call("read_file", path="hello.txt"),
            call("read_file", path="hello.txt"),
            call("write_file", path="hello.txt", content="hello"),
            call("final_answer", text="Created hello.txt after correction."),
        ],
        supervisor,
        policy=SupervisorPolicy(
            mode="online_microtask",
            max_online_directives=8,
            online_actions_per_directive=6,
        ),
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(supervisor.directive_requests) == 4
    assert result.state.failure_budgets
    assert max(result.state.failure_budgets.values()) == 5


def test_online_supervisor_reviews_bounded_protocol_rejection_batch(
    tmp_path: Path,
) -> None:
    supervisor = OnlineFakeSupervisor(
        [
            {
                "disposition": "continue",
                "review_status": "initial",
                "review_summary": "Start the requested change.",
                "microtask_objective": "Create hello.txt.",
                "completion_checks": ("hello.txt contains hello.",),
            },
            {
                "disposition": "continue",
                "review_status": "needs_correction",
                "review_summary": "Two attempted calls violated the displayed schema.",
                "issues": ("Use only arguments present in the current tool contract.",),
                "microtask_objective": "Create hello.txt using a valid direct operation.",
                "completion_checks": ("The operation executes and changes the workspace.",),
            },
            {
                "disposition": "accept_final",
                "review_status": "satisfied",
                "review_summary": "The valid RWKV action and Final satisfy the request.",
            },
        ]
    )
    controller, _, workspace, _ = build(
        tmp_path,
        [
            call(
                "write_file",
                path="hello.txt",
                content="hello",
                unknown_argument=True,
            ),
            call(
                "write_file",
                path="hello.txt",
                content="hello",
                unknown_argument=True,
            ),
            call("write_file", path="hello.txt", content="hello"),
            call("final_answer", text="Created hello.txt."),
        ],
        supervisor,
        policy=SupervisorPolicy(
            mode="online_microtask",
            max_online_directives=8,
            online_actions_per_directive=6,
            online_protocol_rejections_per_directive=2,
        ),
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert result.state.protocol_rejections == 2
    assert len(supervisor.directive_requests) == 3
    correction = supervisor.directive_requests[1]
    assert correction.worker_outcome is not None
    assert correction.worker_outcome["type"] == "protocol_batch"
    assert len(correction.worker_outcome["rejection_refs"]) == 2
    assert correction.worker_outcome["action_ids"] == []


def test_supervisor_revision_returns_bounded_feedback_to_same_rwkv_lane(
    tmp_path: Path,
) -> None:
    revise = SupervisorReview.create(
        ReviewDisposition.REVISE,
        summary="The requested file has not been created.",
        issues=("Create hello.txt and verify its content before finishing.",),
    )
    passed = SupervisorReview.create(
        ReviewDisposition.PASS,
        summary="hello.txt now exists with the requested content.",
    )
    supervisor = FakeSupervisor([revise, passed])
    controller, _, workspace, client = build(
        tmp_path,
        [
            call("final_answer", text="Done."),
            call("write_file", path="hello.txt", content="hello"),
            call("final_answer", text="Created hello.txt containing hello."),
        ],
        supervisor,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created hello.txt containing hello."
    assert (workspace / "hello.txt").read_text() == "hello"
    assert len(supervisor.review_requests) == 2
    assert supervisor.review_requests[1].action_count == 1
    assert supervisor.review_requests[1].actions[0]["operation"] == "write_file"
    assert "supervisor_review" in client.prompts[1]
    assert {checkpoint.lane_id for checkpoint in result.state.model_states.values()} == {
        "LANE:ACTION"
    }


def test_revision_budget_interrupts_instead_of_creating_reviewer_loop(
    tmp_path: Path,
) -> None:
    first = SupervisorReview.create(
        ReviewDisposition.REVISE,
        summary="First candidate is incomplete.",
        issues=("Provide the missing workspace evidence.",),
    )
    second = SupervisorReview.create(
        ReviewDisposition.REVISE,
        summary="The repair is still incomplete.",
        issues=("The required file is still absent.",),
    )
    supervisor = FakeSupervisor([first, second])
    controller, _, _, client = build(
        tmp_path,
        [
            call("final_answer", text="First candidate."),
            call("final_answer", text="Second candidate."),
        ],
        supervisor,
        policy=SupervisorPolicy(max_review_repairs=1),
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.INTERRUPTED
    assert result.final_output == "Second candidate."
    assert len(supervisor.review_requests) == 2
    assert len(client.prompts) == 2
    terminal = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_interrupted"
    ][0]
    assert terminal.payload["reason"] == "supervisor_revision_budget_exhausted"
    assert terminal.payload["output_source"] == "rwkv_candidate_not_approved_by_supervisor"


def test_supervisor_plan_failure_is_audited_and_fails_closed(tmp_path: Path) -> None:
    supervisor = FailingPlanSupervisor([])
    controller, _, _, client = build(
        tmp_path,
        [call("final_answer", text="must not run")],
        supervisor,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.INTERRUPTED
    assert result.final_output == ""
    assert client.prompts == []
    failures = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "supervisor_call_failed"
    ]
    assert len(failures) == 1
    assert failures[0].payload["phase"] == "plan"
    assert failures[0].payload["fail_closed"] is True
    pending = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "supervisor_call_pending"
    ]
    assert len(pending) == 1
    assert pending[0].payload["phase"] == "plan"
    assert pending[0].payload["retry_trigger"] == "resume_or_proactive_scheduler"


def test_pending_supervisor_plan_retries_from_committed_state_on_resume(
    tmp_path: Path,
) -> None:
    supervisor = RecoveringPlanSupervisor(
        [SupervisorReview.create(ReviewDisposition.PASS, summary="supported")]
    )
    controller, _, _, client = build(
        tmp_path,
        [call("final_answer", text="Exact recovered candidate.")],
        supervisor,
    )

    first = controller.run("RUN")
    recovered = controller.resume("RUN")

    assert first.state.status == RunStatus.INTERRUPTED
    assert recovered.state.status == RunStatus.COMPLETED
    assert recovered.final_output == "Exact recovered candidate."
    assert len(supervisor.plan_requests) == 2
    assert len(client.prompts) == 1
    assert unresolved_supervisor_pending(recovered.state) == ()
    resolved = [
        event
        for event in recovered.state.causal_records.values()
        if event.event_type == "supervisor_call_resolved"
    ]
    assert len(resolved) == 1
    assert resolved[0].payload["phase"] == "plan"


def test_pending_resolution_recovers_if_process_stops_after_plan_commit(
    tmp_path: Path,
) -> None:
    supervisor = RecoveringPlanSupervisor(
        [SupervisorReview.create(ReviewDisposition.PASS, summary="supported")]
    )
    controller, store, _, client = build(
        tmp_path,
        [call("final_answer", text="Exact recovered candidate.")],
        supervisor,
    )
    first = controller.run("RUN")
    assert first.state.status == RunStatus.INTERRUPTED
    original_save = store.save
    lost_once = False

    def stop_before_resolution(state, *, expected_revision=None, causal_event):
        nonlocal lost_once
        if causal_event.event_type == "supervisor_call_resolved" and not lost_once:
            lost_once = True
            raise RuntimeError("simulated process loss before pending resolution")
        return original_save(
            state,
            expected_revision=expected_revision,
            causal_event=causal_event,
        )

    store.save = stop_before_resolution  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="before pending resolution"):
        controller.resume("RUN")
    store.save = original_save  # type: ignore[method-assign]
    committed = store.load("RUN")
    assert any(
        event.event_type == "supervisor_plan_committed"
        for event in committed.causal_records.values()
    )
    assert len(unresolved_supervisor_pending(committed)) == 1

    recovered = controller.resume("RUN")

    assert recovered.state.status == RunStatus.COMPLETED
    assert unresolved_supervisor_pending(recovered.state) == ()
    assert len(supervisor.plan_requests) == 2
    assert len(client.prompts) == 1


def test_passed_review_is_recovered_without_repeating_either_model_call(
    tmp_path: Path,
) -> None:
    passed = SupervisorReview.create(
        ReviewDisposition.PASS,
        summary="The final candidate passes the completion checks.",
    )
    supervisor = FakeSupervisor([passed])
    controller, store, _, client = build(
        tmp_path,
        [call("final_answer", text="Exact RWKV candidate.")],
        supervisor,
    )
    original_save = store.save

    def interrupt_before_terminal(state, *, expected_revision=None, causal_event):
        if causal_event.event_type == "run_completed":
            raise RuntimeError("simulated process loss after review commit")
        return original_save(
            state,
            expected_revision=expected_revision,
            causal_event=causal_event,
        )

    store.save = interrupt_before_terminal  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="simulated process loss"):
        controller.run("RUN")
    store.save = original_save  # type: ignore[method-assign]

    result = controller.resume("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Exact RWKV candidate."
    assert len(supervisor.plan_requests) == 1
    assert len(supervisor.review_requests) == 1
    assert len(client.prompts) == 1


def test_hybrid_resume_without_supervisor_cannot_bypass_review(tmp_path: Path) -> None:
    passed = SupervisorReview.create(
        ReviewDisposition.PASS,
        summary="Unused scripted review.",
    )
    supervisor = FakeSupervisor([passed])
    controller, store, _, client = build(
        tmp_path,
        [call("final_answer", text="must not be accepted")],
        supervisor,
    )
    original_save = store.save

    def interrupt_before_rwkv_session(state, *, expected_revision=None, causal_event):
        if causal_event.event_type == "action_session_started":
            raise RuntimeError("simulated process loss after plan commit")
        return original_save(
            state,
            expected_revision=expected_revision,
            causal_event=causal_event,
        )

    store.save = interrupt_before_rwkv_session  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="simulated process loss"):
        controller.run("RUN")
    store.save = original_save  # type: ignore[method-assign]

    pure_controller = LongHorizonController(
        store,
        model=controller.model,
        harness=controller.harness,
    )
    result = pure_controller.resume("RUN")

    assert result.state.status == RunStatus.INTERRUPTED
    assert result.final_output == ""
    assert client.prompts == []
    missing = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "supervisor_configuration_missing"
    ]
    assert len(missing) == 1
    assert missing[0].payload["fail_closed"] is True


def test_unreviewed_committed_rwkv_final_is_recovered_without_regeneration(
    tmp_path: Path,
) -> None:
    passed = SupervisorReview.create(
        ReviewDisposition.PASS,
        summary="Recovered candidate passes.",
    )
    supervisor = ProcessLossDuringReviewSupervisor([passed])
    controller, _, _, client = build(
        tmp_path,
        [call("final_answer", text="Persisted before the process loss.")],
        supervisor,
    )

    with pytest.raises(SystemExit, match="simulated process loss"):
        controller.run("RUN")
    result = controller.resume("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Persisted before the process loss."
    assert len(client.prompts) == 1
    assert len(supervisor.plan_requests) == 1
    # The unknown-outcome review is retried, but the committed RWKV generation is not.
    assert len(supervisor.review_requests) == 2
