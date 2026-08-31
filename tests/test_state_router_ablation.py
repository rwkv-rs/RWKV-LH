from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from rwkv_lh.state_router.protocol import HEAD_LABELS


ROOT = Path(__file__).resolve().parents[1]


def test_ablation_runner_enforces_frozen_sample_order_and_safety_first(tmp_path: Path) -> None:
    dataset = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/test.jsonl"
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    predictions = tmp_path / "perfect.jsonl"
    with predictions.open("w", encoding="utf-8") as stream:
        for row in rows:
            values = {}
            for name, labels in HEAD_LABELS.items():
                loser = 0.001 / (len(labels) - 1)
                values[name] = {
                    label: 0.999 if label == row["labels"][name] else loser
                    for label in labels
                }
            stream.write(
                json.dumps(
                    {"sample_id": row["sample_id"], "probabilities": values},
                    sort_keys=True,
                )
                + "\n"
            )
    output = tmp_path / "ablation.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate_state_router_ablation_v1.py"),
            "--dataset",
            str(dataset),
            "--candidate",
            f"A={predictions}",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["selected_candidate"] == "A"
    assert result["candidate_reports"]["A"]["formal_safety_pass"] is True
    assert result["candidate_reports"]["A"]["metrics"]["route_macro_f1"] == 1.0
