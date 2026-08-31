from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
S18 = ROOT / "data/datasets/rwkv_lh_network_connector_function_s18_v1"
S19 = ROOT / "data/datasets/rwkv_lh_network_connector_function_s19_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_s18_connector_function_selection_is_exact_unique_and_balanced() -> None:
    manifest = json.loads((S18 / "manifest.json").read_text(encoding="utf-8"))
    cases_path = S18 / "cases.jsonl"
    rows = _jsonl(cases_path)

    assert manifest["counts"] == {
        "binary_labels": {"CONNECTOR": 690, "OTHER": 1310},
        "groups": {
            "connector_positive": 690,
            "control_process": 150,
            "deterministic": 150,
            "other_local_read": 150,
            "read_file": 250,
            "read_json": 150,
            "web": 310,
            "workspace_mutation": 150,
        },
        "rows": 2000,
    }
    assert len(rows) == 2000
    assert _sha256(cases_path) == "1983f1b0c2195eadf08b17a1747ac863225d09c7d3f80f59e29453c0da76c662"
    assert len({row["source_sample_id"] for row in rows}) == 2000
    assert len({int(row["source_index"]) for row in rows}) == 2000
    assert Counter(str(row["binary_label"]) for row in rows) == Counter(
        {"CONNECTOR": 690, "OTHER": 1310}
    )
    assert all(
        (row["binary_label"] == "CONNECTOR") == (row["source_label"] == "connector_lookup")
        for row in rows
    )
    assert manifest["generated_rwkv_text_count"] == 0
    assert manifest["sampling_invocation_count"] == 0


def test_s19_function_pair_export_has_serving_parity_and_isolation() -> None:
    manifest = json.loads((S19 / "manifest.json").read_text(encoding="utf-8"))
    expected = {
        "train": (2000, Counter({"OTHER": 1310, "CONNECTOR": 690}), "f263c81c8ad20569db174f584645359bb343da8beea13a540f969ffa163f752a"),
        "dev": (926, Counter({"OTHER": 832, "CONNECTOR": 94}), "c06fcb583807fdb5ad1b2ff1272c66e0fb77afddb5ffbf82cdd41fbef02d3c5b"),
    }
    split_rows: dict[str, list[dict[str, object]]] = {}
    all_prompts: list[str] = []

    for split, (count, labels, digest) in expected.items():
        path = S19 / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        rows = _jsonl(path)
        split_rows[split] = rows
        assert len(rows) == count
        assert _sha256(path) == digest
        assert Counter(str(row["label"]) for row in rows) == labels
        for row in rows:
            prompt = str(row["prompt"])
            all_prompts.append(prompt)
            assert row["rendered_input"] == prompt
            assert row["text"] == prompt + row["target"]
            assert row["target"] == f"\nFunctionLabelV1: {row['label']}"
            assert row["loss_mask"] == "target_suffix"
            assert row["jsonl_bos_token_id"] == 0
            assert row["generated_rwkv_text"] is False
            assert int(row["text_tokens_including_bos"]) <= 512
            assert prompt.startswith("ConnectorFunctionV1: ")
            payload = json.loads(prompt.removeprefix("ConnectorFunctionV1: "))
            assert payload["function"] == manifest["function"]
            assert set(payload) == {"function", "objective", "schema_version"}

    train_families = {
        (str(row["source_kind"]), str(row["semantic_family_id"]))
        for row in split_rows["train"]
    }
    dev_families = {
        (str(row["source_kind"]), str(row["semantic_family_id"]))
        for row in split_rows["dev"]
    }
    assert train_families.isdisjoint(dev_families)
    assert len(set(all_prompts)) == len(all_prompts)
    assert manifest["training_contract"] == {
        "ctx_len": 512,
        "epoch_steps": 2000,
        "jsonl_bos_token_id": 0,
        "loss_mask": "target_suffix",
        "seed": 857,
        "step_save": 500,
    }
    assert manifest["validation"]["contamination"]["algorithm"] == "utf8-byte-5gram-cosine.v1"
    assert manifest["validation"]["contamination"]["maximum"]["score"] < 0.75
    assert manifest["validation"]["generated_rwkv_text_count"] == 0
