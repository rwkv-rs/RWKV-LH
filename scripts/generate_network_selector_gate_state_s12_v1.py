#!/usr/bin/env python3
"""Export serving-parity S11 Gate labels for S12 state tuning."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s11_v1/cases.jsonl"
SOURCE_MANIFEST = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s11_v1/manifest.json"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_gate_state_s12_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S12_GATE_STATE_PREREGISTRATION.md"
SOURCE_SHA = "553208ddf01e9baa6542fbd95ed653a0615111263a0573be4c388a4ca86f0c17"
VERSION = "rwkv-lh.network-selector-gate-state.s12.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if sha256_file(SOURCE) != SOURCE_SHA or OUTPUT.exists() or not PROTOCOL.is_file():
        raise RuntimeError("S12 frozen source/output/protocol contract failed")
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    contamination = source_manifest["validation"]["contamination"]
    if contamination["algorithm"] != "utf8-byte-5gram-cosine.v1" or contamination["maximum"]["score"] >= 0.75:
        raise RuntimeError("S12 inherited contamination contract changed")
    tokenizer = RWKVTokenizer()
    exported: dict[str, list[dict[str, object]]] = {"train": [], "dev": []}
    excluded: Counter[tuple[str, str]] = Counter()
    for source in (json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()):
        split = str(source["split"])
        if split == "test":
            continue
        label = "NETWORK" if source["label"] != "DEFER" else "DEFER"
        prompt = str(source["rendered_input"])
        prompt_tokens = 1 + len(tokenizer.encode(prompt))
        if prompt_tokens > 384:
            excluded[(split, label)] += 1
            continue
        target = f"\nGateLabelV1: {label}"
        row = {
            "schema_version": "rwkv-lh.target-suffix-state-row.v1",
            "dataset_version": VERSION,
            "sample_id": f"GATE-S12-{source['sample_id']}",
            "source_sample_id": source["sample_id"],
            "semantic_family_id": source["semantic_family_id"],
            "split": split,
            "label": label,
            "prompt": prompt,
            "target": target,
            "text": prompt + target,
            "prompt_tokens_including_bos": prompt_tokens,
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "generated_rwkv_text": False,
        }
        exported[split].append(row)
    counts = {split: len(rows) for split, rows in exported.items()}
    labels = {split: dict(sorted(Counter(str(row["label"]) for row in rows).items())) for split, rows in exported.items()}
    if counts != {"train": 1467, "dev": 275} or labels != {"train": {"DEFER": 787, "NETWORK": 680}, "dev": {"DEFER": 165, "NETWORK": 110}}:
        raise RuntimeError(f"S12 fixed counts changed: {counts=} {labels=}")
    if excluded != Counter({("train", "DEFER"): 39, ("dev", "DEFER"): 14}):
        raise RuntimeError(f"S12 exclusion counts changed: {excluded}")
    families = {split: {str(row["semantic_family_id"]) for row in rows} for split, rows in exported.items()}
    if families["train"] & families["dev"]:
        raise RuntimeError("S12 family crosses train/dev")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_gate_s12.", dir=OUTPUT.parent))
    files = {}
    for split, rows in exported.items():
        path = staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        with path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        files[path.name] = {"rows": len(rows), "sha256": sha256_file(path)}
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S12-GATE serving-parity function-state tuning",
        "counts": counts,
        "label_counts": labels,
        "excluded_over_384": {"train_defer": 39, "dev_defer": 14, "network": 0},
        "source": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA, "manifest_sha256": sha256_file(SOURCE_MANIFEST)},
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "training_contract": {"loss_mask": "target_suffix", "jsonl_bos_token_id": 0, "ctx_len": 512, "epoch_steps": 1467, "step_save": 489, "seed": 843},
        "validation": {"train_dev_family_overlap": 0, "maximum_prompt_tokens_including_bos": max(int(row["prompt_tokens_including_bos"]) for rows in exported.values() for row in rows), "contamination": contamination, "generated_rwkv_text_count": 0},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator_sha256": sha256_file(Path(__file__)),
        "files": files,
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
