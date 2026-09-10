"""Optimizer/admission mechanism fixtures, never production role training data."""
from copy import deepcopy
import importlib
from types import SimpleNamespace

import pytest
import torch

from rwkv_lh import statetune_core as core


def api():
    return importlib.import_module("rwkv_lh.statetune_training")


class MechanismModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layout = SimpleNamespace(layers=2, heads=1, head_size=2)
        self.blocks = torch.nn.ModuleList([torch.nn.Module() for _ in range(2)])
        for block in self.blocks:
            block.att = torch.nn.Module()
            block.att.time_state = torch.nn.Parameter(torch.zeros(1, 2, 2))
        self.base = torch.nn.Parameter(torch.tensor([0.1, 0.4, -0.2, 0.7]))
        self.seen = []

    def forward(self, tokens):
        self.seen.append(tokens.detach().clone())
        state = sum(block.att.time_state.flatten() for block in self.blocks)
        return (self.base + state).expand(*tokens.shape, 4)


def rows():
    return [{"sample_id": str(i), "input_token_ids": [0, 1], "target_token_ids": target}
            for i, target in enumerate(([2], [3, 2], [1]))]


def config(**changes):
    return {"seed": 19, "epochs": 1, "gradient_accumulation": 2, "learning_rate": 0.01,
            "betas": [0.9, 0.999], "eps": 1e-8, "weight_decay": 0.0,
            "max_grad_norm": 1.0, "max_optimizer_steps": 10,
            "max_seconds": 120.0, "max_allocated_bytes": 10**9, **changes}


def test_actual_optimizer_updates_only_state_and_flushes_partial_accumulation():
    model = MechanismModel()
    original = model.base.detach().clone()
    records = []
    result = api().optimize_state(model, rows(), config(), context_tokens=8, record=records.append)
    assert result["optimizer_steps"] == 2
    assert result["samples_seen"] == 3
    assert result["status"] == "candidate"
    assert result["stop_reason"] == "registered_epochs_finished"
    assert torch.equal(model.base, original) and model.base.grad is None
    assert all(torch.count_nonzero(p) for p in core.state_parameters(model, layers=2).values())
    assert [r["optimizer_steps"] for r in records if r["event"] == "optimizer_step_completed"] == [1, 2]
    assert records[-1]["event"] == "optimization_stopped"


def test_accumulation_weights_target_tokens_and_has_no_recurrent_carry():
    model, reference = MechanismModel(), MechanismModel()
    inputs = rows()[:2]
    cfg = config(gradient_accumulation=2, max_grad_norm=1e9)
    api().optimize_state(model, inputs, cfg, context_tokens=8, record=lambda row: None)
    parameters = core.freeze_for_state_tuning(reference, layers=2)
    optimizer = torch.optim.AdamW(parameters.values(), lr=cfg["learning_rate"], betas=cfg["betas"],
                                 eps=cfg["eps"], weight_decay=0)
    batch = core.collate_samples(inputs, context_tokens=8)
    core.target_cross_entropy(reference(batch["input_ids"]), batch["labels"]).backward()
    optimizer.step()
    for name, value in core.state_parameters(model, layers=2).items():
        torch.testing.assert_close(value, parameters[name], rtol=0, atol=1e-7)
    assert all(tokens.shape[0] == 1 for tokens in model.seen)
    assert sorted(tokens.tolist()[0][:2] for tokens in model.seen) == [[0, 1], [0, 1]]


def test_step_budget_is_interruption_and_does_not_claim_epochs_finished():
    records = []
    result = api().optimize_state(MechanismModel(), rows(), config(max_optimizer_steps=1),
                                  context_tokens=8, record=records.append)
    assert result["optimizer_steps"] == 1
    assert result["samples_seen"] == 2
    assert result["status"] == "interrupted"
    assert result["stop_reason"] == "optimizer_step_budget"


def test_time_budget_before_step_records_zero_actual_optimizer_steps():
    moments = iter([0, 0, 0, 100, 100, 100, 100])
    result = api().optimize_state(MechanismModel(), rows(), config(max_seconds=1), context_tokens=8,
                                  record=lambda row: None, clock=lambda: next(moments, 100))
    assert result["optimizer_steps"] == 0
    assert result["status"] == "interrupted"
    assert result["stop_reason"] == "wall_time_budget"


def test_failed_backward_records_counts_and_never_steps():
    class Broken(MechanismModel):
        def forward(self, tokens):
            return super().forward(tokens) * float("nan")
    records = []
    with pytest.raises(ValueError, match="nonfinite"):
        api().optimize_state(Broken(), rows(), config(), context_tokens=8, record=records.append)
    assert records[-1]["status"] == "failed"
    assert records[-1]["optimizer_steps"] == 0


@pytest.mark.parametrize("key,value", [("epochs", 0), ("max_optimizer_steps", True),
    ("gradient_accumulation", 0), ("learning_rate", float("nan")),
    ("betas", [1, 0.9]), ("max_seconds", 0), ("max_allocated_bytes", -1)])
def test_invalid_registered_budget_rejected_before_model_call(key, value):
    model = MechanismModel()
    with pytest.raises(ValueError):
        api().optimize_state(model, rows(), config(**{key: value}), context_tokens=8, record=lambda row: None)
    assert not model.seen


def test_partial_or_wrong_state_cannot_be_reused(tmp_path):
    model = MechanismModel()
    values = {name: torch.ones_like(p).bfloat16() for name, p in core.state_parameters(model, layers=2).items()}
    path = tmp_path / "state.pth"
    torch.save(values, path)
    reference = {"path": str(path), "sha256": core.sha256_file(path)}
    api().initialize_state(model, reference)
    assert all(torch.all(p == 1) for p in core.state_parameters(model, layers=2).values())
    values.pop(next(iter(values)))
    torch.save(values, path)
    with pytest.raises(ValueError, match="key set"):
        api().initialize_state(model, {**reference, "sha256": core.sha256_file(path)})


