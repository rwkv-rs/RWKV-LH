from __future__ import annotations

import pytest

from rwkv_lh.goal_state_protocols import ROLE_STATE_IDS
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ModelLaneKind


class _UnusedClient:
    model_name = "rwkv7-g1j-13.3b-test"

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        raise AssertionError("architecture construction must not generate")


def _session(role: str, digest_character: str) -> ModelSession:
    return ModelSession(
        _UnusedClient(),
        settings=RuntimeSettings(
            base_url="http://127.0.0.1:29613/v1",
            api_key="",
            model="rwkv7-g1j-13.3b-test",
            model_sha256="a" * 64,
            tool_disclosure_mode="progressive",
            state_transport="prompt_replay",
            state_profile_id=ROLE_STATE_IDS[role],
            state_profile_sha256=digest_character * 64,
        ),
    )


def test_gate0_generative_roles_have_distinct_lanes_sessions_and_profiles() -> None:
    executor = _session("executor_args", "1")
    step_auditor = _session("auditor_step", "2")
    finalizer = _session("finalizer_answer", "3")
    final_auditor = _session("auditor_final", "4")
    model = LongHorizonModel(
        executor,
        step_auditor_session=step_auditor,
        finalizer_session=finalizer,
        final_auditor_session=final_auditor,
    )

    model.validate_goal_role_sessions()

    assert len(
        {
            id(model.session),
            id(model.step_auditor_session),
            id(model.finalizer_session),
            id(model.final_auditor_session),
        }
    ) == 4
    assert {
        ModelLaneKind.ACTION.value,
        ModelLaneKind.STEP_AUDIT.value,
        ModelLaneKind.FINALIZER.value,
        ModelLaneKind.FINAL_AUDIT.value,
    } == {"action", "auditor_step", "finalizer", "auditor_final"}


def test_gate0_rejects_cross_role_state_identity() -> None:
    model = LongHorizonModel(
        _session("executor_args", "1"),
        step_auditor_session=_session("auditor_step", "2"),
        finalizer_session=_session("finalizer_answer", "3"),
        final_auditor_session=_session("auditor_step", "4"),
    )

    with pytest.raises(ValueError, match="another role's State profile"):
        model.validate_goal_role_sessions()


def test_gate0_rejects_shared_session_even_with_distinct_role_arguments() -> None:
    executor = _session("executor_args", "1")
    shared_auditor = _session("auditor_step", "2")
    model = LongHorizonModel(
        executor,
        step_auditor_session=shared_auditor,
        finalizer_session=_session("finalizer_answer", "3"),
        final_auditor_session=shared_auditor,
    )

    with pytest.raises(ValueError, match="distinct Executor"):
        model.validate_goal_role_sessions()
