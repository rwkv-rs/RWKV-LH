from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import (
    INDEPENDENT_EXECUTOR_REQUEST_LAST_PROTOCOL,
    parse_model_command,
)


ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ROOT / "data/datasets/rwkv_lh_network_selector_true_workflow_s55_v1"
EXECUTOR = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_2k"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_s55_g4_frozen_manifests_and_counts() -> None:
    assert sha256_file(SELECTOR / "manifest.json") == (
        "0301ee78e793f80d314fb6f877433b101881bd5ec856bb67691d0fc0c7c4e659"
    )
    assert sha256_file(EXECUTOR / "manifest.json") == (
        "ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f"
    )
    selector_manifest = json.loads((SELECTOR / "manifest.json").read_text(encoding="utf-8"))
    executor_manifest = json.loads((EXECUTOR / "manifest.json").read_text(encoding="utf-8"))
    assert selector_manifest["counts"] == {"train": 800, "dev": 240, "test": 240}
    assert executor_manifest["counts"] == {"train": 2000, "dev": 480}
    assert executor_manifest["validation"]["current_requirement_last"] is True
    assert executor_manifest["validation"]["target_truncation_count"] == 0
    assert executor_manifest["validation"]["all_targets_current_contract_valid"] is True


def test_g4_workflow_rows_keep_full_request_last_and_targets_exact() -> None:
    expected = {"train": 2000, "dev": 480}
    for split, count in expected.items():
        rows = [
            json.loads(line)
            for line in (EXECUTOR / f"stage_sft.{split}.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(rows) == count
        assert Counter(row["source_kind"] for row in rows) == {
            "g3_frozen_direct_retention": 1200 if split == "train" else 240,
            "synthetic_true_workflow_request_last": 800 if split == "train" else 240,
        }
        for row in rows:
            assert row["text"] == row["prompt"] + row["target"]
            assert hashlib.sha256(row["prompt"].encode("utf-8")).hexdigest() == row[
                "prompt_sha256"
            ]
            assert hashlib.sha256(row["target"].encode("utf-8")).hexdigest() == row[
                "target_sha256"
            ]
            command = parse_model_command(row["target"])
            assert command.name == row["selected_operation"]
            continuation = row["prompt"].rsplit(
                "\n\nUser: Executor continuation input: ", 1
            )[1].split("\n\nAssistant:", 1)[0]
            payload = json.loads(continuation)
            assert payload["protocol"] == INDEPENDENT_EXECUTOR_REQUEST_LAST_PROTOCOL
            assert list(payload)[-1] == "current_requirement"
            assert isinstance(payload["current_requirement"], str)
            assert payload["current_requirement"].strip()
            assert row["generated_rwkv_text"] is False
            assert row["raw_output_modified"] is False
