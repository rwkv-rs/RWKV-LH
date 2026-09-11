"""Fixed-evaluation mechanism fixtures; never role training examples."""
from dataclasses import asdict, replace
import importlib
from types import SimpleNamespace

import pytest

from rwkv_lh import statetune_core as core
from rwkv_lh import statetune_data as data
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_SELECTOR_MENU_ORDER_IDS, NetworkSelectorInput
from rwkv_lh.goal_state_protocols import selector_intent_v7
from rwkv_lh.role_trace_inputs import rebuild_role_input
from rwkv_lh.token_budget import tokenizer
from test_native_network_selector_service import _settings
from test_role_trace_inputs import _selector_boundary
from test_statetune_data import row as opaque_row


def api():
    return importlib.import_module("rwkv_lh.statetune_evaluation")


def plan(**thresholds):
    return {"schema_version": api().PLAN_SCHEMA, "role": "selector_intent",
        "regression_fingerprint": "a" * 64,
        "metrics": ["menu_accuracy", "ensemble_accuracy", "transport_failures"],
        "thresholds": {"menu_accuracy": 0.95, "ensemble_accuracy": 0.95,
            "max_transport_failures": 0, "max_regressions": 0, **thresholds},
        "agent_metrics": ["strict", "completed", "mutation", "termination_reasons"],
        "retention_rule": "role_qualification_then_separate_agent_acceptance"}


@pytest.mark.parametrize("thresholds", [{"menu_accuracy": -1}, {"ensemble_accuracy": float("nan")},
    {"max_transport_failures": 1}, {"max_regressions": True}])
def test_invalid_evaluation_rules_fail_before_model_call(thresholds):
    with pytest.raises(ValueError):
        api().validate_plan(plan(**thresholds))


def test_explicit_evaluation_split_does_not_let_trainer_read_regression():
    sample = opaque_row()
    sample["split"] = "dev"
    kwargs = dict(role="selector_intent", model_sha256="b" * 64,
                  context_tokens=16384, vocab_size=65536, bos_token_id=0)
    with pytest.raises(ValueError, match="train row"):
        data.normalize_row(sample, **kwargs)
    assert data.normalize_row(sample, expected_split="dev", **kwargs)["sample_id"] == sample["sample_id"]


def case(tmp_path, *, menu="canonical", split="dev"):
    _store, state = _selector_boundary(tmp_path)
    boundary = state.causal_order[-1]
    rebuilt = rebuild_role_input("selector_intent", state, {"boundary_event_id": boundary, "menu_order_id": menu})
    network = rebuilt["network_input"]
    prompt = rebuilt["full_input_text"]
    sample = opaque_row()
    target_source = dict(rebuilt["prompt_source"])
    target_source.update(selected_operation="read_json", selection_authority="planner_contract",
                         selection_verifier_id=boundary)
    target = selector_intent_v7.render_target(target_source)
    tokens = tokenizer().encode(prompt)
    sample.update(source_run_id="mechanism", run_id=state.run_id, split=split,
        sample_id=split + menu, boundary_event_id=boundary, input_text=prompt,
        target_text=target, target_token_ids=tokenizer().encode(target))
    sample["context"].update(prompt_text=prompt, token_ids=[0, *tokens], reconstructed_token_ids=tokens,
        menu_order_id=menu, initial_state={"model_sha256": _settings(zero=True).model_sha256})
    source = SimpleNamespace(snapshots={boundary: state}, registration={
        "source_run_id": "mechanism", "run_id": state.run_id})
    return sample, source, network


def test_case_uses_durable_production_builder_and_rejects_prompt_drift(tmp_path):
    sample, source, network = case(tmp_path)
    result = api().rebuild_case(sample, source, _settings(zero=True))
    assert result.network.to_dict() == network and result.target == "read_json"
    sample["input_text"] += " changed"
    sample["context"]["prompt_text"] = sample["input_text"]
    ids = tokenizer().encode(sample["input_text"])
    sample["context"].update(token_ids=[0, *ids], reconstructed_token_ids=ids)
    with pytest.raises(ValueError, match="production builder"):
        api().rebuild_case(sample, source, _settings(zero=True))