def test_context_overflow_has_no_silent_truncation_or_optimizer_steps():
    model = MechanismModel()
    records = []
    with pytest.raises(ValueError, match="truncation"):
        api().optimize_state(model, rows(), config(), context_tokens=1, record=records.append)
    assert not model.seen
    assert records[-1]["optimizer_steps"] == 0


def test_candidate_manifest_is_not_a_frozen_training_dataset(tmp_path):
    import json
    from rwkv_lh.role_trace_artifacts import ARTIFACT_SCHEMA
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema": ARTIFACT_SCHEMA, "purpose": "audit_candidate_only", "status": "valid"}))
    with pytest.raises(ValueError, match="frozen role dataset"):
        api().admit_dataset({"path": str(path), "sha256": core.sha256_file(path)},
                            role="selector_intent", expected_regression="a" * 64,
                            model_sha256="b" * 64, context_tokens=16384, vocab_size=65536, bos_token_id=0)


def test_expired_budget_during_last_step_cannot_claim_candidate():
    current = [0.0]
    def record(row):
        if row["event"] == "optimizer_step_completed":
            current[0] = 2.0
    result = api().optimize_state(MechanismModel(), rows()[:1], config(max_seconds=1), context_tokens=8,
                                  record=record, clock=lambda: current[0])
    assert result["optimizer_steps"] == 1
    assert result["status"] == "interrupted"
    assert result["stop_reason"] == "wall_time_budget"


def test_numeric_compatibility_must_bind_the_exact_runtime_and_model():
    registration = {"runtime": {"sha256": "a" * 64}, "base_sha256": "b" * 64,
                    "context_tokens": 128, "source_manifest_sha256": "c" * 64}
    compatibility = {"purpose": "numerical_mechanism_only", "optimizer_steps": 0,
        "base_sha256": "b" * 64, "context_tokens": 128, "source_manifest_sha256": "c" * 64}
    result = {"passed": True, "optimizer_steps": 0, "runtime_sha256": "a" * 64,
              "registration_sha256": "d" * 64}
    api().validate_compatibility(registration, compatibility, result, registration_sha256="d" * 64)
    for changed in ({**result, "passed": False}, {**result, "runtime_sha256": "e" * 64}):
        with pytest.raises(ValueError, match="compatibility"):
            api().validate_compatibility(registration, compatibility, changed, registration_sha256="d" * 64)
    with pytest.raises(ValueError, match="compatibility"):
        api().validate_compatibility(registration, {**compatibility, "base_sha256": "f" * 64}, result,
                                     registration_sha256="d" * 64)


def test_failed_runtime_admission_retains_immutable_zero_step_run(tmp_path, monkeypatch):
    import json
    from rwkv_lh.goal_state_protocols import selector_intent_v6
    from rwkv_lh import statetune_native_runtime
    from test_statetune_evaluation import plan
    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value) + "\n")
        return {"path": str(path), "sha256": core.sha256_file(path)}
    evaluation = write("evaluation.json", plan())
    registration = {"schema_version": api().RUN_SCHEMA, "run_id": "MECHANISM-ADMISSION", "role": "selector_intent",
        "input_protocol": selector_intent_v6.INPUT_SCHEMA_VERSION,
        "protocol_sha256": core.sha256_file(selector_intent_v6.__file__), "optimizer": config(),
        "authorization": write("authorization.json", {"unit_test_only": True}),
        "evaluation_registration": evaluation, "regression_fingerprint": "a" * 64,
        "ledger_root": str(tmp_path / "runs"), "runtime": {"path": "unavailable", "sha256": "b" * 64},
        "source_manifest_sha256": "c" * 64}
    reference = write("registration.json", registration)
    def rejected(*args, **kwargs):
        raise ValueError("test runtime identity rejected")
    monkeypatch.setattr(statetune_native_runtime, "verify_native_runtime", rejected)
    output = tmp_path / "runs/MECHANISM-ADMISSION"
    with pytest.raises(ValueError, match="runtime identity rejected"):
        api().run_training(reference, output, source_root=tmp_path)
    report = json.loads((output / "RESULT.json").read_text())
    assert report["status"] == "failed" and report["optimizer_steps"] == 0
    assert report["retained"] is False
    assert report["log_sha256"] == core.sha256_file(output / "events.jsonl")
    assert core.sha256_file(output / "REGISTRATION.json") == reference["sha256"]
    before = (output / "RESULT.json").read_bytes()
    with pytest.raises(FileExistsError):
        api().run_training(reference, output, source_root=tmp_path)
    assert (output / "RESULT.json").read_bytes() == before


def test_candidate_export_uses_real_serving_loader_and_one_transpose(tmp_path):
    model = MechanismModel()
    with torch.no_grad():
        for index, parameter in enumerate(core.state_parameters(model, layers=2).values()):
            parameter.copy_(torch.arange(4).reshape(1, 2, 2) + index + 1)
    result = api().publish_state(model, tmp_path, profile_id="MECHANISM-CANDIDATE", model_artifact=str(tmp_path),
                                 engine_revision="f" * 40)
    assert result["profile_id"] == "MECHANISM-CANDIDATE"
    assert result["serving_loader_verified"] is True
    assert core.sha256_file(result["state"]["path"]) == result["state"]["sha256"]
    values = torch.load(result["state"]["path"], weights_only=True)
    for name, parameter in core.state_parameters(model, layers=2).items():
        assert torch.equal(values[name], parameter.bfloat16())
    assert core.sha256_file(result["manifest"]["path"]) == result["manifest"]["sha256"]
