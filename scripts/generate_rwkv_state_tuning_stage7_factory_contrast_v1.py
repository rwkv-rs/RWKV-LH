"""Build Stage7 from strong-model surface cards and deterministic Harness labels."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from rwkv_lh.model_io import parse_tool_selection

from scripts import generate_rwkv_action_state_tuning_round1_2k_v1 as round1
from scripts import generate_rwkv_action_state_tuning_v1 as pilot
from scripts import generate_rwkv_state_tuning_stage3_natural_route_stop_v1 as stage3


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/datasets/rwkv_lh_state_tuning_stage7_factory_seed_v1"
SURFACES = ROOT / "data/datasets/rwkv_lh_state_tuning_stage7_factory_surfaces_v1"
FACTORY_SOURCE = (
    ROOT.parent
    / "RWKV-state-factory/rwkv_web_retrieval_state_factory/surface_synthesis.py"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage7_factory_contrast_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_STATE_TUNING_STAGE7_FACTORY_CONTRAST_V1_20260827"
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
VERSION = "rwkv-lh.state-tuning.stage7-factory-contrast.v1"
FACTORY_SCHEMA = "rwkv-surface-factory.cards.v1"
SIGNATURES = {
    "phase_evidence_contrast": "FST-S7-001",
    "web_connector_role_contrast": "FST-S7-002",
    "mixed_privacy_local_first": "FST-S7-003",
    "no_progress_success_stop": "FST-S7-004",
    "stage1_safety_anchor": "FST-S7-005",
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


def base_candidate(
    card: Mapping[str, Any], lane: str, variant: int, *, language: str
) -> dict[str, Any]:
    surface_id = str(card["surface_id"])
    split = str(card["split"])
    family_id = f"AST-S7-SF-{surface_id}"
    return {
        "schema_version": pilot.CANDIDATE_SCHEMA,
        "trajectory_id": f"AST-S7-{surface_id}-{lane}-{variant + 1:02d}",
        "factory_surface_id": surface_id,
        "source_seed_id": str(card["seed_id"]),
        "semantic_family_id": family_id,
        "split": split,
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
        "contrast_group": family_id,
    }


def turn_final(text: str, reason: str) -> dict[str, Any]:
    return pilot._turn("final_answer", {"text": text}, reason)


def phase_candidates(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = dict(card["fields"])
    result: list[dict[str, Any]] = []
    nonce = str(card["surface_id"]).lower()
    for variant, language in enumerate(("zh", "en")):
        row = base_candidate(card, "phase", variant, language=language)
        path = f"factory/phase/{nonce}-{variant + 1}.txt"
        marker = f"observed-{nonce}-{variant + 1}"
        template = fields[f"{language}_request_template"]
        row.update(
            {
                "request": str(template).replace("{path}", path).replace(
                    "{marker}", marker
                ),
                "workspace_files": [pilot._workspace_file(path, marker + "\n")],
                "turns": [
                    pilot._turn("read_file", {"path": path}, "initial"),
                    turn_final(
                        (
                            f"已从指定本地证据确认标记 {marker}。"
                            if language == "zh"
                            else f"Confirmed marker {marker} from the specified local evidence."
                        ),
                        "after_required_evidence",
                    ),
                ],
            }
        )
        result.append(row)
    return result


def role_candidates(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = dict(card["fields"])
    result: list[dict[str, Any]] = []
    nonce = int(card["ordinal"])
    entity = f"{fields['entity_stem']} {str(card['surface_id']).split('-')[-1]}"
    connector_operations = (
        "github_repository",
        "github_release",
        "github_commit",
        "github_code",
        "package_release",
        "scholarly_record",
        "weather",
        "weather_alerts",
    )
    operation = connector_operations[nonce % len(connector_operations)]
    for language in ("zh", "en"):
        for lane in ("web", "connector"):
            variant = len(result)
            row = base_candidate(card, lane, variant, language=language)
            template = fields[f"{language}_{lane}_request_template"]
            if lane == "web":
                target = pilot._turn(
                    "web_search", {"query": entity, "max_results": 5}, "initial"
                )
            else:
                target = pilot._turn(
                    "connector_lookup",
                    {"operation": operation, "query": entity},
                    "initial",
                )
            row.update(
                {
                    "network_policy": "auto_public",
                    "request": str(template).replace("{entity}", entity),
                    "turns": [target],
                    "expected_backend_executions": 1,
                }
            )
            result.append(row)
    return result


def mixed_privacy_candidates(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = dict(card["fields"])
    language = "zh" if int(card["ordinal"]) % 2 == 0 else "en"
    nonce = str(card["surface_id"]).lower()
    result: list[dict[str, Any]] = []

    mixed = base_candidate(card, "mixed", 0, language=language)
    mixed_path = f"factory/mixed/{nonce}.txt"
    query = f"{fields['entity_stem']} public notice {nonce}"
    mixed.update(
        {
            "network_policy": "auto_public",
            "request": str(fields[f"{language}_mixed_request_template"]).replace(
                "{path}", mixed_path
            ),
            "workspace_files": [pilot._workspace_file(mixed_path, query + "\n")],
            "turns": [
                pilot._turn("read_file", {"path": mixed_path}, "initial"),
                pilot._turn(
                    "web_search", {"query": query, "max_results": 5}, "after_read"
                ),
            ],
            "expected_backend_executions": 1,
        }
    )
    result.append(mixed)

    # The existing privacy seed supplies provenance labels and the typed Gate
    # rejection; the Factory changes only the public request surface.
    privacy_seed = "ST-ACT-013" if int(card["ordinal"]) % 2 == 0 else "ST-ACT-014"
    privacy = pilot._instantiate(
        privacy_seed,
        7000 + int(card["ordinal"]) + (0 if card["split"] == "train" else 1000),
        int(card["ordinal"]) % 4,
    )
    privacy_path = str(privacy["workspace_files"][0]["path"])
    privacy.update(
        {
            "trajectory_id": f"AST-S7-{card['surface_id']}-privacy-01",
            "factory_seed_id": str(card["seed_id"]),
            "factory_surface_id": str(card["surface_id"]),
            "semantic_family_id": mixed["semantic_family_id"],
            "split": str(card["split"]),
            "language": language,
            "request": str(fields[f"{language}_privacy_request_template"]).replace(
                "{path}", privacy_path
            ),
            "failure_cluster": str(card["cluster"]),
            "failure_signature_id": SIGNATURES[str(card["cluster"])],
            "contrast_group": mixed["semantic_family_id"],
        }
    )
    result.append(privacy)
    return result


def stop_candidates(
    card: Mapping[str, Any],
) -> list[tuple[dict[str, Any], Sequence[tuple[str, int | str]]]]:
    fields = dict(card["fields"])
    nonce = str(card["surface_id"]).lower()
    language = "zh" if int(card["ordinal"]) % 2 == 0 else "en"
    other_language = "en" if language == "zh" else "zh"
    success = base_candidate(card, "success", 0, language=language)
    path = f"factory/stop/{nonce}.txt"
    marker = f"complete-{nonce}"
    success.update(
        {
            "request": str(fields[f"{language}_success_request_template"]).replace(
                "{path}", path
            ),
            "workspace_files": [pilot._workspace_file(path, marker + "\n")],
            "turns": [
                pilot._turn("read_file", {"path": path}, "initial"),
                turn_final(
                    (
                        f"本地观察已成功完成：{marker}。"
                        if language == "zh"
                        else f"The local observation completed successfully: {marker}."
                    ),
                    "after_required_evidence",
                ),
            ],
        }
    )

    unavailable = unavailable_candidate(card, other_language)
    prelude = unavailable["prelude"][0]
    operation = str(prelude["operation"])
    params = dict(prelude["params"])
    route = base_candidate(card, "unavailable-route", 1, language=other_language)
    route.update(
        {
            "network_policy": "auto_public",
            "request": unavailable["request"],
            "turns": [pilot._turn(operation, params, "initial")],
            "expected_backend_executions": 1,
        }
    )
    return [
        (success, (("turn", 0), ("operation", "final_answer"))),
        (route, (("turn", 0),)),
        (unavailable, (("operation", "final_answer"),)),
    ]


def unavailable_candidate(card: Mapping[str, Any], language: str) -> dict[str, Any]:
    fields = dict(card["fields"])
    row = pilot._instantiate(
        "ST-ACT-017",
        9000 + int(card["ordinal"]) + (0 if card["split"] == "train" else 1000),
        0 if language == "zh" else 1,
    )
    query = str(row["prelude"][0]["params"].get("query") or "fictional current fact")
    row.update(
        {
            "trajectory_id": f"AST-S7-{card['surface_id']}-unavailable-{language}",
            "factory_seed_id": str(card["seed_id"]),
            "factory_surface_id": str(card["surface_id"]),
            "semantic_family_id": f"AST-S7-SF-{card['surface_id']}",
            "split": str(card["split"]),
            "language": language,
            "request": str(fields[f"{language}_unavailable_request_template"]).replace(
                "{query}", query
            ),
            "failure_cluster": str(card["cluster"]),
            "failure_signature_id": SIGNATURES[str(card["cluster"])],
            "contrast_group": f"AST-S7-SF-{card['surface_id']}",
        }
    )
    return row


def select_stages(
    candidate: Mapping[str, Any], selectors: Sequence[tuple[str, int | str]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    positive, validation, _rejected = pilot._replay(candidate)
    selected: list[dict[str, Any]] = []
    for kind, value in selectors:
        if kind == "turn":
            matches = [
                dict(row)
                for row in positive
                if row["stage"] == "selector" and int(row["turn_index"]) == int(value)
            ]
        elif kind == "operation":
            matches = [
                dict(row)
                for row in positive
                if row["stage"] == "selector" and row["target_operation"] == value
            ]
        else:
            raise ValueError(kind)
        if len(matches) != 1:
            raise RuntimeError(
                f"selector {kind}={value} missing for {candidate['trajectory_id']}"
            )
        row = matches[0]
        if parse_tool_selection(str(row["target"])) != row["target_operation"]:
            raise RuntimeError(f"invalid selector target: {candidate['trajectory_id']}")
        row.update(
            {
                "schema_version": "rwkv-lh.failure-grounded-action-stage-sft.v1",
                "failure_cluster": candidate["failure_cluster"],
                "failure_signature_id": candidate["failure_signature_id"],
                "training_intent": "matched_state_contrast_not_generic_task_sft",
                "contrast_group": candidate["contrast_group"],
                "surface_id": str(candidate["factory_surface_id"]),
            }
        )
        selected.append(row)
    return selected, validation


def replay_card(card: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cluster = str(card["cluster"])
    rows: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    if cluster == "phase_evidence_contrast":
        for candidate in phase_candidates(card):
            picked, validation = select_stages(
                candidate, (("turn", 0), ("operation", "final_answer"))
            )
            rows.extend(picked)
            validations.append({"surface_id": card["surface_id"], **validation})
            candidates.append(candidate)
    elif cluster == "web_connector_role_contrast":
        for candidate in role_candidates(card):
            picked, validation = select_stages(candidate, (("turn", 0),))
            rows.extend(picked)
            validations.append({"surface_id": card["surface_id"], **validation})
            candidates.append(candidate)
    elif cluster == "mixed_privacy_local_first":
        for candidate in mixed_privacy_candidates(card):
            network_operation = next(
                str(turn["target_operation"])
                for turn in candidate["turns"]
                if turn["target_operation"] in {"web_search", "connector_lookup"}
            )
            picked, validation = select_stages(
                candidate, (("turn", 0), ("operation", network_operation))
            )
            rows.extend(picked)
            validations.append({"surface_id": card["surface_id"], **validation})
            candidates.append(candidate)
    elif cluster == "no_progress_success_stop":
        for candidate, selectors in stop_candidates(card):
            picked, validation = select_stages(candidate, selectors)
            rows.extend(picked)
            validations.append({"surface_id": card["surface_id"], **validation})
            candidates.append(candidate)
    else:
        raise ValueError(cluster)
    if len(rows) != 4:
        raise RuntimeError(f"surface family did not produce four stages: {card['surface_id']}")
    return rows, validations, candidates


def stable_anchor_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, contamination = stage3.stable_rows()
    # Deterministic 80% stratified retention: remove every fifth source row.
    selected = [dict(row) for index, row in enumerate(rows) if index % 5 != 4]
    if len(selected) != 400:
        raise RuntimeError(f"Stage1 safety anchor count changed: {len(selected)}")
    for index, row in enumerate(selected):
        row.update(
            {
                "failure_cluster": "stage1_safety_anchor",
                "failure_signature_id": SIGNATURES["stage1_safety_anchor"],
                "training_intent": "preserve_stage1_selector_safety_and_stopping",
                "contrast_group": f"AST-S7-ANCHOR-{index + 1:04d}",
            }
        )
    return selected, contamination


def interleave_key(row: Mapping[str, Any]) -> str:
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
    for required in (
        PREREGISTRATION,
        SEED / "seed_plan.jsonl",
        SURFACES / "manifest.json",
        SURFACES / "surface_cards.jsonl",
        FACTORY_SOURCE,
    ):
        if not required.is_file():
            raise FileNotFoundError(required)
    factory_manifest = read_json(SURFACES / "manifest.json")
    if factory_manifest["schema_version"] != FACTORY_SCHEMA or factory_manifest[
        "card_count"
    ] != 500:
        raise RuntimeError("Factory surface manifest does not contain frozen 500 cards")
    cards = read_jsonl(SURFACES / "surface_cards.jsonl")
    if len(cards) != 500:
        raise RuntimeError("Factory surface card count changed")

    stages: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    raw_candidates: list[dict[str, Any]] = []
    for index, card in enumerate(cards, 1):
        try:
            picked, reports, candidates = replay_card(card)
        except Exception as exc:
            raise RuntimeError(
                f"Stage7 replay failed at {index}/500 for {card['surface_id']}"
            ) from exc
        stages.extend(picked)
        validations.extend(reports)
        raw_candidates.extend(candidates)
        if index % 25 == 0:
            print(f"controller replay {index}/500", flush=True)

    anchors, anchor_contamination = stable_anchor_rows()
    train = [row for row in stages if row["split"] == "train"] + anchors
    dev = [row for row in stages if row["split"] == "dev"]
    train.sort(key=interleave_key)
    dev.sort(key=interleave_key)
    expected_train = Counter(
        {
            "phase_evidence_contrast": 400,
            "web_connector_role_contrast": 400,
            "mixed_privacy_local_first": 400,
            "no_progress_success_stop": 400,
            "stage1_safety_anchor": 400,
        }
    )
    expected_dev = Counter(
        {
            "phase_evidence_contrast": 100,
            "web_connector_role_contrast": 100,
            "mixed_privacy_local_first": 100,
            "no_progress_success_stop": 100,
        }
    )
    if Counter(row["failure_cluster"] for row in train) != expected_train:
        raise RuntimeError("Stage7 train quota changed")
    if Counter(row["failure_cluster"] for row in dev) != expected_dev:
        raise RuntimeError("Stage7 dev quota changed")
    if len(train) != 2000 or len(dev) != 400:
        raise RuntimeError(f"Stage7 split count changed: {len(train)}, {len(dev)}")
    if len({row["text"] for row in [*train, *dev]}) != 2400:
        raise RuntimeError("Stage7 exact stage duplicate detected")
    train_families = {str(row["semantic_family_id"]) for row in train}
    dev_families = {str(row["semantic_family_id"]) for row in dev}
    if train_families & dev_families:
        raise RuntimeError("Stage7 semantic family crosses train/dev")
    contrast_counts = Counter(
        str(row["contrast_group"])
        for row in [*train, *dev]
        if row["failure_cluster"] != "stage1_safety_anchor"
    )
    if set(contrast_counts.values()) != {4} or len(contrast_counts) != 500:
        raise RuntimeError("Stage7 contrast groups are not 500 groups x 4 stages")
    privacy_backend = sum(
        int(row["backend_execution_count"])
        for row in validations
        if row.get("trajectory_id", "").find("privacy") >= 0
    )
    if privacy_backend:
        raise RuntimeError(f"privacy backend execution count={privacy_backend}")
    contamination = round1._holdout_contamination(
        [*anchor_contamination, *raw_candidates]
    )

    OUTPUT.mkdir(parents=True)
    write_jsonl(OUTPUT / "stage_sft.train.jsonl", train)
    write_jsonl(OUTPUT / "stage_sft.dev.jsonl", dev)
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        (
            {"prompt": row["prompt"], "target": row["target"], "text": row["text"]}
            for row in train
        ),
    )
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        (
            {"prompt": row["prompt"], "target": row["target"], "text": row["text"]}
            for row in dev
        ),
    )
    write_jsonl(OUTPUT / "controller_replay_validation.jsonl", validations)
    write_json(
        OUTPUT / "residual_registry.json",
        {
            "schema_version": "rwkv-lh.stage7-residuals.v1",
            "source": "Frozen Stage4-6 results and Stage1 Shadow canary",
            "residuals": {
                "state_phase_leakage": "Stage5 stop 1/120 but mixed 3/20 and privacy 3/10",
                "surface_narrowing": "Stage6 own web 48/48 vs ECRA web 16/25; own connector 39/48 vs ECRA 8/20",
                "destructive_superposition": "Stage6 mixed recovered to 14/20 while required-online FNR rose to 0.2769",
            },
            "correction": "Factory surface diversity plus matched state contrast; labels remain deterministic Harness outputs",
        },
    )
    (OUTPUT / "README.md").write_text(
        "# RWKV-LH Stage7 Factory contrast state tuning\n\n"
        "Two thousand train selectors and four hundred family-disjoint dev selectors. "
        "Strong-model Factory output owns only public wording; every target is rendered "
        "by the current progressive Controller and verified by ActionHarness.\n",
        encoding="utf-8",
    )
    files = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "artifact_kind": "factory_surface_expanded_harness_verified_matched_state_contrast",
        "purpose": "Correct evidence-phase leakage and web/connector surface narrowing without generic task SFT.",
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
            "train_clusters": dict(expected_train),
            "dev_clusters": dict(expected_dev),
            "train_semantic_families": len(train_families),
            "dev_semantic_families": len(dev_families),
        },
        "validation": {
            "controller_replay_rate": 1.0,
            "target_parse_rate": 1.0,
            "contrast_group_size": 4,
            "privacy_backend_execution_count": privacy_backend,
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
            "preregistration_sha256": sha256(PREREGISTRATION),
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
            "seed": 833,
            "lr_init": "3e-6",
            "lr_final": "6e-7",
            "parent": "stage4-step1140-experimental",
            "checkpoint_steps": [500, 1000, 1500, 2000],
        },
        "remote": {
            "ssh_alias": "rwkv-8222",
            "project_dir": "/home/chase/chase/RWKV-PEFT",
            "upload_dir": "/home/chase/chase/RWKV-PEFT/data/rwkv_lh_state_tuning_stage7_factory_contrast_v1",
            "gpu": 0,
        },
        "files": files,
        "generation": f"uv run python {Path(__file__).resolve()}",
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(
        json.dumps(
            manifest["counts"] | {"contamination": contamination},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