def test_same_boundary_name_in_other_source_is_rejected(tmp_path):
    sample, source, _network = case(tmp_path)
    sample["source_run_id"] = "another-source"
    with pytest.raises(ValueError, match="source identity"):
        api().rebuild_case(sample, source, _settings(zero=True))


def test_comparison_changes_only_initial_state_identity():
    zero, candidate = _settings(zero=True), _settings()
    api().validate_arms({"zero": zero, "candidate": candidate})
    with pytest.raises(ValueError, match="same model"):
        api().validate_arms({"zero": zero, "candidate": replace(candidate, decoder_sha256="f" * 64)})
    with pytest.raises(ValueError, match="zero State"):
        api().validate_arms({"zero": candidate, "candidate": candidate})


def cases(tmp_path):
    sample, source, _ = case(tmp_path)
    base = api().rebuild_case(sample, source, _settings(zero=True))
    values = []
    for split in ("dev", "confirmation"):
        for menu in NETWORK_SELECTOR_MENU_ORDER_IDS:
            network = NetworkSelectorInput.create(current_subtask=base.network.current_subtask,
                current_progress=base.network.current_progress, eligible_labels=("read_file", "read_json"),
                menu_order_id=menu)
            values.append(replace(base, split=split, sample_id=split + menu,
                group=("mechanism", split, "boundary"), network=network))
    return values


class Client:
    def __init__(self, labels):
        self.labels = iter(labels)
        self.calls = []

    def select(self, network, *, run_id, trace_id):
        self.calls.append((run_id, trace_id))
        selected = next(self.labels)
        if isinstance(selected, Exception):
            raise selected
        return SimpleNamespace(selected_operation=selected, eligible_labels=network.eligible_labels,
            raw_record=lambda: {"mechanism_selected": selected}), SimpleNamespace(checkpoint_id=trace_id)


def test_evaluation_uses_production_vote_rule_and_keeps_failed_denominator(tmp_path):
    values = cases(tmp_path)
    client = Client(["read_json", "read_file", "read_json", "read_json", RuntimeError("HTTP fixture"), "read_json"])
    records = []
    result = api().evaluate_arm(values, client, run_id="mechanism", arm="zero", max_seconds=60, record=records.append)
    assert result["dev"]["menu_correct"] == 2 and result["dev"]["menu_total"] == 3
    assert result["dev"]["ensemble_correct"] == result["dev"]["ensemble_total"] == 1
    assert result["confirmation"]["menu_total"] == 3
    assert result["confirmation"]["transport_failures"] == 1
    assert result["confirmation"]["ensemble_correct"] == 0
    assert len(client.calls) == 6 and len(set(client.calls)) == 6
    assert any(row.get("error") == "HTTP fixture" for row in records)


def test_incomplete_menu_groups_are_reported_without_inventing_extra_calls(tmp_path):
    values = cases(tmp_path)[::3]
    client = Client(["read_json", "read_json"])
    result = api().evaluate_arm(values, client, run_id="mechanism", arm="zero", max_seconds=60, record=lambda r: None)
    assert len(client.calls) == 2
    assert result["dev"]["incomplete_menu_groups"] == 1
    assert result["dev"]["ensemble_total"] == 0 and result["dev"]["ensemble_accuracy"] is None


def test_budget_expiry_is_not_success_or_a_reduced_denominator(tmp_path):
    values = cases(tmp_path)
    moments = iter([0, 61, 61, 61, 61, 61, 61, 61])
    client = Client([])
    result = api().evaluate_arm(values, client, run_id="mechanism", arm="zero", max_seconds=60,
        record=lambda r: None, clock=lambda: next(moments, 61))
    assert not client.calls
    assert result["dev"]["not_run"] == result["dev"]["menu_total"] == 3
    assert result["dev"]["menu_accuracy"] == 0


