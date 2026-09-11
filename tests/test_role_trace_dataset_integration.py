"""Controller/Harness integration with mock model decisions, never training data.

The test uses the production artifact shape to verify extraction code. Explicit
zero identities and token IDs belong to fake transports; they establish no model
capability or production provenance. All generated files stay in pytest storage.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import gzip
import hashlib
import json
from json import loads as decode_json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from rwkv_lh.exact_tool_selector.native_network_protocol import NativeNetworkToolSelection
from rwkv_lh.goal_state_protocols import selector_intent_v7
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import (
    DatasetIntegrityError, EQUIVALENCE_WAIVER_SCHEMA, NON_WAIVABLE_PATHS, ROLE_MODULES,
    SOURCE_CODE_PATHS, extract_registration, extract_source, load_source_run,
    read_equivalence_waiver, register_case,
)
from rwkv_lh.model_session import ModelSession
from rwkv_lh.role_trace_stages import LANE_ROLES
from rwkv_lh.schema import RunState
from rwkv_lh.stateful_goal_loop import STATEFUL_GOAL_LOOP_ARCHITECTURE
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.token_budget import tokenizer
from scripts.run_rwkv_e2e_benchmark import _causal_ledger, _state_timeline
from test_role_trace_inputs import controller_role_snapshots  # noqa: F401


def _write_json(path: Path, value):
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(gzip.compress(encoded, mtime=0) if path.suffix == ".gz" else encoded)


@pytest.fixture
def mock_controller_case(tmp_path, monkeypatch, request):
    import test_stateful_goal_loop as fixtures

    native = getattr(request, "param", "prompt_replay") == "native_rwkv"
    failed_audit = getattr(request, "param", "") == "failed_step"
    role_stage = getattr(request, "param", "") == "role_stage"
    trace = []
    original_init = ModelSession.__init__
    original_queue = fixtures._QueueClient
    original_completion = fixtures._QueueClient.text_completion
    original_selector = fixtures._selector
    original_post = fixtures._SelectorHTTP.post

    def session_init(self, client=None, *, settings=None, audit_hook=None):
        assert settings is not None  # This test never creates a real runtime.
        configured = replace(settings, state_profile_id="zero", state_profile_sha256="0" * 64)
        original_init(self, client, settings=configured, audit_hook=trace.append)

    def completion(self, *args, **kwargs):
        response = original_completion(self, *args, **kwargs)
        if failed_audit:
            command = decode_json(response.content)
            if command["function"] == "audit_decision" and command["params"]["step_id"] == "S1":
                from rwkv_lh.goal_state_protocols import auditor_step_v7
                command["params"].update(verdict="repair", step_complete=False,
                    gaps=sorted(["write_root_unproved:result.txt", "phase_evidence_unproved:mutate"]),
                    reason="The current step still lacks the required evidence.")
                response.content = json.dumps(command, ensure_ascii=False)
        response.metadata = {"token_ids": tokenizer().encode(response.content)}
        response.model = self.model_name
        return response

    def selector(operations):
        selected = original_selector(operations)
        selected.settings = replace(
            selected.settings, state_profile_id="verified-selector" if role_stage else "zero",
            state_profile_sha256=("a" if role_stage else "0") * 64,
            state_profile_manifest_sha256="0" * 64,
        )
        selected._session.settings = selected.settings
        return selected

    def post(self, url, *, json, timeout):
        response = original_post(self, url, json=json, timeout=timeout)
        wire = decode_json(response.content)
        selected = NativeNetworkToolSelection.from_dict(wire["selection"])
        # Use the current production prefix constant and actual local vocabulary.
        # The logits are explicitly deterministic mock decisions.
        suffixes = {
            label: tokenizer().encode(selector_intent_v7.TARGET_PREFIX + label)
            for label in selected.eligible_labels
        }
        selected_ids = suffixes[selected.selected_operation]
        decisions = []
        for position, chosen in enumerate(selected_ids):
            prefix = selected_ids[:position]
            allowed = sorted({ids[position] for ids in suffixes.values()
                              if len(ids) > position and ids[:position] == prefix})
            decisions.append({
                "position": position, "allowed_token_ids": allowed,
                "allowed_token_logits": {str(token): 10.0 if token == chosen else 0.0 for token in allowed},
                "chosen_token_id": chosen, "chosen_token_logit": 10.0,
                "chosen_vs_runner_up_margin": None if len(allowed) == 1 else 10.0,
            })
        token_count = len(tokenizer().encode(json["bootstrap"] + "\n" + json["step"]))
        selected = replace(selected, input_token_count=token_count, decoder_trace={
            **selected.decoder_trace, "prompt_token_count": token_count,
            "token_ids": selected_ids, "decisions": decisions,
        })
        wire["selection"] = selected.raw_record()
        return fixtures._SelectorResponse(wire)

    monkeypatch.setattr(ModelSession, "__init__", session_init)
    monkeypatch.setattr(fixtures._QueueClient, "text_completion", completion)
    monkeypatch.setattr(fixtures, "_selector", selector)
    monkeypatch.setattr(fixtures._SelectorHTTP, "post", post)
    if native:
        import rwkv_lh.model as model_module
        import rwkv_lh.model_session as session_module
        from rwkv_lh.model_session import NativeRWKVModelSession
        from test_role_trace_context import STOP, TokenNativeClient

        clients = []

        def native_queue(outputs, **kwargs):
            queued = original_queue(outputs, **kwargs)
            # Reuse the mock completion's production command normalization.
            canonical_outputs = [original_completion(queued, "").content for _ in outputs]
            client = TokenNativeClient([output + STOP for output in canonical_outputs])
            client.model_name = queued.model_name
            clients.append(client)
            return client

        def native_session(client=None, *, settings=None, audit_hook=None):
            assert settings is not None and (client is not None or clients)
            return NativeRWKVModelSession(
                client if client is not None else clients[0],
                settings=replace(settings, state_transport="native_rwkv"),
                audit_hook=trace.append,
            )

        monkeypatch.setattr(fixtures, "_QueueClient", native_queue)
        # The imported Controller fixture chooses its actual session here;
        # isolated role sessions share only the fake backend, not a State lane.
        monkeypatch.setattr(session_module, "ModelSession", native_session)
        monkeypatch.setattr(model_module, "create_model_session", native_session)
    snapshots, final = request.getfixturevalue("controller_role_snapshots")
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    events = store.event_records(final.run_id)
    timeline = _state_timeline(store, final.run_id)
    ledger = _causal_ledger(trace, events, timeline, final)
    frozen_root = tmp_path / "mock_frozen_run"
    case_root = frozen_root / "cases" / final.run_id
    (case_root / "state").mkdir(parents=True)
    # Freeze the live WAL-backed store into a standalone SQLite artifact.
    source_connection = sqlite3.connect(store.database_path.as_uri() + "?mode=ro", uri=True)
    target_connection = sqlite3.connect(case_root / "state" / "long_horizon.db")
    try:
        source_connection.backup(target_connection)
    finally:
        source_connection.close()
        target_connection.close()
    for name, value in (
        ("model_trace.json", trace), ("event_log.json", events),
        ("state_timeline.json.gz", timeline), ("causal_ledger.json", ledger),
    ):
        _write_json(case_root / name, value)
    repository = Path(__file__).resolve().parents[1]
    source_paths = {repository / path for path in SOURCE_CODE_PATHS}
    source_manifest = [{
        "path": str(path.relative_to(repository)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    } for path in sorted(source_paths)]
    _write_json(frozen_root / "source_tree_manifest.json", source_manifest)
    manifest_sha = hashlib.sha256(json.dumps(
        source_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    _write_json(frozen_root / "RUN_PROTOCOL.json", {
        "schema_version": "rwkv-lh.round-run-protocol.v1",
        "round": "MOCK-CODE-ONLY", "architecture": STATEFUL_GOAL_LOOP_ARCHITECTURE,
        "selected_case_ids": [final.run_id], "selected_case_count": 1,
        "source_resources": [{
            "suite": "controller_mock_code_verification", "role": "visible_tasks",
            "path": "mock-development-scope", "sha256": hashlib.sha256(b"MOCK-CODE-ONLY").hexdigest(),
        }],
        "code": {"source_tree_manifest_sha256": manifest_sha},
        **({"role_data_collection": {
            "mode": "role_stage", "stage_id": "MOCK-EXECUTOR-STAGE", "target_role": "executor_args",
            "profiles": {LANE_ROLES[cp.lane_kind.value]: {
                "profile_id": cp.state_profile_id, "profile_sha256": cp.state_profile_sha256,
                "model_sha256": cp.native_state_metadata["model_sha256"],
            } for cp in final.model_states.values()},
        }} if role_stage else {}),
    })
    registration = register_case(
        case_root, run_id=final.run_id, source_run_id="MOCK-CODE-ONLY",
        project_family="mock-controller-integration-only", suite="controller_mock_code_verification",
    )
    registration_path = case_root / "mock_code_registration.json"
    _write_json(registration_path, registration)
    return {
        "root": case_root, "snapshots": snapshots, "final": final,
        "model_trace": trace, "event_log": events, "timeline": timeline, "ledger": ledger,
        "registration": registration, "registration_path": registration_path,
    }


def _load(case):
    return load_source_run(case["registration"]["source_runs"][0], base_dir=case["root"])


def _mock_reviews(row, *, target=None):
    """Explicitly fake reviewers for code tests, never production label authority."""
    selected = row["target_text"] if target is None else target
    bound = {key: row[key] for key in ("source_run_id", "run_id", "request_id", "role",
                                      "boundary_event_id", "original_output_record_sha256")}
    return [{**bound, "reviewer_id": reviewer, "decision": "accept",
             "purpose": "semantic_label" if target is None else "trace_correction",
             "input_sha256": hashlib.sha256(row["input_text"].encode()).hexdigest(),
             "target_sha256": hashlib.sha256(selected.encode()).hexdigest(),
             "target_text": selected, "evidence_refs": row["available_evidence_refs"],
             "rationale": "MOCK review of Controller code fixture; not a real human review."}
            for reviewer in ("MOCK-REVIEWER-ONE", "MOCK-REVIEWER-TWO")]


def _with_mock_audit_reviews(source):
    _, excluded = extract_source(source, roles=["auditor_step", "auditor_final", "finalizer_answer"])
    return replace(source, reviews=[review for item in excluded
                                   for review in _mock_reviews(item["review_candidate"])])


def test_kernel_acceptance_does_not_grant_auditor_semantic_label_authority(mock_controller_case):
    source = replace(_load(mock_controller_case), reviews=[])
    samples, excluded = extract_source(source, roles=["auditor_step"])
    assert samples == []
    assert len(excluded) == 1
    candidate = excluded[0]["review_candidate"]
    assert candidate["role"] == "auditor_step"
    assert candidate["label_authority"] == "pending_human_review"
    assert candidate["input_text"] and candidate["raw_output_token_ids"]


def test_review_approval_cannot_replace_missing_executor_execution(mock_controller_case, monkeypatch):
    from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as pipeline

    source = _load(mock_controller_case)
    samples, _ = extract_source(source, roles=["executor_args"])
    request_id = samples[0]["request_id"]
    state_without_execution = deepcopy(source.final_state)
    state_without_execution.actions = {}
    source = replace(source, final_state=state_without_execution,
                     reviews=[{"role": "executor_args", "request_id": request_id}])
    # Isolate the execution invariant from independent human review validation:
    # even a positive review service result cannot manufacture a Harness action.
    monkeypatch.setattr(pipeline, "_review_authority", lambda *args: ["MOCK-ONE", "MOCK-TWO"])
    rows, excluded = extract_source(source, roles=["executor_args"])
    assert rows == []
    assert any("missing actual Executor execution" in item["reason"] for item in excluded)


@pytest.mark.parametrize(("mock_controller_case", "controller_role_snapshots"), [("failed_step", 3)], indirect=True)
def test_failed_run_supplies_reviewed_correction_without_later_roles(mock_controller_case, controller_role_snapshots):
    from rwkv_lh.model_io import ModelCommand, parse_model_command
    source = _load(mock_controller_case)
    assert source.final_state.status.value == "interrupted"
    samples, excluded = extract_source(source, roles=["auditor_step"])
    assert samples == []
    row = excluded[0]["review_candidate"]
    command = parse_model_command(row["original_target_text"])
    corrected = dict(command.arguments)
    corrected["gaps"] = ["phase_evidence_unproved:mutate"]
    target = ModelCommand(command.name, corrected).canonical
    reviewed = replace(source, reviews=_mock_reviews(row, target=target))
    samples, excluded = extract_source(reviewed, roles=["auditor_step"])
    assert not excluded and len(samples) == 1
    sample = samples[0]
    assert sample["input_text"] == row["input_text"]
    assert sample["target_text"] == target
    assert sample["target_origin"] == "human_trace_correction"
    assert sample["raw_output"] == row["raw_output"]
    assert sample["raw_output_token_ids"] == row["raw_output_token_ids"]
    assert sample["target_token_ids"] == tokenizer().encode(target)
    assert sample["target_token_ids_source"] == "local_tokenizer_for_reviewed_target"
    assert not source.final_state.final_output
    reviewed.reviews[1]["original_output_record_sha256"] = "f" * 64
    with pytest.raises(DatasetIntegrityError, match="original_output_record"):
        extract_source(reviewed, roles=["auditor_step"])


@pytest.mark.parametrize("mock_controller_case", ["role_stage"], indirect=True)
def test_executor_stage_collects_with_frozen_tuned_selector(mock_controller_case):
    source = _load(mock_controller_case)
    assert source.collection_contract["target_role"] == "executor_args"
    samples, excluded = extract_source(source, roles=["executor_args"])
    assert not excluded and len(samples) == 1
    assert samples[0]["context"]["initial_state"]["state_profile_id"] == "zero"
    with pytest.raises(DatasetIntegrityError, match="frozen target role"):
        extract_source(source, roles=["selector_intent"])


def _replace_artifact(case, name, value):
    artifact = case["registration"]["source_runs"][0]["artifacts"][name]
    path = Path(artifact["path"])
    _write_json(path, value)
    artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


def test_mock_controller_exports_can_rebuild_all_five_role_paths(mock_controller_case):
    case = mock_controller_case
    samples, excluded = extract_source(_with_mock_audit_reviews(_load(case)))
    assert not excluded
    assert {sample["role"] for sample in samples} == set(ROLE_MODULES)
    assert len([sample for sample in samples if sample["role"] == "selector_intent"]) == 3
    assert all(sample["source_run_id"] == "MOCK-CODE-ONLY" for sample in samples)
    assert all(sample["context"]["token_ids_complete"] is False for sample in samples)


@pytest.mark.parametrize("mock_controller_case", ["native_rwkv"], indirect=True)
def test_native_mock_controller_exports_rebuild_five_roles_with_original_stop_tokens(mock_controller_case):
    from test_role_trace_context import STOP

    source = _with_mock_audit_reviews(_load(mock_controller_case))
    samples, excluded = extract_source(source)
    assert not excluded
    assert {sample["role"] for sample in samples} == set(ROLE_MODULES)
    for sample in samples:
        if sample["role"] == "selector_intent":
            continue
        assert sample["context"]["transport"] == "native_rwkv"
        assert sample["context"]["token_ids_complete"] is False
        original_stream = tokenizer().decode_bytes(sample["raw_output_token_ids"]).decode("utf-8")
        assert original_stream == sample["target_text"]
        assert original_stream == sample["raw_output"]["raw_output"] + STOP
        assert sample["context"]["initial_state"]["state_profile_id"] == "zero"
        assert sample["context"]["segments"]
        # Isolated Auditor and Finalizer sessions discard their candidate State
        # after recording output; only the continuing Executor commits it.
        expected_outcome = "committed" if sample["role"] == "executor_args" else "rolled_back"
        assert sample["context"]["generation_evidence"]["outcome"] == expected_outcome


@pytest.mark.parametrize("source_kind", ["fixture", "authored_reference"])
def test_mock_or_reference_provenance_cannot_supply_real_training_sources(mock_controller_case, source_kind):
    case = mock_controller_case
    record = deepcopy(case["registration"]["source_runs"][0])
    record["source_kind"] = source_kind
    with pytest.raises(DatasetIntegrityError, match="production_trace"):
        load_source_run(record, base_dir=case["root"])


def test_single_mock_case_exports_only_an_invalid_coverage_audit(mock_controller_case):
    case = mock_controller_case
    output = case["root"] / "incomplete_coverage_audit"
    manifest = extract_registration(case["registration_path"], output)
    assert manifest["status"] == "invalid"
    assert manifest["quality_gates"]["required_coverage_per_role"] is False
    assert manifest["provenance"]["output_kind"] == "candidate_audit_only"
    assert manifest["provenance"]["training_started"] is False
    assert manifest["provenance"]["formal_dataset_version_created"] is False
    assert "regression_candidate.json" not in manifest["files"]
    assert "review_queue.jsonl" in manifest["files"]
    queue = [decode_json(line) for line in (output / "review_queue.jsonl").read_text().splitlines()]
    assert {row["role"] for row in queue} == {"auditor_step", "auditor_final", "finalizer_answer"}
    assert all(row["label_authority"] == "pending_human_review" for row in queue)


def test_focused_scope_must_be_pinned_in_source_before_it_can_relax_coverage(mock_controller_case):
    case = mock_controller_case
    scope_path = case["root"] / "coverage_scope.json"
    _write_json(scope_path, {"schema_version": "rwkv-lh.role-trace-coverage-scope.v1",
                            "objective": "MOCK tool choice at missing targets", "requirements": {"selector_intent": ["missing_target"]}})
    scope_sha = hashlib.sha256(scope_path.read_bytes()).hexdigest()
    case["registration"]["coverage_scope"] = {"path": str(scope_path), "sha256": scope_sha}
    _write_json(case["registration_path"], case["registration"])
    with pytest.raises(DatasetIntegrityError, match="not pinned"):
        extract_registration(case["registration_path"], case["root"] / "unpinned_scope", roles=["selector_intent"])
    record = case["registration"]["source_runs"][0]
    protocol = decode_json(Path(record["artifacts"]["run_protocol"]["path"]).read_text())
    protocol["role_data_scope_sha256"] = scope_sha
    _replace_artifact(case, "run_protocol", protocol)
    _write_json(case["registration_path"], case["registration"])
    result = extract_registration(case["registration_path"], case["root"] / "pinned_scope", roles=["selector_intent"])
    assert result["quality_gates"]["required_coverage_per_role"] is True
    assert result["quality_gates"]["requested_roles_present"] is True
    assert result["coverage_audit"]["selector_intent"]["execute"] == 0
    assert result["status"] == "invalid"  # one family cannot supply three splits


WAIVER_TARGET = "rwkv_lh/harness.py"


def _stale_frozen_manifest(case):
    """Rewrite the frozen manifest so one file's frozen SHA differs from disk.

    This simulates a production fix landing after the trace was frozen: the
    manifest keeps the old (fake) digest while the working tree has the real
    bytes. All pinned artifact hashes are re-sealed so only the whole-tree
    scope check can object.
    """
    record = case["registration"]["source_runs"][0]
    manifest_path = Path(record["artifacts"]["source_tree_manifest"]["path"])
    manifest = decode_json(manifest_path.read_text())
    frozen_sha = hashlib.sha256(b"MOCK-PREVIOUS-FROZEN-BYTES").hexdigest()
    for item in manifest:
        if item["path"] == WAIVER_TARGET:
            item["sha256"] = frozen_sha
    _replace_artifact(case, "source_tree_manifest", manifest)
    protocol_path = Path(record["artifacts"]["run_protocol"]["path"])
    protocol = decode_json(protocol_path.read_text())
    protocol["code"]["source_tree_manifest_sha256"] = hashlib.sha256(json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    _replace_artifact(case, "run_protocol", protocol)
    repository = Path(__file__).resolve().parents[1]
    current_sha = hashlib.sha256((repository / WAIVER_TARGET).read_bytes()).hexdigest()
    return frozen_sha, current_sha


def _waiver_document(entries, *, reviewers=("MOCK-REVIEWER-ONE", "MOCK-REVIEWER-TWO"), decision="accept"):
    return {"schema_version": EQUIVALENCE_WAIVER_SCHEMA, "decision": decision,
            "reviewers": list(reviewers), "entries": entries}


def _waiver_entry(path, frozen_sha, current_sha):
    return {"path": path, "frozen_sha256": frozen_sha, "current_sha256": current_sha,
            "rationale": "MOCK waiver for code tests; not a real human review.",
            "evidence_refs": ["data/experiments/MOCK_EVIDENCE_R0_00000000/REPORT.md"]}


def _write_waiver(tmp_dir, document):
    path = tmp_dir / "equivalence_waiver.json"
    _write_json(path, document)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_scope_change_rejected_without_exactly_pinned_waiver(mock_controller_case):
    case = mock_controller_case
    frozen_sha, current_sha = _stale_frozen_manifest(case)
    record = case["registration"]["source_runs"][0]
    with pytest.raises(DatasetIntegrityError, match="implementation differs"):
        load_source_run(record, base_dir=case["root"])
    # A waiver pinning the wrong frozen digest does not relax the scope check.
    wrong = {WAIVER_TARGET: (hashlib.sha256(b"MOCK-OTHER-BYTES").hexdigest(), current_sha)}
    with pytest.raises(DatasetIntegrityError, match="implementation differs"):
        load_source_run(record, base_dir=case["root"], equivalence_waiver=wrong)
    # Same for a waiver pinning a current digest that is not the working tree.
    stale = {WAIVER_TARGET: (frozen_sha, hashlib.sha256(b"MOCK-OTHER-BYTES").hexdigest())}
    with pytest.raises(DatasetIntegrityError, match="implementation differs"):
        load_source_run(record, base_dir=case["root"], equivalence_waiver=stale)
    exact = {WAIVER_TARGET: (frozen_sha, current_sha)}
    source = load_source_run(record, base_dir=case["root"], equivalence_waiver=exact)
    assert source.waived_paths == (WAIVER_TARGET,)
    # The waived source still passes the full extraction defenses unchanged.
    samples, excluded = extract_source(_with_mock_audit_reviews(source))
    assert not excluded
    assert {sample["role"] for sample in samples} == set(ROLE_MODULES)


def test_unwaived_sources_load_with_empty_waived_paths(mock_controller_case):
    source = _load(mock_controller_case)
    assert source.waived_paths == ()


def test_waiver_document_review_and_entry_constraints(mock_controller_case, tmp_path):
    frozen_sha = hashlib.sha256(b"MOCK-PREVIOUS-FROZEN-BYTES").hexdigest()
    current_sha = hashlib.sha256(b"MOCK-CURRENT-BYTES").hexdigest()
    good_entry = _waiver_entry(WAIVER_TARGET, frozen_sha, current_sha)
    path, sha = _write_waiver(tmp_path, _waiver_document([good_entry]))
    assert read_equivalence_waiver(path, sha) == {WAIVER_TARGET: (frozen_sha, current_sha)}
    rejected = [
        (_waiver_document([good_entry], decision="reject"), "not an accepted review"),
        (_waiver_document([good_entry], reviewers=("MOCK-REVIEWER-ONE",)), "two distinct reviewers"),
        (_waiver_document([good_entry], reviewers=("MOCK-SAME", "MOCK-SAME ")), "two distinct reviewers"),
        (_waiver_document([]), "no entries"),
        (_waiver_document([good_entry, good_entry]), "duplicate waiver entry"),
        (_waiver_document([_waiver_entry(WAIVER_TARGET, frozen_sha, frozen_sha)]), "distinct frozen/current"),
        (_waiver_document([{**good_entry, "rationale": " "}]), "rationale"),
        (_waiver_document([{**good_entry, "evidence_refs": []}]), "evidence refs"),
        ({**_waiver_document([good_entry]), "schema_version": "other.v1"}, "unsupported"),
    ]
    for index, (document, match) in enumerate(rejected):
        bad_path = tmp_path / f"bad_waiver_{index}.json"
        _write_json(bad_path, document)
        with pytest.raises(DatasetIntegrityError, match=match):
            read_equivalence_waiver(bad_path, hashlib.sha256(bad_path.read_bytes()).hexdigest())


def test_waiver_can_never_cover_vocabulary_protocols_or_unknown_paths(mock_controller_case, tmp_path):
    frozen_sha = hashlib.sha256(b"MOCK-PREVIOUS-FROZEN-BYTES").hexdigest()
    current_sha = hashlib.sha256(b"MOCK-CURRENT-BYTES").hexdigest()
    assert NON_WAIVABLE_PATHS <= set(SOURCE_CODE_PATHS)
    # role_trace_* helpers are outside the frozen scope entirely; a waiver
    # naming them (or any unknown path) is rejected as unknown.
    for target in sorted(NON_WAIVABLE_PATHS) + ["rwkv_lh/role_trace_inputs.py", "unrelated/path.py"]:
        document = _waiver_document([_waiver_entry(target, frozen_sha, current_sha)])
        bad_path = tmp_path / (target.replace("/", "_") + ".json")
        _write_json(bad_path, document)
        with pytest.raises(DatasetIntegrityError, match="cannot cover this path"):
            read_equivalence_waiver(bad_path, hashlib.sha256(bad_path.read_bytes()).hexdigest())


def test_waived_extraction_records_waiver_provenance(mock_controller_case, tmp_path):
    case = mock_controller_case
    frozen_sha, current_sha = _stale_frozen_manifest(case)
    _write_json(case["registration_path"], case["registration"])
    with pytest.raises(DatasetIntegrityError, match="both the reviewed document"):
        extract_registration(case["registration_path"], case["root"] / "waiver_missing_pin",
                             equivalence_waiver={WAIVER_TARGET: (frozen_sha, current_sha)})
    path, sha = _write_waiver(tmp_path, _waiver_document([_waiver_entry(WAIVER_TARGET, frozen_sha, current_sha)]))
    waiver = read_equivalence_waiver(path, sha)
    manifest = extract_registration(case["registration_path"], case["root"] / "waived_audit",
                                    equivalence_waiver=waiver, equivalence_waiver_sha256=sha)
    assert manifest["provenance"]["equivalence_waiver_sha256"] == sha
    assert manifest["provenance"]["waived_paths"] == [WAIVER_TARGET]
    with pytest.raises(DatasetIntegrityError, match="implementation differs"):
        extract_registration(case["registration_path"], case["root"] / "unwaived_audit")


def test_frozen_artifact_sha_rejects_post_registration_edit(mock_controller_case):
    case = mock_controller_case
    path = case["root"] / "model_trace.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(DatasetIntegrityError, match="SHA mismatch"):
        _load(case)


def test_source_suite_cannot_be_relabelled_outside_frozen_scope(mock_controller_case):
    case = mock_controller_case
    record = deepcopy(case["registration"]["source_runs"][0])
    record["suite"] = "different_development_scope"
    with pytest.raises(DatasetIntegrityError, match="scope|suite"):
        load_source_run(record, base_dir=case["root"])


@pytest.mark.parametrize("artifact", ["event_log", "state_timeline", "causal_ledger"])
def test_rehashed_exports_still_must_match_authoritative_sqlite(mock_controller_case, artifact):
    case = mock_controller_case
    value = deepcopy(case[{"event_log": "event_log", "state_timeline": "timeline", "causal_ledger": "ledger"}[artifact]])
    if artifact == "event_log":
        value[-1]["data"]["untrusted_future_fact"] = "forged"
    elif artifact == "state_timeline":
        value[-1]["state_sha256"] = "0" * 64
    else:
        value["causal_events"].reverse()
    _replace_artifact(case, artifact, value)
    with pytest.raises(DatasetIntegrityError, match="mismatch|recomputed|differs"):
        _load(case)


def test_future_snapshot_poisoning_rejected_even_after_rehashing_all_exports(mock_controller_case):
    case = mock_controller_case
    artifact = case["registration"]["source_runs"][0]["artifacts"]["sqlite"]
    path = Path(artifact["path"])
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        older = connection.execute("SELECT revision FROM checkpoints ORDER BY revision LIMIT 1 OFFSET 1").fetchone()[0]
        poisoned = case["final"].to_dict()
        poisoned["revision"] = older
        connection.execute("UPDATE checkpoints SET state_json=? WHERE revision=?", (LongHorizonStore._serialize(poisoned), older))
        connection.commit()
        rows = connection.execute("SELECT * FROM checkpoints ORDER BY revision").fetchall()
    finally:
        connection.close()
    artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    records = [{
        "revision": row["revision"], "event_type": row["event_type"],
        "milestone": bool(row["milestone"]), "created_at": row["created_at"],
        "state": RunState.from_dict(LongHorizonStore._deserialize(row["state_json"])).to_dict(),
    } for row in rows]
    timeline = _state_timeline(SimpleNamespace(checkpoint_records=lambda _: records), case["final"].run_id)
    _replace_artifact(case, "state_timeline", timeline)
    _replace_artifact(case, "causal_ledger", _causal_ledger(case["model_trace"], case["event_log"], timeline, case["final"]))
    with pytest.raises(DatasetIntegrityError, match="causal|snapshot|revision"):
        _load(case)


@pytest.mark.parametrize("missing", ["input_checkpoint", "role_snapshot", "response"])
def test_missing_executor_evidence_is_an_explicit_exclusion(mock_controller_case, missing):
    source = _load(mock_controller_case)
    boundary = next(record for record in source.final_state.causal_records.values()
                    if record.event_type == "tool_schema_disclosed")
    request = next(item for item in source.model_trace
                   if item.get("input_checkpoint_id") == boundary.payload["checkpoint_id"])
    if missing == "response":
        source = replace(source, model_trace=[item for item in source.model_trace if not (
            item.get("type") == "model_session_generation_returned"
            and item.get("request_id") == request["request_id"]
        )])
    else:
        snapshots = dict(source.snapshots)
        if missing == "role_snapshot":
            del snapshots[boundary.event_id]
        else:
            snapshots[boundary.event_id] = deepcopy(snapshots[boundary.event_id])
            del snapshots[boundary.event_id].model_states[boundary.payload["checkpoint_id"]]
        source = replace(source, snapshots=snapshots)
    samples, exclusions = extract_source(source, roles=("executor_args",))
    assert not samples
    assert any(item.get("request_id") == request["request_id"] and "missing" in item["reason"] for item in exclusions)


def _assert_no_positive_role(source, role):
    try:
        samples, exclusions = extract_source(source, roles=(role,))
    except DatasetIntegrityError:
        return  # Contradictory identity may reject the whole extraction batch.
    assert not samples
    assert any(item.get("role") == role for item in exclusions)


@pytest.mark.parametrize("corruption", [
    "other_candidate", "other_audit_boundary", "kernel_not_validated",
    "completion_decision", "completion_request", "completion_audit", "completion_output_sha",
])
def test_finalizer_cannot_borrow_another_candidate_or_completion_acceptance(mock_controller_case, corruption):
    source = deepcopy(_load(mock_controller_case))
    events = list(source.final_state.causal_records.values())
    opened = next(item for item in events if item.event_type == "goal_audit_boundary_opened" and item.payload.get("final_candidate"))
    accepted = next(item for item in events if item.event_type == "goal_audit_accepted" and item.payload.get("audit_boundary_id") == opened.subject_id)
    completed = next(item for item in events if item.event_type == "run_completed")
    if corruption == "other_candidate":
        opened.payload["decision_id"] = "D-OTHER-CANDIDATE"
    elif corruption == "other_audit_boundary":
        accepted.payload["audit_boundary_id"] = "GAB-OTHER-CANDIDATE"
    elif corruption == "kernel_not_validated":
        accepted.payload["kernel_validated"] = False
    else:
        field = {"completion_decision": "decision_id", "completion_request": "request_id",
                 "completion_audit": "audit_id", "completion_output_sha": "final_output_sha256"}[corruption]
        completed.payload[field] = "0" * 64 if field.endswith("sha256") else "OTHER-CANDIDATE"
    _assert_no_positive_role(source, "finalizer_answer")


@pytest.mark.parametrize("role", ["auditor_step", "auditor_final"])
@pytest.mark.parametrize("corruption", ["other_boundary", "other_audit", "audit_digest", "kernel_not_validated"])
def test_auditor_positive_requires_its_own_unchanged_kernel_acceptance(mock_controller_case, role, corruption):
    source = deepcopy(_load(mock_controller_case))
    events = list(source.final_state.causal_records.values())
    recorded = next(item for item in events if item.event_type == "goal_audit_recorded" and item.payload.get("auditor_role") == role)
    accepted = next(item for item in events if item.event_type == "goal_audit_accepted" and item.payload.get("request_id") == recorded.payload["request_id"])
    if corruption == "other_boundary":
        accepted.payload["audit_boundary_id"] = "GAB-OTHER-AUDIT"
    elif corruption == "other_audit":
        accepted.payload["audit_id"] = "AUD-OTHER-AUDIT"
    elif corruption == "audit_digest":
        accepted.payload["audit_digest"] = "0" * 64
    else:
        accepted.payload["kernel_validated"] = False
    _assert_no_positive_role(source, role)


@pytest.mark.parametrize("corruption", ["missing_token_ids", "raw_text", "nonzero_state"])
def test_finalizer_only_extraction_still_checks_referenced_final_auditor_output(mock_controller_case, corruption):
    source = deepcopy(_load(mock_controller_case))
    recorded = next(item for item in source.final_state.causal_records.values()
                    if item.event_type == "goal_audit_recorded" and item.payload.get("auditor_role") == "auditor_final")
    raw = recorded.payload["raw_generation"]
    if corruption == "missing_token_ids":
        raw["raw_token_ids"] = []
    elif corruption == "raw_text":
        raw["raw_output"] = "unrelated mocked output"
    else:
        raw["state_profile_id"] = "other-state"
    _assert_no_positive_role(source, "finalizer_answer")


@pytest.mark.parametrize("role", ["executor_args", "finalizer_answer"])
@pytest.mark.parametrize("field", ["input_digest", "raw_output"])
def test_accepted_event_decision_must_match_durable_decision_record(mock_controller_case, role, field):
    """An event copy cannot override the independently persisted model decision."""
    source = deepcopy(_load(mock_controller_case))
    accepted = next(
        event for event in source.final_state.causal_records.values()
        if event.event_type == "model_call_accepted"
        and (event.payload.get("model_role") == "finalizer_answer") == (role == "finalizer_answer")
    )
    original = deepcopy(source.final_state.decisions[accepted.payload["decision_id"]].to_dict())
    accepted.payload["decision"][field] = "0" * 64 if field == "input_digest" else "forged different output"
    assert source.final_state.decisions[accepted.payload["decision_id"]].to_dict() == original
    with pytest.raises(DatasetIntegrityError):
        extract_source(source, roles=(role,))
