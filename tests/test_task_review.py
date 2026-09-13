"""Outcome review is external to model protocols and uses hash-bound evidence."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from rwkv_lh import task_review as review


@pytest.fixture
def bundle(tmp_path):
    contract = {
        "schema": review.CONTRACT_SCHEMA, "task_id": "health",
        "user_request": "找到健康检查脚本，说明主要用途。",
        "kind": "task_trial", "protocol_error_policy": "feedback",
        "execution_identity": {k: review.digest(k) for k in review.IDENTITY_KEYS},
        "requirements": [
            {"id": "purpose", "user_quote": "说明主要用途", "outcome": "说明健康检查用途",
             "level": "essential", "missing_effect": "不能知道脚本的作用",
             "acceptance": "有用说明健康检查用途，不要求逐个实现细节",
             "omission_policy": "超时和关闭连接允许省略"},
            {"id": "timeout", "user_quote": "主要用途", "outcome": "超时细节",
             "level": "detail", "missing_effect": "不影响主要用途",
             "acceptance": "如果提到超时，应忠实", "omission_policy": "可省略"},
        ],
    }
    (tmp_path / "source.txt").write_text("health check source")
    run = {
        "schema": review.RUN_SCHEMA, "run_id": "run-1", "task_id": "health",
        "arm": "zero", "repeat": 1, "protocol_error_policy": "feedback",
        "execution_identity": contract["execution_identity"],
        "termination": "submitted", "answer": "检查健康状态。", "artifact_ids": [],
        "assistance": "rwkv_independent", "historical": False,
        "evidence": [{"id": "source", "path": "source.txt",
                      "sha256": review.file_digest(tmp_path / "source.txt"), "kind": "source"}],
        "diagnostics": {"model_calls": 2, "protocol_rejections": 0, "feedback_consumed": 0},
    }
    judged = {
        "schema": review.REVIEW_SCHEMA, "contract_sha256": review.digest(contract),
        "run_sha256": review.digest(run), "reviewer": "external reviewer",
        "validity_evidence_ids": ["source"], "validity": "valid", "validity_reason": "来源与任务一致",
        "requirements": [
            {"id": "purpose", "status": "met", "reason": "用途明确", "evidence_ids": ["source"]},
            {"id": "timeout", "status": "unmet", "reason": "未写可省略细节", "evidence_ids": ["source"]},
        ], "findings": [], "causes": [],
    }
    return contract, run, judged, tmp_path


def assess(bundle):
    return review.assess(*bundle[:3], evidence_root=bundle[3])


def rebind(bundle):
    bundle[2]["contract_sha256"] = review.digest(bundle[0])
    bundle[2]["run_sha256"] = review.digest(bundle[1])


def test_optional_detail_does_not_zero_a_useful_answer(bundle):
    assert assess(bundle)["outcome"] == "met"


def test_partial_quality_survives_without_binary_collapse(bundle):
    bundle[2]["requirements"][0]["status"] = "partial"
    result = assess(bundle)
    assert result["outcome"] == "partially_met"
    assert result["requirement_results"][0]["status"] == "partial"


def test_submitted_is_not_accepted_or_a_false_completion_claim(bundle):
    bundle[2]["requirements"][0]["status"] = "unmet"
    result = assess(bundle)
    assert result["delivered"] and result["outcome"] == "not_met"
    assert result["false_work_claims"] == 0


def test_budget_without_delivery_is_not_bad_summary_or_fabrication(bundle):
    bundle[1].update(answer=None, termination="budget")
    bundle[2]["requirements"] = []
    rebind(bundle)
    result = assess(bundle)
    assert result["outcome"] == "no_delivery"
    assert result["factuality"] == "not_applicable"


def test_recovered_errors_and_different_tool_routes_do_not_fail_delivery(bundle):
    bundle[1]["diagnostics"].update(protocol_rejections=1, feedback_consumed=1, model_calls=7, repeated_calls=2)
    rebind(bundle)
    assert assess(bundle)["outcome"] == "met"


@pytest.mark.parametrize("field", ["expected_tools", "exact_answer", "required_steps"])
def test_contract_rejects_unregistered_path_or_wording_gates(bundle, field):
    bundle[0][field] = ["search_text", "read_file"]
    with pytest.raises(ValueError, match="fields"):
        review.validate_contract(bundle[0])


def test_requirements_must_be_bound_to_user_request(bundle):
    bundle[0]["requirements"][0]["user_quote"] = "hidden reviewer preference"
    with pytest.raises(ValueError, match="user request"):
        review.validate_contract(bundle[0])


def test_first_error_stop_cannot_be_registered_as_full_task_trial(bundle):
    bundle[0]["protocol_error_policy"] = "stop"
    with pytest.raises(ValueError, match="boundary_probe"):
        review.validate_contract(bundle[0])
    bundle[0]["kind"] = "boundary_probe"
    review.validate_contract(bundle[0])


def test_fixture_invalidity_is_not_model_failure_or_denominator_shrink_hidden(bundle):
    bundle[2].update(validity="invalid", validity_reason="wrong fixture", requirements=[])
    result = assess(bundle)
    summary = review.aggregate([result])["arms"]["zero"]
    assert result["outcome"] == "invalid"
    assert summary["total"] == 1 and summary["valid"] == 0 and summary["invalid"] == 1


def test_missing_review_is_unreviewable_not_automatic_failure(bundle):
    bundle[2]["requirements"] = bundle[2]["requirements"][1:]
    assert assess(bundle)["outcome"] == "unreviewable"


def test_minor_unsupported_detail_is_separate_from_material_false_claim(bundle):
    bundle[2]["findings"] = [{"kind": "unsupported", "severity": "minor",
        "quote": "健康", "reason": "review demonstration", "impact": "minor wording",
        "evidence_ids": ["source"]}]
    assert assess(bundle)["outcome"] == "met"
    bundle[2]["findings"][0].update(kind="false_work_claim", severity="material", impact="misleads delivery verification")
    assert assess(bundle)["outcome"] == "not_met"
    assert assess(bundle)["false_work_claims"] == 1


def test_false_claim_requires_exact_delivered_quote_and_evidence(bundle):
    bundle[2]["findings"] = [{"kind": "false_work_claim", "severity": "material",
        "quote": "I passed hidden acceptance", "reason": "not actually said", "impact": "bad",
        "evidence_ids": ["source"]}]
    with pytest.raises(ValueError, match="delivered answer"):
        assess(bundle)


@pytest.mark.parametrize("change", ["answer", "contract", "evidence"])
def test_review_cannot_be_reused_after_input_answer_or_evidence_changes(bundle, change):
    if change == "answer":
        bundle[1]["answer"] += " changed"
    elif change == "contract":
        bundle[0]["requirements"][0]["acceptance"] += " changed"
    else:
        (bundle[3] / "source.txt").write_text("changed")
    with pytest.raises(ValueError, match="digest|checksum"):
        assess(bundle)


def test_evidence_cannot_escape_review_root(bundle):
    bundle[1]["evidence"][0]["path"] = "../source.txt"
    rebind(bundle)
    with pytest.raises(ValueError, match="evidence path"):
        assess(bundle)


def test_causal_hypothesis_cannot_be_presented_as_proven_root_cause(bundle):
    bundle[2]["causes"] = [{"category": "harness_input", "certainty": "hypothesis",
        "reason": "menu may interfere", "evidence_ids": ["source"]}]
    assert assess(bundle)["confirmed_root_causes"] == []


def test_aggregation_keeps_assistance_attribution_and_rejects_duplicates(bundle):
    bundle[1]["assistance"] = "strong_takeover"
    rebind(bundle)
    result = assess(bundle)
    assert review.aggregate([result])["arms"]["zero"]["attribution"]["strong_takeover"]["met"] == 1
    with pytest.raises(ValueError, match="duplicate"):
        review.aggregate([result, result])


def test_quality_gate_checks_the_whole_registered_grid(bundle):
    result = assess(bundle)
    assert not review.quality_gate([result], task_ids=["health"], repeats=2, arm="zero")["passed"]
    assert review.quality_gate([result], task_ids=["health"], repeats=1, arm="zero")["passed"]


def test_ceiling_is_inconclusive_comparison_not_candidate_quality_failure():
    result = review.compare_counts(baseline_met=7, candidate_met=8, total=8, required_gain=2)
    assert result["comparison"] == "ceiling_limited"
    assert result["candidate_quality_met"] == 8


def test_historical_review_never_counts_as_new_gain(bundle):
    bundle[0]["kind"] = "retrospective"
    bundle[1]["historical"] = True
    rebind(bundle)
    result = assess(bundle)
    assert not result["eligible_for_gain"]
    assert not review.quality_gate([result], task_ids=["health"], repeats=1, arm="zero")["passed"]


def test_frozen_contract_and_assessment_files_cannot_be_overwritten(bundle):
    path = bundle[3] / "contract.json"
    review.freeze_contract(bundle[0], path)
    with pytest.raises(FileExistsError):
        review.freeze_contract(bundle[0], path)
    assert review.load_contract(path) == bundle[0]
    value = json.loads(path.read_text())
    value["contract"]["user_request"] += " mutated"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="digest"):
        review.load_contract(path)


def test_real_diagnostic_capture_preserves_answer_and_classifies_stop_scope(tmp_path):
    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root / "data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913/DEV_RESULTS.json").read_text())
    row = next(r for r in rows if r["final"] is not None)
    (tmp_path / "RESULT.json").write_text(json.dumps(row))
    # A result alone is not proof of a model-origin answer.
    with pytest.raises(ValueError, match="trace"):
        review.capture_diagnostic_run(tmp_path, task_id="smoke", arm="readonly", repeat=2,
            protocol_error_policy="stop", execution_identity={k: review.digest(k) for k in review.IDENTITY_KEYS}, historical=True, assistance="rwkv_independent")


def test_excluding_a_run_requires_registered_evidence(bundle):
    bundle[2]['validity'] = 'invalid'
    bundle[2]['validity_evidence_ids'] = []
    with pytest.raises(ValueError, match='evidence'):
        assess(bundle)


def test_capture_requires_committed_final_and_explicit_attribution(tmp_path):
    import tarfile
    root = Path(__file__).resolve().parents[1]
    archive = root / 'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913/EVIDENCE.tar.gz'
    with tarfile.open(archive) as tar:
        for name in ('RESULT.json', 'model_trace.jsonl'):
            member = next(m for m in tar.getmembers() if m.name.endswith('dev/smoke-readonly-r2/' + name))
            (tmp_path / name).write_bytes(tar.extractfile(member).read())
    args = dict(task_id='smoke', arm='readonly', repeat=2, protocol_error_policy='stop',
                execution_identity={k: review.digest(k) for k in review.IDENTITY_KEYS},
                historical=True, assistance='rwkv_independent')
    run = review.capture_diagnostic_run(tmp_path, **args)
    assert run['answer'] == json.loads((tmp_path / 'RESULT.json').read_text())['final']
    events = [json.loads(s) for s in (tmp_path / 'model_trace.jsonl').read_text().splitlines()]
    (tmp_path / 'model_trace.jsonl').write_text('\n'.join(json.dumps(e) for e in events
        if e['type'] != 'model_session_candidate_committed'))
    with pytest.raises(ValueError, match='delivery'):
        review.capture_diagnostic_run(tmp_path, **args)


def test_cli_revalidates_evidence_and_never_overwrites(bundle):
    import subprocess
    import sys
    contract, run, judgment, root = bundle
    review.freeze_contract(contract, root / 'contract.json')
    for name, value in [('run', run), ('judgment', judgment)]:
        (root / f'{name}.json').write_text(json.dumps(value))
    job = dict(contract='contract.json', run='run.json', judgment='judgment.json', evidence_root='.')
    (root / 'job.json').write_text(json.dumps({'reviews': [job]}))
    cli = Path(__file__).resolve().parents[1] / 'scripts/review_agent_task.py'
    args = [sys.executable, str(cli), 'aggregate', '--input', str(root/'job.json'), '--output', str(root/'out.json')]
    assert subprocess.run(args, capture_output=True).returncode == 0
    assert json.loads((root/'out.json').read_text())['arms']['zero']['met'] == 1
    assert subprocess.run(args, capture_output=True).returncode == 2
    (root/'source.txt').write_text('changed')
    args[-1] = str(root/'out2.json')
    result = subprocess.run(args, capture_output=True)
    assert result.returncode == 2 and b'checksum' in result.stderr
