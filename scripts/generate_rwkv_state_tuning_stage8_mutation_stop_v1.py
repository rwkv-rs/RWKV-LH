"""Build Stage8 mutation/verification stopping contrasts from real Controller replay."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable, Mapping

from rwkv_lh.chunks import slice_text_from_byte_cursor

from scripts import generate_rwkv_action_state_tuning_round1_2k_v1 as round1
from scripts import generate_rwkv_action_state_tuning_v1 as pilot
from scripts import generate_rwkv_state_tuning_stage7_factory_contrast_v1 as stage7


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/datasets/rwkv_lh_state_tuning_stage8_mutation_stop_seed_v1"
SURFACES = ROOT / "data/datasets/rwkv_lh_state_tuning_stage8_mutation_stop_surfaces_v1"
FACTORY_SOURCE = (
    ROOT.parent
    / "RWKV-state-factory/rwkv_web_retrieval_state_factory/surface_synthesis.py"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage8_mutation_stop_v1"
VERSION = "rwkv-lh.state-tuning.stage8-mutation-stop.v1"
FACTORY_SCHEMA = "rwkv-surface-factory.cards.v1"
SIGNATURES = {
    "mutation_success_stop": "FST-S8-001",
    "investigate_scope_stop": "FST-S8-002",
    "verify_evidence_stop": "FST-S8-003",
    "idempotent_repeat_stop": "FST-S8-004",
    "stage7_safety_anchor": "FST-S8-005",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _base(card: Mapping[str, Any], lane: str, *, language: str) -> dict[str, Any]:
    surface_id = str(card["surface_id"])
    family = f"AST-S8-SF-{surface_id}"
    return {
        "schema_version": pilot.CANDIDATE_SCHEMA,
        "trajectory_id": f"AST-S8-{surface_id}-{lane}",
        "factory_surface_id": surface_id,
        "source_seed_id": str(card["seed_id"]),
        "semantic_family_id": family,
        "split": str(card["split"]),
        "language": language,
        "network_policy": "offline",
        "request": "",
        "workspace_files": [],
        "turns": [],
        "prelude": [],
        "expected_backend_executions": 0,
        "private_oracle_digest": "",
        "failure_cluster": str(card["cluster"]),
        "failure_signature_id": SIGNATURES[str(card["cluster"])],
        "contrast_group": family,
        "state_lane": lane,
    }


def _final(language: str, detail: str) -> dict[str, Any]:
    text = (
        f"当前步骤已有完整证据，可以停止：{detail}。"
        if language == "zh"
        else f"The current step has complete evidence and can stop: {detail}."
    )
    return pilot._turn("final_answer", {"text": text}, "evidence_complete")


def _fill(template: str, values: Mapping[str, object]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace("{" + key + "}", str(value))
    if "{" in result or "}" in result:
        raise ValueError(f"unfilled surface template: {result}")
    return result


def _mutation_candidates(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = dict(card["fields"])
    language = "zh" if int(card["ordinal"]) % 2 == 0 else "en"
    template = str(fields[f"{language}_objective_template"])
    nonce = str(card["surface_id"]).lower()
    path = f"stage8/mutation/{nonce}.json"
    wanted = {
        "project": f"{fields['entity_stem']}-{int(card['ordinal']):04d}",
        "count": 11 + int(card["ordinal"]) % 83,
    }
    old = {"project": wanted["project"], "count": int(wanted["count"]) + 1}
    request = _fill(
        template,
        {
            "target_path": path,
            "project_value": wanted["project"],
            "count_value": wanted["count"],
            "entity_stem": fields["entity_stem"],
        },
    )
    write = pilot._turn("write_json", {"path": path, "value": wanted}, "mutation_required")
    read = pilot._turn("read_json", {"path": path}, "intervening_exact_observation")

    before = _base(card, "before-mutation", language=language)
    before.update({"request": request, "turns": [write]})

    committed = _base(card, "after-first-success", language=language)
    committed.update(
        {
            "request": request,
            "prelude": [{"operation": "write_json", "params": {"path": path, "value": wanted}}],
            "turns": [_final(language, f"{path} committed")],
        }
    )

    repeated = _base(card, "after-identical-repeat", language=language)
    repeated.update(
        {
            "request": request,
            "prelude": [
                {"operation": "write_json", "params": {"path": path, "value": wanted}},
                {"operation": read["target_operation"], "params": read["target_params"]},
                {"operation": "write_json", "params": {"path": path, "value": wanted}},
            ],
            "turns": [_final(language, f"{path} already exact; no third write")],
        }
    )

    changed = _base(card, "changed-required-value", language=language)
    changed.update(
        {
            "request": request,
            "prelude": [{"operation": "write_json", "params": {"path": path, "value": old}}],
            "turns": [write],
        }
    )
    return [before, committed, repeated, changed]


def _investigate_candidates(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = dict(card["fields"])
    language = "zh" if int(card["ordinal"]) % 2 == 0 else "en"
    template = str(fields[f"{language}_objective_template"])
    nonce = str(card["surface_id"]).lower()
    source = f"stage8/investigate/{nonce}-source.txt"
    target = f"stage8/investigate/{nonce}-downstream.json"
    marker = f"source-{int(card['ordinal']):04d}-{fields['entity_stem']}"
    long_content = ("context-segment|" * 320) + f"\nrequired-source-value={marker}\n"
    next_source_byte = slice_text_from_byte_cursor(
        source, long_content, start_byte=0, max_tokens=256
    ).descriptor.core_end
    request = _fill(
        template,
        {
            "source_path": source,
            "target_path": target,
            "entity_stem": fields["entity_stem"],
        },
    )
    source_read = {"operation": "read_file", "params": {"path": source}}
    missing_target = {"operation": "read_json", "params": {"path": target}}

    unobserved = _base(card, "source-unobserved", language=language)
    unobserved.update(
        {
            "request": request,
            "workspace_files": [pilot._workspace_file(source, f"required-source-value={marker}\n")],
            "turns": [pilot._turn("read_file", {"path": source}, "source_unobserved")],
        }
    )

    complete = _base(card, "source-complete", language=language)
    complete.update(
        {
            "request": request,
            "workspace_files": [pilot._workspace_file(source, f"required-source-value={marker}\n")],
            "prelude": [source_read],
            "turns": [_final(language, f"investigation recorded {marker}")],
        }
    )

    downstream_missing = _base(card, "downstream-missing-out-of-scope", language=language)
    downstream_missing.update(
        {
            "request": request,
            "workspace_files": [pilot._workspace_file(source, f"required-source-value={marker}\n")],
            "prelude": [source_read, missing_target],
            "turns": [_final(language, f"source recorded; missing {target} is outside this atom")],
        }
    )

    incomplete = _base(card, "source-incomplete", language=language)
    incomplete.update(
        {
            "request": request,
            "workspace_files": [pilot._workspace_file(source, long_content)],
            "prelude": [{"operation": "read_file", "params": {"path": source, "max_tokens": 256}}],
            "turns": [
                pilot._turn(
                    "read_file",
                    {"path": source, "start_byte": next_source_byte, "max_tokens": 256},
                    "source_projection_incomplete",
                )
            ],
        }
    )
    return [unobserved, complete, downstream_missing, incomplete]


def _verify_candidates(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = dict(card["fields"])
    language = "zh" if int(card["ordinal"]) % 2 == 0 else "en"
    template = str(fields[f"{language}_objective_template"])
    nonce = str(card["surface_id"]).lower()
    source = f"stage8/verify/{nonce}-source.json"
    target = f"stage8/verify/{nonce}-target.json"
    marker = f"verify-{int(card['ordinal']):04d}-{fields['entity_stem']}"
    value = {"record": marker, "approved": True, "revision": 3}
    padded = {"padding": "p" * 6000, **value}
    canonical_padded = json.dumps(
        padded, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    next_target_byte = slice_text_from_byte_cursor(
        target + "#canonical-json",
        canonical_padded,
        start_byte=0,
        max_tokens=256,
        media_type="application/json",
    ).descriptor.core_end
    request = _fill(
        template,
        {
            "source_path": source,
            "target_path": target,
            "entity_stem": fields["entity_stem"],
        },
    )
    source_file = pilot._workspace_file(source, json.dumps(value, ensure_ascii=False) + "\n")
    target_file = pilot._workspace_file(target, json.dumps(value, ensure_ascii=False) + "\n")
    source_read = {"operation": "read_json", "params": {"path": source}}
    target_read = {"operation": "read_json", "params": {"path": target}}

    source_missing = _base(card, "source-evidence-missing", language=language)
    source_missing.update(
        {
            "request": request,
            "workspace_files": [source_file, target_file],
            "turns": [pilot._turn("read_json", {"path": source}, "source_unobserved")],
        }
    )

    target_missing = _base(card, "target-evidence-missing", language=language)
    target_missing.update(
        {
            "request": request,
            "workspace_files": [source_file, target_file],
            "prelude": [source_read],
            "turns": [pilot._turn("read_json", {"path": target}, "target_unobserved")],
        }
    )

    both_complete = _base(card, "both-evidence-complete", language=language)
    both_complete.update(
        {
            "request": request,
            "workspace_files": [source_file, target_file],
            "prelude": [source_read, target_read],
            "turns": [_final(language, f"{target} matches {source}")],
        }
    )

    target_incomplete = _base(card, "target-evidence-incomplete", language=language)
    target_incomplete.update(
        {
            "request": request,
            "workspace_files": [
                source_file,
                pilot._workspace_file(target, json.dumps(padded, ensure_ascii=False) + "\n"),
            ],
            "prelude": [
                source_read,
                {"operation": "read_json", "params": {"path": target, "max_tokens": 256}},
            ],
            "turns": [
                pilot._turn(
                    "read_json",
                    {"path": target, "start_byte": next_target_byte, "max_tokens": 512},
                    "target_projection_incomplete",
                )
            ],
        }
    )
    return [source_missing, target_missing, both_complete, target_incomplete]


def _idempotent_candidates(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = dict(card["fields"])
    language = "zh" if int(card["ordinal"]) % 2 == 0 else "en"
    template = str(fields[f"{language}_objective_template"])
    nonce = str(card["surface_id"]).lower()
    target = f"stage8/idempotent/{nonce}.txt"
    unrelated = f"stage8/idempotent/{nonce}-unrelated"
    marker = f"{fields['entity_stem']}-{int(card['ordinal']):04d}"
    content = marker + "\n"
    request = _fill(template, {"target_path": target, "marker_value": marker})
    write_params = {"path": target, "content": content}
    wrong_file = pilot._workspace_file(target, "wrong-marker\n")

    wrong = _base(card, "target-wrong", language=language)
    wrong.update(
        {
            "request": request,
            "workspace_files": [wrong_file],
            "turns": [pilot._turn("write_file", write_params, "target_wrong")],
        }
    )

    first_success = _base(card, "first-success", language=language)
    first_success.update(
        {
            "request": request,
            "prelude": [{"operation": "write_file", "params": write_params}],
            "turns": [_final(language, f"{target} contains {marker}")],
        }
    )

    repeat = _base(card, "identical-count-two", language=language)
    repeat.update(
        {
            "request": request,
            "prelude": [
                {"operation": "write_file", "params": write_params},
                {"operation": "read_file", "params": {"path": target}},
                {"operation": "write_file", "params": write_params},
            ],
            "turns": [_final(language, f"{target} is exact; repeated mutation must stop")],
        }
    )

    unrelated_success = _base(card, "unrelated-success", language=language)
    unrelated_success.update(
        {
            "request": request,
            "workspace_files": [wrong_file],
            "prelude": [{"operation": "make_directory", "params": {"path": unrelated}}],
            "turns": [pilot._turn("write_file", write_params, "target_still_wrong")],
        }
    )
    return [wrong, first_success, repeat, unrelated_success]


BUILDERS = {
    "mutation_success_stop": _mutation_candidates,
    "investigate_scope_stop": _investigate_candidates,
    "verify_evidence_stop": _verify_candidates,
    "idempotent_repeat_stop": _idempotent_candidates,
}


def replay_card(
    card: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = BUILDERS[str(card["cluster"])](card)
    rows: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    for candidate in candidates:
        picked, validation = stage7.select_stages(candidate, (("turn", 0),))
        if len(picked) != 1:
            raise RuntimeError(f"unexpected selected stage count: {candidate['trajectory_id']}")
        row = picked[0]
        row["state_lane"] = candidate["state_lane"]
        rows.append(row)
        validations.append(
            {
                "surface_id": card["surface_id"],
                "state_lane": candidate["state_lane"],
                **validation,
            }
        )
    if len(rows) != 4:
        raise RuntimeError(f"surface family does not contain four states: {card['surface_id']}")
    return rows, validations, candidates


def stable_anchor_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, contamination = stage7.stable_anchor_rows()
    if len(rows) != 400:
        raise RuntimeError("Stage7 stable anchor count changed")
    selected: list[dict[str, Any]] = []
    for index, source in enumerate(rows):
        row = dict(source)
        row.update(
            {
                "failure_cluster": "stage7_safety_anchor",
                "failure_signature_id": SIGNATURES["stage7_safety_anchor"],
                "training_intent": "preserve_stage7_selector_safety_and_routing",
                "contrast_group": f"AST-S8-ANCHOR-{index + 1:04d}",
            }
        )
        selected.append(row)
    return selected, contamination


def _interleave_key(row: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        (
            str(row.get("contrast_group") or "")
            + "|"
            + str(row["trajectory_id"])
            + "|"
            + str(row["turn_index"])
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset: {OUTPUT}")
    required = (
        SEED / "seed_plan.jsonl",
        SURFACES / "manifest.json",
        SURFACES / "surface_cards.jsonl",
        FACTORY_SOURCE,
    )
    if any(not path.is_file() for path in required):
        raise FileNotFoundError([str(path) for path in required if not path.is_file()])
    factory_manifest = read_json(SURFACES / "manifest.json")
    cards = read_jsonl(SURFACES / "surface_cards.jsonl")
    if (
        factory_manifest.get("schema_version") != FACTORY_SCHEMA
        or factory_manifest.get("card_count") != 500
        or len(cards) != 500
    ):
        raise RuntimeError("frozen Stage8 Factory surface contract changed")

    stages: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index, (card, result) in enumerate(
            zip(cards, pool.map(replay_card, cards)), 1
        ):
            try:
                picked, reports, rendered = result
            except Exception as exc:
                raise RuntimeError(
                    f"Stage8 replay failed at {index}/500 for {card['surface_id']}"
                ) from exc
            stages.extend(picked)
            validations.extend(reports)
            candidates.extend(rendered)
            if index % 25 == 0:
                print(f"controller replay {index}/500", flush=True)

    anchors, anchor_contamination = stable_anchor_rows()
    train = [row for row in stages if row["split"] == "train"] + anchors
    dev = [row for row in stages if row["split"] == "dev"]
    train.sort(key=_interleave_key)
    dev.sort(key=_interleave_key)
    expected_train = Counter(
        {
            "mutation_success_stop": 400,
            "investigate_scope_stop": 400,
            "verify_evidence_stop": 400,
            "idempotent_repeat_stop": 400,
            "stage7_safety_anchor": 400,
        }
    )
    expected_dev = Counter(
        {
            "mutation_success_stop": 100,
            "investigate_scope_stop": 100,
            "verify_evidence_stop": 100,
            "idempotent_repeat_stop": 100,
        }
    )
    if Counter(row["failure_cluster"] for row in train) != expected_train:
        raise RuntimeError("Stage8 train quota changed")
    if Counter(row["failure_cluster"] for row in dev) != expected_dev:
        raise RuntimeError("Stage8 dev quota changed")
    if len(train) != 2000 or len(dev) != 400:
        raise RuntimeError(f"Stage8 split count changed: {len(train)}, {len(dev)}")
    if len({row["text"] for row in [*train, *dev]}) != 2400:
        raise RuntimeError("Stage8 exact stage duplicate detected")
    train_families = {str(row["semantic_family_id"]) for row in train}
    dev_families = {str(row["semantic_family_id"]) for row in dev}
    if train_families & dev_families:
        raise RuntimeError("Stage8 semantic family crosses train/dev")
    contrast_counts = Counter(
        str(row["contrast_group"])
        for row in [*train, *dev]
        if row["failure_cluster"] != "stage7_safety_anchor"
    )
    if set(contrast_counts.values()) != {4} or len(contrast_counts) != 500:
        raise RuntimeError("Stage8 contrast groups are not 500 groups x 4 states")
    contamination = round1._holdout_contamination(
        [*anchor_contamination, *candidates]
    )

    OUTPUT.mkdir(parents=True)
    write_jsonl(OUTPUT / "stage_sft.train.jsonl", train)
    write_jsonl(OUTPUT / "stage_sft.dev.jsonl", dev)
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        ({"prompt": row["prompt"], "target": row["target"], "text": row["text"]} for row in train),
    )
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        ({"prompt": row["prompt"], "target": row["target"], "text": row["text"]} for row in dev),
    )
    write_jsonl(OUTPUT / "controller_replay_validation.jsonl", validations)
    files = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "artifact_kind": "failure_grounded_factory_surface_controller_replayed_state_contrast",
        "purpose": "Correct premature continuation after exact local evidence and repeated successful idempotent workspace mutation without generic task SFT.",
        "training_ready": False,
        "local_validation_complete": True,
        "remote_tokenizer_validated": False,
        "strong_model_as_label_source": False,
        "controller_replay": True,
        "counts": {
            "train": len(train),
            "dev": len(dev),
            "factory_surface_families": len(cards),
            "contrast_groups": len(contrast_counts),
            "controller_replayed_trajectories": len(candidates),
            "train_clusters": dict(expected_train),
            "dev_clusters": dict(expected_dev),
        },
        "validation": {
            "controller_replay_rate": 1.0,
            "target_parse_rate": 1.0,
            "contrast_group_size": 4,
            "exact_stage_duplicate_count": 0,
            "train_dev_family_overlap_count": 0,
            "contamination": contamination,
        },
        "source": {
            "seed_plan_sha256": sha256(SEED / "seed_plan.jsonl"),
            "factory_manifest_sha256": sha256(SURFACES / "manifest.json"),
            "factory_surface_cards_sha256": sha256(SURFACES / "surface_cards.jsonl"),
            "factory_generator_source": str(FACTORY_SOURCE),
            "factory_generator_sha256": sha256(FACTORY_SOURCE),
            "generator_sha256": sha256(Path(__file__)),
        },
        "training_contract": {
            "training_file": "rwkv_state_tuning.train.requires_target_suffix.jsonl",
            "development_file": "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "ctx_len": 2496,
            "peft": "state",
            "op": "fla",
            "seed": 834,
            "parent": "stage7-step1500",
        },
        "remote": {
            "ssh_alias": "rwkv-8222",
            "project_dir": "/home/chase/chase/RWKV-PEFT",
            "upload_dir": "/home/chase/chase/RWKV-PEFT/data/rwkv_lh_state_tuning_stage8_mutation_stop_v1",
            "gpu": 0,
        },
        "files": files,
        "generation": f"uv run python {Path(__file__).resolve()}",
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"] | {"contamination": contamination}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
