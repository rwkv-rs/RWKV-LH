"""Run Stage-0 scheme C with pinned RWKV single-token constrained codes."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.state_router.local_backend import (
    DEFAULT_ROUTER_MODEL,
    DEFAULT_VLLM_RWKV_PYTHON,
    DEFAULT_VLLM_RWKV_REVISION,
    DEFAULT_VLLM_RWKV_ROOT,
    LocalVLLMRWKVExtractor,
    LocalVLLMRWKVSettings,
)
from rwkv_lh.state_router.metrics import (
    FIRST_ROUND_GATES,
    FORMAL_GATES,
    acceptance_gates,
    evaluate_probabilities,
)
from rwkv_lh.state_router.protocol import HEAD_LABELS, RouterInput, canonical_digest
from rwkv_lh.state_router.training import (
    file_sha256,
    probability_records,
    read_rows,
    select_temperature,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/samples.jsonl"
DEFAULT_OUTPUT = (
    ROOT / "data/experiments/STATE_ROUTER_STAGE0_VLLM_CONSTRAINED_LOGITS_V1_20260827"
)
PROMPT_PROTOCOL_VERSION = "rwkv-lh.state-router-constrained-codes.v1"
HEAD_TITLES = {
    "context_mode": "whether this is a fresh request or a continuation",
    "execution_phase": "the current evidence and policy execution phase",
    "route_family": "the required capability family",
    "network_recommendation": "whether network access is required",
}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pending.replace(path)


def codes_for(head: str) -> dict[str, str]:
    return {
        label: chr(ord("A") + index)
        for index, label in enumerate(HEAD_LABELS[head])
    }


def constrained_prompt(router_input: RouterInput, head: str) -> str:
    codes = codes_for(head)
    legend = "; ".join(f"{code}={label}" for label, code in codes.items())
    return "\n".join(
        (
            "Classify one RWKV-LH State Router record.",
            f"Decision: {HEAD_TITLES[head]}.",
            f"Allowed codes: {legend}.",
            "Reply with exactly one allowed code and no other text.",
            "Record:",
            router_input.render(),
            "Code:",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", type=Path, default=DEFAULT_ROUTER_MODEL)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_VLLM_RWKV_ROOT)
    parser.add_argument("--engine-revision", default=DEFAULT_VLLM_RWKV_REVISION)
    parser.add_argument("--engine-python", type=Path, default=DEFAULT_VLLM_RWKV_PYTHON)
    parser.add_argument("--wkv-mode", choices=("fp16", "fp32io16"), default="fp16")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args()

    import torch

    dataset = args.dataset.resolve()
    output = args.output.resolve()
    rows = read_rows(dataset)
    inputs = [RouterInput.from_dict(row["input"]) for row in rows]
    extractor = LocalVLLMRWKVExtractor(
        LocalVLLMRWKVSettings(
            model=args.model,
            engine_root=args.engine_root,
            engine_revision=args.engine_revision,
            engine_python=args.engine_python,
            batch_size=args.batch_size,
            max_tokens=args.max_tokens,
            wkv_mode=args.wkv_mode,
        )
    )
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    logits: dict[str, Any] = {}
    for head in HEAD_LABELS:
        codes = codes_for(head)
        logits[head] = extractor.score_single_token_codes(
            [constrained_prompt(router_input, head) for router_input in inputs],
            list(codes.values()),
        )
    inference_seconds = time.perf_counter() - started

    label_indices = {
        name: {label: index for index, label in enumerate(labels)}
        for name, labels in HEAD_LABELS.items()
    }
    labels = {
        name: torch.tensor(
            [label_indices[name][str(row["labels"][name])] for row in rows],
            dtype=torch.long,
        )
        for name in HEAD_LABELS
    }
    split_indices = {
        split: [index for index, row in enumerate(rows) if row["split"] == split]
        for split in ("train", "dev", "test")
    }
    if {name: len(indices) for name, indices in split_indices.items()} != {
        "train": 1400,
        "dev": 300,
        "test": 300,
    }:
        raise ValueError("constrained-logits evaluation requires frozen 1400/300/300 splits")
    dev_index = torch.tensor(split_indices["dev"], dtype=torch.long)
    temperatures = {
        name: select_temperature(values[dev_index], labels[name][dev_index])
        for name, values in logits.items()
    }
    probabilities = probability_records(logits, temperatures)
    split_reports = {
        split: evaluate_probabilities(
            [rows[index] for index in indices],
            [probabilities[index] for index in indices],
        )
        for split, indices in split_indices.items()
    }
    prompt_identity = {
        "protocol_version": PROMPT_PROTOCOL_VERSION,
        "head_titles": HEAD_TITLES,
        "head_labels": {name: list(labels) for name, labels in HEAD_LABELS.items()},
        "codes": {name: codes_for(name) for name in HEAD_LABELS},
        "template": constrained_prompt(inputs[0], "route_family").replace(
            inputs[0].render(), "<ROUTER_INPUT_V1>"
        ),
    }
    runtime_identity = extractor.identity()
    result = {
        "schema_version": "rwkv-lh.state-router-constrained-result.v1",
        "scheme": "C",
        "dataset": {
            "path": str(dataset),
            "sha256": file_sha256(dataset),
            "rows": len(rows),
        },
        "runtime_identity": runtime_identity,
        "prompt_identity": prompt_identity,
        "prompt_hash": canonical_digest(prompt_identity),
        "temperatures": temperatures,
        "temperature_selection_split": "dev",
        "metrics": split_reports,
        "acceptance": {
            split: {
                "first_round": acceptance_gates(split_reports[split], FIRST_ROUND_GATES),
                "formal": acceptance_gates(split_reports[split], FORMAL_GATES),
            }
            for split in ("dev", "test")
        },
        "label_counts": {
            split: {
                name: dict(
                    sorted(
                        Counter(str(rows[index]["labels"][name]) for index in indices).items()
                    )
                )
                for name in HEAD_LABELS
            }
            for split, indices in split_indices.items()
        },
        "runtime_measurements": {
            "inference_seconds": inference_seconds,
            "samples_per_second": len(rows) / inference_seconds,
            "cuda_peak_allocated_bytes": int(
                runtime_identity.get("runtime", {}).get(
                    "cuda_peak_allocated_bytes", 0
                )
            ),
            "cuda_peak_reserved_bytes": int(
                runtime_identity.get("runtime", {}).get(
                    "cuda_peak_reserved_bytes", 0
                )
            ),
        },
    }
    write_json(output / "results.json", result)
    predictions_path = output / "predictions.test.jsonl"
    pending_predictions = predictions_path.with_suffix(".jsonl.pending")
    pending_predictions.parent.mkdir(parents=True, exist_ok=True)
    with pending_predictions.open("w", encoding="utf-8") as stream:
        for index in split_indices["test"]:
            stream.write(
                json.dumps(
                    {
                        "schema_version": "rwkv-lh.state-router-prediction.v1",
                        "sample_id": rows[index]["sample_id"],
                        "probabilities": probabilities[index],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    pending_predictions.replace(predictions_path)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
