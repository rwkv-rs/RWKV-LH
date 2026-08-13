from scripts.analyze_rwkv_round import byte_ngram_cosine
from scripts.run_rwkv_e2e_benchmark import _causal_ledger, _json_changes


def test_fixed_byte_ngram_similarity_is_exact_and_symmetric():
    assert byte_ngram_cosine("Hello, RWKV-LH!\n", "Hello, RWKV-LH!\n") == 1.0
    assert byte_ngram_cosine("", "") == 1.0
    assert byte_ngram_cosine("", "answer") == 0.0
    assert byte_ngram_cosine("alpha", "beta") == byte_ngram_cosine("beta", "alpha")


def test_state_delta_records_add_remove_and_replace_without_interpretation():
    changes = _json_changes(
        {"status": "running", "tasks": [{"id": "T1", "attempt": 1}], "old": True},
        {"status": "completed", "tasks": [{"id": "T1", "attempt": 2}], "new": True},
    )
    assert changes == [
        {"op": "add", "path": "$.new", "after": True},
        {"op": "remove", "path": "$.old", "before": True},
        {
            "op": "replace",
            "path": "$.status",
            "before": "running",
            "after": "completed",
        },
        {"op": "replace", "path": "$.tasks[0].attempt", "before": 1, "after": 2},
    ]


def test_causal_ledger_links_exact_model_exchange_state_revision_and_task_outputs():
    trace = [
        {
            "type": "model_request_started",
            "request_id": "R1",
            "request_type": "tool_action_commit",
            "task_id": "T2",
            "prompt": "exact prompt",
            "temperature": 0.05,
        },
        {
            "type": "model_request_returned",
            "request_id": "R1",
            "request_type": "tool_action_commit",
            "task_id": "T2",
            "raw_output": '{"tool":"read_file","arguments":{"path":"x.py"}}',
            "finish_reason": "stop",
        },
        {
            "type": "model_protocol_parsed",
            "request_id": "R1",
            "request_type": "tool_action_commit",
            "parsed_payload": {
                "tool": "read_file",
                "arguments": {"path": "x.py"},
            },
        },
    ]
    events = [
        {
            "type": "model_protocol_normalized",
            "data": {
                "request_id": "R1",
                "task_id": "T2",
                "raw_payload": {"tool": "read_file"},
                "normalized_payload": {"name": "read_file"},
            },
        },
        {
            "type": "action_returned",
            "data": {"task_id": "T2", "attempt_id": "T2-A1"},
        },
    ]
    timeline = [
        {
            "revision": 1,
            "event_type": events[0]["type"],
            "state_sha256": "a" * 64,
            "changes_from_previous": [{"op": "add", "path": "$.tasks.T2.action"}],
        },
        {
            "revision": 2,
            "event_type": events[1]["type"],
            "state_sha256": "b" * 64,
            "changes_from_previous": [{"op": "add", "path": "$.memory_index.M2"}],
        },
    ]
    state = {
        "tasks": {
            "T1": {"dependencies": [], "attempt_ids": [], "output_refs": ["M1"]},
            "T2": {
                "dependencies": ["T1"],
                "attempt_ids": ["T2-A1"],
                "output_refs": ["M2", "A2"],
            },
        },
        "attempts": {"T2-A1": {"attempt_id": "T2-A1", "task_id": "T2"}},
        "memory_index": {"M1": {"content": "dependency"}, "M2": {"content": "actual"}},
        "artifacts": {"A2": {"path": "x.py", "sha256": "c" * 64}},
        "criterion_claims": {
            "CC1": {"producer_task_id": "T2", "subject_task_id": "T2"}
        },
        "criterion_evidence": {"CE1": {"owner_task_id": "T2"}},
    }

    ledger = _causal_ledger(trace, events, timeline, state)

    request = ledger["requests"][0]
    assert ledger["request_order"] == ["R1"]
    assert request["input"]["prompt"] == "exact prompt"
    assert request["raw_output"]["text"].startswith('{"tool":"read_file"')
    assert request["protocol_events"][0]["parsed_payload"]["tool"] == "read_file"
    assert request["linked_event_revisions"][0]["revision"] == 1
    task = ledger["tasks"]["T2"]
    assert task["dependency_outputs"] == {"T1": ["M1"]}
    assert [item["kind"] for item in task["resolved_outputs"]] == [
        "memory",
        "artifact",
    ]
    assert set(task["criterion_claims"]) == {"CC1"}
    assert set(task["criterion_evidence"]) == {"CE1"}