def test_role_qualification_prefers_zero_on_tie_and_never_claims_agent_retention(tmp_path):
    values = cases(tmp_path)
    result = api().evaluate_arm(values, Client(["read_json"] * 6), run_id="mechanism", arm="zero",
        max_seconds=60, record=lambda r: None)
    compared = api().compare_arms({"zero": result, "candidate": result}, plan())
    assert compared["preferred_state"] == "zero" and compared["zero_qualified"] is True
    assert compared["retained"] is False and compared["agent_evaluation_status"] == "not_run"


def test_candidate_cannot_hide_a_regression_behind_equal_aggregate_accuracy(tmp_path):
    values = cases(tmp_path)
    zero = api().evaluate_arm(values, Client(["read_json", "read_file", "read_json"] * 2),
        run_id="mechanism", arm="zero", max_seconds=60, record=lambda r: None)
    candidate = api().evaluate_arm(values, Client(["read_file", "read_json", "read_json"] * 2),
        run_id="mechanism", arm="candidate", max_seconds=60, record=lambda r: None)
    compared = api().compare_arms({"zero": zero, "candidate": candidate}, plan(menu_accuracy=0.5))
    assert compared["candidate_qualified"] is False
    assert compared["regressions"]["dev"] == ["devcanonical"]


def test_changed_votes_cannot_hide_an_ensemble_regression(tmp_path):
    values = []
    for item in cases(tmp_path):
        network = NetworkSelectorInput.create(current_subtask=item.network.current_subtask,
            current_progress=item.network.current_progress, eligible_labels=("read_file", "read_json", "file_digest"),
            menu_order_id=item.network.menu_order_id)
        for index in range(2):
            values.append(replace(item, sample_id=item.sample_id + str(index),
                group=(*item.group[:2], str(index)), target="read_file", network=network))
    zero_labels = ["read_file", "read_file", "read_json", "read_json", "file_digest", "file_digest"] * 2
    candidate_labels = ["read_file", "read_file", "read_json", "read_json", "read_json", "file_digest"] * 2
    results = {}
    for arm, labels in (("zero", zero_labels), ("candidate", candidate_labels)):
        results[arm] = api().evaluate_arm(values, Client(labels), run_id="mechanism", arm=arm,
            max_seconds=60, record=lambda r: None)
    compared = api().compare_arms(results, plan(menu_accuracy=0.3, ensemble_accuracy=0.5))
    assert compared["regressions"]["dev"] == []
    assert compared["candidate_qualified"] is False
    assert len(compared["ensemble_regressions"]["dev"]) == 1


def test_failed_source_admission_has_an_immutable_evaluation_ledger(tmp_path, monkeypatch):
    import json
    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value) + "\n")
        return {"path": str(path), "sha256": core.sha256_file(path)}
    registration = {"schema_version": api().RUN_SCHEMA, "run_id": "MECHANISM-EVALUATION",
        "evaluation_registration": write("plan.json", plan()),
        "arms": {"zero": asdict(_settings(zero=True)), "candidate": asdict(_settings())},
        "ledger_root": str(tmp_path / "runs"), "source_manifest": {"path": "unavailable", "sha256": "a" * 64}}
    reference = write("evaluation.json", registration)
    def reject(*args, **kwargs):
        raise ValueError("source changed fixture")
    monkeypatch.setattr(api(), "verify_project_source", reject)
    output = tmp_path / "runs/MECHANISM-EVALUATION"
    with pytest.raises(ValueError, match="source changed"):
        api().run_evaluation(reference, output, source_root=tmp_path)
    before = (output / "RESULT.json").read_bytes()
    result = json.loads(before)
    assert result["status"] == "failed" and result["retained"] is False
    assert result["log_sha256"] == core.sha256_file(output / "events.jsonl")
    with pytest.raises(FileExistsError):
        api().run_evaluation(reference, output, source_root=tmp_path)
    assert (output / "RESULT.json").read_bytes() == before
