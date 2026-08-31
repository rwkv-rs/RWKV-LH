#!/usr/bin/env python3
"""Generate serving-parity connector function-pair rows for S19 state ablation."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import network_selector_tool_menu
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "data/datasets/rwkv_lh_network_connector_function_s18_v1/cases.jsonl"
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_description_s6_v1/queries.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S19_CONNECTOR_FUNCTION_STATE_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_connector_function_s19_v1"
EXPECTED = {
    "selection": "1983f1b0c2195eadf08b17a1747ac863225d09c7d3f80f59e29453c0da76c662",
    "source": "d60ad4a2404fda0f9401a5858070bb5e3063d408be68c9f88e1c0431eed1313c",
    "ecra": "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a",
}
VERSION = "rwkv-lh.network-connector-function.s19.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    data = text.encode("utf-8")
    return Counter(data[index:index + n] for index in range(max(0, len(data) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return dot / math.sqrt(sum(value * value for value in left.values()) * sum(value * value for value in right.values()))


def main() -> None:
    if OUTPUT.exists() or not PROTOCOL.is_file():
        raise RuntimeError("S19 output exists or protocol is missing")
    paths = {"selection": SELECTION, "source": SOURCE, "ecra": ECRA}
    if any(sha256_file(path) != EXPECTED[name] for name, path in paths.items()):
        raise RuntimeError("S19 frozen source identity changed")
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    selected = [json.loads(line) for line in SELECTION.read_text(encoding="utf-8").splitlines()]
    train_indices = [int(row["source_index"]) for row in selected]
    if len(train_indices) != 2000 or len(set(train_indices)) != 2000:
        raise RuntimeError("S19 train selection changed")
    connector = next(item for item in network_selector_tool_menu() if item["name"] == "connector_lookup")
    tokenizer = RWKVTokenizer()

    def project(source_index: int, split: str) -> dict[str, object]:
        source = source_rows[source_index]
        payload = {
            "schema_version": "rwkv-lh.connector-function-input.s19.v1",
            "objective": source["stage_objective"],
            "function": dict(connector),
        }
        label = "CONNECTOR" if source["label"] == "connector_lookup" else "OTHER"
        prompt = "ConnectorFunctionV1: " + canonical_json(payload)
        target = f"\nFunctionLabelV1: {label}"
        return {
            "schema_version": "rwkv-lh.target-suffix-state-row.v1",
            "dataset_version": VERSION,
            "sample_id": f"CONNFN-S19-{split.upper()}-{source['sample_id']}",
            "source_sample_id": source["sample_id"],
            "source_index": source_index,
            "semantic_family_id": source["semantic_family_id"],
            "source_kind": source["source_kind"],
            "split": split,
            "label": label,
            "source_label": source["label"],
            "prompt": prompt,
            "rendered_input": prompt,
            "target": target,
            "text": prompt + target,
            "input_digest": canonical_digest(payload),
            "prompt_tokens_including_bos": 1 + len(tokenizer.encode(prompt)),
            "text_tokens_including_bos": 1 + len(tokenizer.encode(prompt + target)),
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "generated_rwkv_text": False,
        }

    train = [project(index, "train") for index in train_indices]
    dev = [project(index, "dev") for index, row in enumerate(source_rows) if row["split"] == "dev"]
    if len(dev) != 926:
        raise RuntimeError("S19 dev cardinality changed")
    counts = {"train": Counter(str(row["label"]) for row in train), "dev": Counter(str(row["label"]) for row in dev)}
    if counts["train"] != Counter({"OTHER": 1310, "CONNECTOR": 690}) or counts["dev"] != Counter({"OTHER": 832, "CONNECTOR": 94}):
        raise RuntimeError("S19 label counts changed")
    families = {split: {(str(row["source_kind"]), str(row["semantic_family_id"])) for row in rows} for split, rows in (("train", train), ("dev", dev))}
    if families["train"] & families["dev"]:
        raise RuntimeError("S19 train/dev families overlap")
    if len({row["prompt"] for row in train + dev}) != len(train) + len(dev):
        raise RuntimeError("S19 exact prompt duplicates exist")
    if max(int(row["text_tokens_including_bos"]) for row in train + dev) > 512:
        raise RuntimeError("S19 target suffix exceeds context")
    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    holdout_grams = [(case["case_id"], byte_ngrams(case["instruction"])) for case in holdout]
    maximum = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in train + dev:
        grams = byte_ngrams(str(source_rows[int(row["source_index"])]["stage_objective"]))
        for holdout_id, reference in holdout_grams:
            score = cosine(grams, reference)
            if score > maximum["score"]:
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if float(maximum["score"]) >= 0.75:
        raise RuntimeError(f"S19 ECRA similarity gate failed: {maximum}")
    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s19_connector.", dir=OUTPUT.parent))
    files = {}
    for split, rows in (("train", train), ("dev", dev)):
        path = staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        with path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        files[path.name] = {"rows": len(rows), "sha256": sha256_file(path)}
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1", "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S19-CONNECTOR-S1 zero/tuned function-pair state ablation",
        "counts": {split: {"rows": sum(values.values()), "labels": dict(sorted(values.items()))} for split, values in counts.items()},
        "function": dict(connector), "function_digest": canonical_digest(dict(connector)),
        "sources": {name: {"path": str(path.relative_to(ROOT)), "sha256": EXPECTED[name]} for name, path in paths.items()},
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "training_contract": {"loss_mask": "target_suffix", "jsonl_bos_token_id": 0, "ctx_len": 512, "epoch_steps": 2000, "step_save": 500, "seed": 857},
        "validation": {"train_dev_family_overlap": 0, "exact_prompt_duplicates": 0, "maximum_prompt_tokens_including_bos": max(int(row["prompt_tokens_including_bos"]) for row in train + dev), "maximum_text_tokens_including_bos": max(int(row["text_tokens_including_bos"]) for row in train + dev), "contamination": {"algorithm": "utf8-byte-5gram-cosine.v1", "threshold_exclusive": 0.75, "maximum": maximum, "holdout_sha256": EXPECTED["ecra"]}, "generated_rwkv_text_count": 0},
        "generator_sha256": sha256_file(Path(__file__)), "generation": f"uv run --no-sync python {Path(__file__).resolve()}", "files": files,
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
