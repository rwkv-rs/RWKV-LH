from scripts.analyze_rwkv_round import byte_ngram_cosine
from scripts.run_rwkv_e2e_benchmark import _json_changes


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
