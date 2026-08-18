from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ModelEvent, ModelLaneKind
from rwkv_lh.store import LongHorizonStore


@dataclass
class Response:
    content: str
    finish_reason: str = "stop"


class PhysicalQueueClient:
    model_name = "test-rwkv"

    def __init__(self, calls: list[dict | str]):
        self.outputs = [
            item if isinstance(item, str) else json.dumps(item, separators=(",", ":"))
            for item in calls
        ]
        self.prompts: list[str] = []
        self.responses: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        if not self.outputs:
            raise AssertionError("unexpected model request")
        output = self.outputs.pop(0)
        self.responses.append(output)
        return Response(output)


def call(name: str, **arguments):
    return {"function": name, "params": arguments}


def settings() -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
    )


def build(tmp_path: Path, calls: list[dict | str]):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    client = PhysicalQueueClient(calls)
    harness = ActionHarness(sandbox_commands=False)
    session = ModelSession(client, settings=settings())
    model = LongHorizonModel(session, harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal(
        "Combine the two inputs exactly.",
        str(workspace),
        constraints=["Operate only inside the workspace"],
    )
    state = store.create_run(goal, "RUN")
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        max_transitions=20,
    )
    return controller, workspace, client


def ensemble_event(state, pair_count: int):
    return next(
        record
        for record in state.causal_records.values()
        if record.event_type == "model_call_accepted"
        and record.payload.get("order_ensemble", {}).get("pair_count") == pair_count
    )


def test_transcript_permutations_preserve_canonical_bytes_and_rebase_digest() -> None:
    raw = call("final_answer", text="same")
    client = PhysicalQueueClient([raw, raw, raw, raw])
    session = ModelSession(client, settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "work",
        [FINAL_ANSWER_DEFINITION],
        lane_id="LANE:ACTION",
    )
    for sequence in (1, 2):
        candidate = session.generate(checkpoint, max_output_tokens=100)
        checkpoint = session.commit(candidate, session.parse(candidate))
        checkpoint = session.append(
            checkpoint,
            ModelEvent(
                "action_result",
                f"EV-{sequence}",
                "LANE:ACTION",
                {"sequence": sequence},
            ),
        )

    pair_count, variants = LongHorizonModel._order_ensemble_transcripts(
        checkpoint.transcript
    )
    by_name = dict(variants)
    assert pair_count == 2
    assert by_name["canonical"] == checkpoint.transcript
    assert by_name["reversed"] == by_name["rotated"]
    assert by_name["reversed"] != by_name["canonical"]

    canonical = session.generate(checkpoint, max_output_tokens=100)
    reordered = session.generate(
        checkpoint,
        max_output_tokens=100,
        transcript_override=by_name["reversed"],
    )
    materialized = session.materialize_candidate(reordered, checkpoint)
    assert materialized.checkpoint.transcript_digest == canonical.checkpoint.transcript_digest


def test_no_majority_executes_canonical_candidate(tmp_path: Path) -> None:
    controller, workspace, client = build(
        tmp_path,
        [
            call("read_file", path="a.txt"),
            call("read_file", path="b.txt"),
            call("write_file", path="alternate-one.txt", content="one\n"),
            call("write_file", path="alternate-two.txt", content="two\n"),
            call("write_file", path="combined.txt", content="canonical\n"),
            call("final_answer", text="reversed final"),
            call("final_answer", text="rotated final"),
            call("final_answer", text="canonical final"),
        ],
    )
    (workspace / "a.txt").write_text("alpha\n")
    (workspace / "b.txt").write_text("beta\n")

    result = controller.run("RUN")

    assert (workspace / "combined.txt").read_text() == "canonical\n"
    assert not (workspace / "alternate-one.txt").exists()
    assert not (workspace / "alternate-two.txt").exists()
    assert result.final_output == "canonical final"
    vote = ensemble_event(result.state, 2).payload["order_ensemble"]
    assert vote["vote_type"] == "canonical_fallback"
    assert vote["agreement"] == "none"
    assert vote["selected_permutation"] == "canonical"
    assert vote["canonical_overridden"] is False
    assert len(client.prompts) == 8
    assert client.outputs == []
    assert json.loads(client.responses[-1])["params"]["text"] == result.final_output


def test_noncanonical_majority_rebases_raw_and_keeps_canonical_final_text(
    tmp_path: Path,
) -> None:
    controller, workspace, client = build(
        tmp_path,
        [
            call("read_file", path="a.txt"),
            call("read_file", path="b.txt"),
            call("write_file", path="combined.txt", content="alpha\nbeta\n"),
            call("write_file", path="combined.txt", content="alpha\nbeta\n"),
            call("write_file", path="wrong.txt", content="wrong\n"),
            call("final_answer", text="reversed final"),
            call("final_answer", text="rotated final"),
            call("final_answer", text="  canonical final\nline two\n"),
        ],
    )
    (workspace / "a.txt").write_text("alpha\n")
    (workspace / "b.txt").write_text("beta\n")

    result = controller.run("RUN")

    assert not (workspace / "wrong.txt").exists()
    assert (workspace / "combined.txt").read_text() == "alpha\nbeta\n"
    assert result.final_output == "  canonical final\nline two\n"

    action_event = ensemble_event(result.state, 2)
    action_vote = action_event.payload["order_ensemble"]
    assert action_vote["vote_type"] == "exact_command_digest"
    assert action_vote["agreement"] == "2/3"
    assert action_vote["selected_permutation"] == "reversed"
    assert action_vote["canonical_overridden"] is True

    decision = result.state.decisions[action_event.subject_id]
    input_checkpoint = result.state.model_states[decision.input_checkpoint_id]
    output_checkpoint = result.state.model_states[decision.output_checkpoint_id]
    assert output_checkpoint.transcript == input_checkpoint.transcript + decision.raw_output

    final_event = ensemble_event(result.state, 3)
    final_vote = final_event.payload["order_ensemble"]
    assert final_vote["vote_type"] == "final_operation"
    assert final_vote["agreement"] == "3/3"
    assert final_vote["selected_permutation"] == "canonical"
    assert len(client.prompts) == 8
    assert client.outputs == []
    assert json.loads(client.responses[-1])["params"]["text"] == result.final_output


def test_noncanonical_final_majority_selects_last_physical_final(tmp_path: Path) -> None:
    controller, workspace, client = build(
        tmp_path,
        [
            call("read_file", path="a.txt"),
            call("read_file", path="b.txt"),
            call("final_answer", text="reversed final"),
            call("final_answer", text="rotated final selected"),
            call("write_file", path="wrong.txt", content="wrong\n"),
        ],
    )
    (workspace / "a.txt").write_text("alpha\n")
    (workspace / "b.txt").write_text("beta\n")

    result = controller.run("RUN")

    assert result.final_output == "rotated final selected"
    assert not (workspace / "wrong.txt").exists()
    vote = ensemble_event(result.state, 2).payload["order_ensemble"]
    assert vote["vote_type"] == "final_operation"
    assert vote["agreement"] == "2/3"
    assert vote["selected_permutation"] == "rotated"
    assert vote["canonical_overridden"] is True
    final_responses = [
        json.loads(response)["params"]["text"]
        for response in client.responses
        if json.loads(response)["function"] == "final_answer"
    ]
    assert final_responses[-1] == result.final_output
    assert len(client.prompts) == 5
    assert client.outputs == []
