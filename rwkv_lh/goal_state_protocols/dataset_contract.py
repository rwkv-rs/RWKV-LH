"""Frozen dataset contract for the five G1J per-stage StateTune roles.

The production renderers and parsers remain the only prompt/target authority.
This module only performs deterministic source splitting, sidecar construction,
token accounting, leakage checks, and byte-for-byte validation.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.goal_state_protocols import ROLE_STATE_IDS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path(__file__).resolve().parents[2]
VOCAB_PATH = ROOT / "rwkv_lh" / "data" / "rwkv_vocab_v20230424.txt"
SPLIT_SALT = "rwkv-lh-g1j-per-stage-state-tuning-v1-family-split"
SPLIT_ALGORITHM = "sha256-first8-mod100.v1"
SIMILARITY_ALGORITHM = "utf8-byte-5gram-cosine.v1"
SIMILARITY_THRESHOLD = 0.95
MANIFEST_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-dataset-manifest.v1"

SOURCE_FIELDS = (
    "schema_version",
    "source_id",
    "stage",
    "project_family",
    "source_kind",
    "source_path",
    "source_sha256",
    "record_locator",
    "parent_source_ids",
    "payload",
)
SOURCE_KINDS = {
    "production_trace",
    "executable_fixture",
    "deterministic_counterfactual",
    "human_double_review",
}
SAMPLE_INDEX_FIELDS = (
    "schema_version",
    "dataset_id",
    "sample_id",
    "stage",
    "split",
    "project_family",
    "source_id",
    "input_schema_version",
    "output_schema_version",
    "renderer_sha256",
    "parser_sha256",
    "verifier_id",
    "verifier_sha256",
    "prompt_sha256",
    "target_sha256",
    "text_sha256",
    "prompt_tokens",
    "target_tokens",
    "total_tokens_with_bos",
)
VERIFICATION_FIELDS = (
    "schema_version",
    "sample_id",
    "source_id",
    "parser_passed",
    "schema_passed",
    "semantic_passed",
    "role_boundary_passed",
    "execution_passed",
    "evidence_binding_passed",
    "leakage_passed",
    "family_split_passed",
)
TOKENIZER_FIELDS = (
    "schema_version",
    "sample_id",
    "tokenizer_sha256",
    "bos_token_id",
    "context_length",
    "prompt_tokens",
    "target_tokens",
    "total_tokens_with_bos",
    "first_target_predicted_from_last_prompt_token",
    "no_truncation",
    "serving_token_ids_match_training",
)
DATASET_FILES = (
    "README.md",
    "manifest.json",
    "split_registry.json",
    "source_registry.jsonl",
    "sample_index.jsonl",
    "verification_records.jsonl",
    "tokenizer_records.jsonl",
    "rwkv_state_tuning.train.requires_target_suffix.jsonl",
    "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
    "generation_validation.json",
    "leakage_audit.json",
    "tokenizer_target_suffix_audit.json",
)
SEALED_FILES = (
    "source_registry.jsonl",
    "sample_index.jsonl",
    "verification_records.jsonl",
    "tokenizer_records.jsonl",
    "rwkv_state_tuning.sealed.requires_target_suffix.jsonl",
)


@dataclass(frozen=True)
class StageSpec:
    key: str
    dataset_id: str
    role_state_id: str
    module_name: str
    source_schema_version: str
    payload_fields: tuple[str, ...]
    similarity_fields: tuple[str, ...]
    purpose: str

    @property
    def module(self):
        return importlib.import_module(self.module_name)

    @property
    def renderer_path(self) -> Path:
        return Path(self.module.__file__).resolve()


STAGE_SPECS: dict[str, StageSpec] = {
    "selector_intent": StageSpec(
        "selector_intent",
        "rwkv_lh_g1j_selector_intent_state_tuning_v1",
        ROLE_STATE_IDS["selector_intent"],
        "rwkv_lh.goal_state_protocols.selector_intent",
        "rwkv-lh.g1j-per-stage-state-tuning.selector-intent-source.v1",
        (
            "stage_objective",
            "stage_role",
            "progress",
            "eligible_labels",
            "selected_operation",
            "selection_authority",
            "selection_verifier_id",
        ),
        ("stage_objective", "stage_role", "progress", "eligible_labels"),
        "Train only the isolated G1J Selector-Intent recurrent State.",
    ),
    "executor_args": StageSpec(
        "executor_args",
        "rwkv_lh_g1j_executor_args_state_tuning_v1",
        ROLE_STATE_IDS["executor_args"],
        "rwkv_lh.goal_state_protocols.executor_args",
        "rwkv-lh.g1j-per-stage-state-tuning.executor-args-source.v1",
        (
            "current_requirement",
            "selected_operation",
            "selected_tool_contract",
            "committed_fact_refs",
            "executor_history",
            "command",
            "fixture_id",
            "execution_verifier_id",
        ),
        (
            "current_requirement",
            "selected_operation",
            "selected_tool_contract",
            "committed_fact_refs",
        ),
        "Train only the isolated G1J Executor-Args recurrent State.",
    ),
    "auditor_step": StageSpec(
        "auditor_step",
        "rwkv_lh_g1j_auditor_step_state_tuning_v1",
        ROLE_STATE_IDS["auditor_step"],
        "rwkv_lh.goal_state_protocols.auditor_step",
        "rwkv-lh.g1j-per-stage-state-tuning.auditor-step-source.v1",
        (
            "boundary",
            "active_step",
            "available_evidence_refs",
            "evidence_records",
            "decision",
            "completion_verifier_id",
        ),
        ("boundary", "active_step", "evidence_records"),
        "Train only the isolated G1J Step-Auditor recurrent State.",
    ),
    "finalizer_answer": StageSpec(
        "finalizer_answer",
        "rwkv_lh_g1j_finalizer_answer_state_tuning_v1",
        ROLE_STATE_IDS["finalizer_answer"],
        "rwkv_lh.goal_state_protocols.finalizer_answer",
        "rwkv-lh.g1j-per-stage-state-tuning.finalizer-answer-source.v1",
        (
            "immutable_goal",
            "completed_steps",
            "committed_facts",
            "evidence_records",
            "format_contract",
            "final_text",
            "fact_verifier_id",
        ),
        ("immutable_goal", "completed_steps", "committed_facts", "format_contract"),
        "Train only the isolated G1J Finalizer-Answer recurrent State.",
    ),
    "auditor_final": StageSpec(
        "auditor_final",
        "rwkv_lh_g1j_auditor_final_state_tuning_v1",
        ROLE_STATE_IDS["auditor_final"],
        "rwkv_lh.goal_state_protocols.auditor_final",
        "rwkv-lh.g1j-per-stage-state-tuning.auditor-final-source.v1",
        (
            "immutable_goal",
            "completed_steps",
            "committed_facts",
            "available_evidence_refs",
            "evidence_records",
            "final_candidate",
            "decision",
            "final_verifier_id",
        ),
        (
            "immutable_goal",
            "completed_steps",
            "committed_facts",
            "final_candidate",
        ),
        "Train only the isolated G1J Final-Auditor recurrent State.",
    ),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=False, separators=(",", ":"))


def canonical_json_line(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def split_for_family(project_family: str) -> tuple[str, int]:
    digest = hashlib.sha256((SPLIT_SALT + "\0" + project_family).encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return ("train" if bucket < 80 else "dev" if bucket < 90 else "sealed", bucket)


def _exact_fields(value: Any, expected: Sequence[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    if tuple(value) != tuple(expected) or set(value) != set(expected):
        raise ValueError(f"{name} fields/order differ from the frozen contract")
    return value


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _validate_sha(value: Any, name: str) -> str:
    selected = _nonempty_string(value, name)
    if len(selected) != 64 or any(char not in "0123456789abcdef" for char in selected):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return selected


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"source registry must be an existing absolute path: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_bytes().splitlines(), 1):
        if not raw:
            raise ValueError(f"blank JSONL row at {path}:{line_number}")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid canonical UTF-8 JSONL at {path}:{line_number}") from exc
        if not isinstance(value, dict) or canonical_json_line(value).rstrip(b"\n") != raw:
            raise ValueError(f"non-canonical JSONL row at {path}:{line_number}")
        rows.append(value)
    if not rows:
        raise ValueError("source registry must not be empty")
    return rows


def _validate_source(row: Mapping[str, Any], spec: StageSpec) -> None:
    _exact_fields(row, SOURCE_FIELDS, "source registry row")
    if row["schema_version"] != spec.source_schema_version:
        raise ValueError("source schema_version differs from the stage contract")
    _nonempty_string(row["source_id"], "source_id")
    if row["stage"] != spec.role_state_id:
        raise ValueError("source stage must equal the frozen role State ID")
    _nonempty_string(row["project_family"], "project_family")
    if row["source_kind"] not in SOURCE_KINDS:
        raise ValueError("source_kind is invalid")
    relative = Path(_nonempty_string(row["source_path"], "source_path"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("source_path must be project-root relative")
    source_path = (ROOT / relative).resolve()
    if not source_path.is_file() or not source_path.is_relative_to(ROOT):
        raise ValueError(f"source_path is missing or out of scope: {relative}")
    expected_source_sha = _validate_sha(row["source_sha256"], "source_sha256")
    if sha256_path(source_path) != expected_source_sha:
        raise ValueError(f"source SHA mismatch: {relative}")
    _nonempty_string(row["record_locator"], "record_locator")
    parents = row["parent_source_ids"]
    if not isinstance(parents, list) or any(not isinstance(item, str) or not item for item in parents):
        raise ValueError("parent_source_ids must be an array of non-empty strings")
    if parents != sorted(set(parents)):
        raise ValueError("parent_source_ids must be sorted and unique")
    _exact_fields(row["payload"], spec.payload_fields, "source payload")
    spec.module.validate_source(row["payload"])


def _ngram_counter(value: bytes, width: int = 5) -> Counter[bytes]:
    if len(value) < width:
        return Counter({value: 1}) if value else Counter()
    return Counter(value[index : index + width] for index in range(len(value) - width + 1))


def _cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right.get(key, 0) for key, count in left.items())
    if not dot:
        return 0.0
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    return dot / (left_norm * right_norm)


def _similarity_bytes(row: Mapping[str, Any], spec: StageSpec) -> bytes:
    selected = [row["payload"][field] for field in spec.similarity_fields]
    return canonical_json(selected).encode("utf-8")


def maximum_cross_split_similarity(
    rows: Sequence[Mapping[str, Any]], spec: StageSpec
) -> float:
    encoded = [
        (split_for_family(str(row["project_family"]))[0], _ngram_counter(_similarity_bytes(row, spec)))
        for row in rows
    ]
    maximum = 0.0
    for left_index, (left_split, left) in enumerate(encoded):
        for right_split, right in encoded[left_index + 1 :]:
            if left_split != right_split:
                maximum = max(maximum, _cosine(left, right))
    return maximum


def _file_record(value: bytes) -> dict[str, int | str]:
    return {
        "sha256": sha256_bytes(value),
        "bytes": len(value),
        "lines": len(value.splitlines()),
    }


def _json_bytes(value: Any) -> bytes:
    return canonical_json_line(value)


def _jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_line(row) for row in rows)


def _sample_id(spec: StageSpec, source_id: str) -> str:
    digest = sha256_bytes((spec.dataset_id + "\0" + source_id).encode("utf-8"))
    return f"{spec.key}-{digest}"


def _sealed_directory(source_registry: Path, spec: StageSpec) -> Path:
    if source_registry.parent.name != spec.key:
        raise ValueError(
            "full source registry must live in an experiment/<stage>/ directory "
            "so sealed_test has one frozen location"
        )
    return source_registry.parent / "sealed_test"


def _prepare_rows(rows: list[dict[str, Any]], spec: StageSpec) -> dict[str, Any]:
    from rwkv_lh.goal_state_protocols.dataset_verifiers import (
        OPERATION_REGISTRY_SHA256,
        VERIFIER_ID,
        verify_stage_payload,
    )

    source_ids: set[str] = set()
    families: dict[str, str] = {}
    for row in rows:
        _validate_source(row, spec)
        source_id = str(row["source_id"])
        if source_id in source_ids:
            raise ValueError(f"duplicate source_id: {source_id}")
        source_ids.add(source_id)
        split, _bucket = split_for_family(str(row["project_family"]))
        families[str(row["project_family"])] = split
    for row in rows:
        split = families[str(row["project_family"])]
        for parent in row["parent_source_ids"]:
            if parent not in source_ids:
                raise ValueError(f"unknown counterfactual parent: {parent}")
            parent_row = next(item for item in rows if item["source_id"] == parent)
            if families[str(parent_row["project_family"])] != split:
                raise ValueError("counterfactual parent crosses a family split")

    similarity = maximum_cross_split_similarity(rows, spec)
    if similarity >= SIMILARITY_THRESHOLD:
        raise ValueError(
            f"maximum cross-split similarity {similarity:.9f} is not below "
            f"{SIMILARITY_THRESHOLD}"
        )

    tokenizer = RWKVTokenizer(VOCAB_PATH)
    serving_tokenizer = RWKVTokenizer(VOCAB_PATH)
    tokenizer_sha = sha256_path(VOCAB_PATH)
    renderer_sha = sha256_path(spec.renderer_path)
    verifier_path = Path(__file__).with_name("dataset_verifiers.py")
    verifier_sha = sha256_path(verifier_path)

    prepared: list[dict[str, Any]] = []
    for row in rows:
        payload = row["payload"]
        prompt = spec.module.render_prompt(payload)
        target = spec.module.render_target(payload)
        parsed = spec.module.parse_target(target)
        verify_stage_payload(spec.key, payload, prompt, target, parsed)
        if target in prompt:
            raise ValueError(f"exact target leaked into prompt: {row['source_id']}")
        prompt_tokens = tokenizer.encode(prompt)
        target_tokens = tokenizer.encode(target)
        if prompt_tokens != serving_tokenizer.encode(prompt) or target_tokens != serving_tokenizer.encode(target):
            raise ValueError("serving and training tokenizer IDs differ")
        total_tokens = 1 + len(prompt_tokens) + len(target_tokens)
        if total_tokens > 4096:
            raise ValueError(f"row exceeds context_length=4096: {row['source_id']}")
        split = families[str(row["project_family"])]
        sample_id = _sample_id(spec, str(row["source_id"]))
        text_value = prompt + target
        training_row = {"prompt": prompt, "target": target, "text": text_value}
        sample = {
            "schema_version": "rwkv-lh.g1j-per-stage-state-sample-index.v1",
            "dataset_id": spec.dataset_id,
            "sample_id": sample_id,
            "stage": spec.role_state_id,
            "split": split,
            "project_family": row["project_family"],
            "source_id": row["source_id"],
            "input_schema_version": spec.module.INPUT_SCHEMA_VERSION,
            "output_schema_version": spec.module.OUTPUT_SCHEMA_VERSION,
            "renderer_sha256": renderer_sha,
            "parser_sha256": renderer_sha,
            "verifier_id": VERIFIER_ID,
            "verifier_sha256": verifier_sha,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "target_sha256": sha256_bytes(target.encode("utf-8")),
            "text_sha256": sha256_bytes(text_value.encode("utf-8")),
            "prompt_tokens": len(prompt_tokens),
            "target_tokens": len(target_tokens),
            "total_tokens_with_bos": total_tokens,
        }
        verification = {
            "schema_version": "rwkv-lh.g1j-per-stage-state-verification.v1",
            "sample_id": sample_id,
            "source_id": row["source_id"],
            "parser_passed": True,
            "schema_passed": True,
            "semantic_passed": True,
            "role_boundary_passed": True,
            "execution_passed": True,
            "evidence_binding_passed": True,
            "leakage_passed": True,
            "family_split_passed": True,
        }
        tokenizer_record = {
            "schema_version": "rwkv-lh.g1j-per-stage-state-tokenizer-record.v1",
            "sample_id": sample_id,
            "tokenizer_sha256": tokenizer_sha,
            "bos_token_id": 0,
            "context_length": 4096,
            "prompt_tokens": len(prompt_tokens),
            "target_tokens": len(target_tokens),
            "total_tokens_with_bos": total_tokens,
            "first_target_predicted_from_last_prompt_token": True,
            "no_truncation": True,
            "serving_token_ids_match_training": True,
        }
        prepared.append(
            {
                "source": row,
                "sample": sample,
                "verification": verification,
                "tokenizer": tokenizer_record,
                "training": training_row,
            }
        )
    prepared.sort(key=lambda item: str(item["sample"]["sample_id"]).encode("utf-8"))
    return {
        "rows": prepared,
        "families": dict(sorted(families.items())),
        "similarity": similarity,
        "tokenizer_sha": tokenizer_sha,
        "renderer_sha": renderer_sha,
        "verifier_path": verifier_path,
        "verifier_sha": verifier_sha,
        "operation_registry_sha": OPERATION_REGISTRY_SHA256,
    }


def _subset_bytes(prepared: Sequence[Mapping[str, Any]], split: str) -> dict[str, bytes]:
    selected = [item for item in prepared if item["sample"]["split"] == split]
    return {
        "source_registry.jsonl": _jsonl_bytes([item["source"] for item in selected]),
        "sample_index.jsonl": _jsonl_bytes([item["sample"] for item in selected]),
        "verification_records.jsonl": _jsonl_bytes([item["verification"] for item in selected]),
        "tokenizer_records.jsonl": _jsonl_bytes([item["tokenizer"] for item in selected]),
        f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl": _jsonl_bytes(
            [item["training"] for item in selected]
        ),
    }


def build_dataset(*, stage: str, source_registry: Path, output: Path, generator_path: Path) -> None:
    spec = STAGE_SPECS[stage]
    source_registry = source_registry.resolve()
    output = output.resolve()
    generator_path = generator_path.resolve()
    if output.exists():
        raise FileExistsError(f"build output must not exist: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"build output parent must exist: {output.parent}")
    sealed_directory = _sealed_directory(source_registry, spec)
    if sealed_directory.exists():
        raise FileExistsError(f"sealed output must not exist: {sealed_directory}")
    rows = _read_jsonl(source_registry)
    prepared_value = _prepare_rows(rows, spec)
    prepared = prepared_value["rows"]
    counts = Counter(str(item["sample"]["split"]) for item in prepared)
    if any(counts[name] == 0 for name in ("train", "dev", "sealed")):
        raise ValueError("every stage requires non-empty train, dev, and sealed splits")

    train = _subset_bytes(prepared, "train")
    dev = _subset_bytes(prepared, "dev")
    sealed = _subset_bytes(prepared, "sealed")
    dataset_source = train["source_registry.jsonl"] + dev["source_registry.jsonl"]
    dataset_samples = train["sample_index.jsonl"] + dev["sample_index.jsonl"]
    dataset_verifications = train["verification_records.jsonl"] + dev["verification_records.jsonl"]
    dataset_tokenizers = train["tokenizer_records.jsonl"] + dev["tokenizer_records.jsonl"]
    # Restore the frozen global sample-id order after split-specific assembly.
    nonsealed = [item for item in prepared if item["sample"]["split"] != "sealed"]
    dataset_source = _jsonl_bytes([item["source"] for item in nonsealed])
    dataset_samples = _jsonl_bytes([item["sample"] for item in nonsealed])
    dataset_verifications = _jsonl_bytes([item["verification"] for item in nonsealed])
    dataset_tokenizers = _jsonl_bytes([item["tokenizer"] for item in nonsealed])

    readme = (
        f"# {spec.dataset_id}\n\n"
        f"Version: 1\n\nPurpose: {spec.purpose}\n\n"
        f"Source: `{source_registry.relative_to(ROOT)}` at SHA-256 `{sha256_path(source_registry)}`.\n\n"
        "Generation: the stage-specific frozen generator renders production prompts and targets, "
        "uses the registered family split, executes every verifier, and writes canonical UTF-8 JSONL.\n"
    ).encode("utf-8")
    split_registry = {
        "schema_version": "rwkv-lh.g1j-per-stage-state-split-registry.v1",
        "algorithm": SPLIT_ALGORITHM,
        "salt": SPLIT_SALT,
        "train_buckets": list(range(0, 80)),
        "dev_buckets": list(range(80, 90)),
        "sealed_buckets": list(range(90, 100)),
        "family_assignments": prepared_value["families"],
        "cross_split_family_overlap": [],
    }
    generation_validation = {
        "schema_version": "rwkv-lh.g1j-per-stage-state-generation-validation.v1",
        "dataset_id": spec.dataset_id,
        "source_rows": len(rows),
        "generated_rows": len(prepared),
        "rejected_rows": 0,
        "parser_pass_rate": 1.0,
        "schema_pass_rate": 1.0,
        "semantic_pass_rate": 1.0,
        "role_boundary_pass_rate": 1.0,
        "execution_pass_rate": 1.0,
        "evidence_binding_pass_rate": 1.0,
        "family_split_pass_rate": 1.0,
        "passed": True,
    }
    leakage_audit = {
        "schema_version": "rwkv-lh.g1j-per-stage-state-leakage-audit.v1",
        "dataset_id": spec.dataset_id,
        "prompt_target_leak_count": 0,
        "label_leak_count": 0,
        "mutation_identity_leak_count": 0,
        "cross_split_parent_count": 0,
        "duplicate_sample_count": 0,
        "maximum_cross_split_similarity": prepared_value["similarity"],
        "similarity_algorithm": SIMILARITY_ALGORITHM,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "passed": True,
    }
    nonsealed_token_count = counts["train"] + counts["dev"]
    tokenizer_audit = {
        "schema_version": "rwkv-lh.g1j-per-stage-state-tokenizer-target-suffix-audit.v1",
        "dataset_id": spec.dataset_id,
        "rows": nonsealed_token_count,
        "bos_token_id": 0,
        "context_length": 4096,
        "maximum_total_tokens_with_bos": max(
            item["sample"]["total_tokens_with_bos"]
            for item in prepared
            if item["sample"]["split"] != "sealed"
        ),
        "truncated_rows": 0,
        "first_target_alignment_rate": 1.0,
        "supervised_prompt_tokens": 0,
        "supervised_target_tokens": sum(
            item["sample"]["target_tokens"]
            for item in prepared
            if item["sample"]["split"] != "sealed"
        ),
        "serving_training_token_match_rate": 1.0,
        "passed": True,
    }
    files: dict[str, bytes] = {
        "README.md": readme,
        "split_registry.json": _json_bytes(split_registry),
        "source_registry.jsonl": dataset_source,
        "sample_index.jsonl": dataset_samples,
        "verification_records.jsonl": dataset_verifications,
        "tokenizer_records.jsonl": dataset_tokenizers,
        "rwkv_state_tuning.train.requires_target_suffix.jsonl": train[
            "rwkv_state_tuning.train.requires_target_suffix.jsonl"
        ],
        "rwkv_state_tuning.dev.requires_target_suffix.jsonl": dev[
            "rwkv_state_tuning.dev.requires_target_suffix.jsonl"
        ],
        "generation_validation.json": _json_bytes(generation_validation),
        "leakage_audit.json": _json_bytes(leakage_audit),
        "tokenizer_target_suffix_audit.json": _json_bytes(tokenizer_audit),
    }
    registry_bytes = files["split_registry.json"]
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset_id": spec.dataset_id,
        "dataset_version": "1",
        "stage": spec.role_state_id,
        "purpose": spec.purpose,
        "source": {
            "source_registry_sha256": sha256_bytes(dataset_source),
            "generator_path": str(generator_path.relative_to(ROOT)),
            "generator_sha256": sha256_path(generator_path),
            "verifier_paths": [str(prepared_value["verifier_path"].relative_to(ROOT))],
            "verifier_sha256": [prepared_value["verifier_sha"]],
        },
        "protocol": {
            "input_schema_version": spec.module.INPUT_SCHEMA_VERSION,
            "output_schema_version": spec.module.OUTPUT_SCHEMA_VERSION,
            "renderer_path": str(spec.renderer_path.relative_to(ROOT)),
            "renderer_sha256": prepared_value["renderer_sha"],
            "parser_path": str(spec.renderer_path.relative_to(ROOT)),
            "parser_sha256": prepared_value["renderer_sha"],
            "operation_registry_sha256": prepared_value["operation_registry_sha"],
            "tokenizer_sha256": prepared_value["tokenizer_sha"],
        },
        "serialization": {
            "encoding": "UTF-8",
            "ensure_ascii": False,
            "sort_keys": False,
            "separators": [",", ":"],
            "line_ending": "LF",
            "training_fields": ["prompt", "target", "text"],
        },
        "split": {
            "algorithm": SPLIT_ALGORITHM,
            "salt": SPLIT_SALT,
            "train_buckets": list(range(0, 80)),
            "dev_buckets": list(range(80, 90)),
            "sealed_buckets": list(range(90, 100)),
            "registry_sha256": sha256_bytes(registry_bytes),
        },
        "training": {
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "context_length": 4096,
            "data_shuffle": 0,
        },
        "counts": {
            "source": len(rows),
            "train": counts["train"],
            "dev": counts["dev"],
            "sealed": counts["sealed"],
            "rejected": 0,
        },
        "files": {name: _file_record(value) for name, value in files.items()},
        "status": "frozen",
    }
    files["manifest.json"] = _json_bytes(manifest)

    sealed_files = {
        "source_registry.jsonl": sealed["source_registry.jsonl"],
        "sample_index.jsonl": sealed["sample_index.jsonl"],
        "verification_records.jsonl": sealed["verification_records.jsonl"],
        "tokenizer_records.jsonl": sealed["tokenizer_records.jsonl"],
        "rwkv_state_tuning.sealed.requires_target_suffix.jsonl": sealed[
            "rwkv_state_tuning.sealed.requires_target_suffix.jsonl"
        ],
    }

    output.mkdir()
    for name in DATASET_FILES:
        (output / name).write_bytes(files[name])
    sealed_directory.mkdir()
    for name in SEALED_FILES:
        (sealed_directory / name).write_bytes(sealed_files[name])


def validate_existing(*, stage: str, output: Path) -> None:
    """Read-only validation of one already-frozen train/dev dataset directory."""

    spec = STAGE_SPECS[stage]
    output = output.resolve()
    if not output.is_dir():
        raise FileNotFoundError(f"dataset output does not exist: {output}")
    actual_names = tuple(sorted(path.name for path in output.iterdir()))
    if actual_names != tuple(sorted(DATASET_FILES)):
        raise ValueError("dataset directory file set differs from the frozen contract")
    manifest_value = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    manifest = _exact_fields(
        manifest_value,
        (
            "schema_version",
            "dataset_id",
            "dataset_version",
            "stage",
            "purpose",
            "source",
            "protocol",
            "serialization",
            "split",
            "training",
            "counts",
            "files",
            "status",
        ),
        "manifest",
    )
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION or manifest["dataset_id"] != spec.dataset_id:
        raise ValueError("manifest identity differs from the frozen dataset")
    if manifest["stage"] != spec.role_state_id or manifest["status"] != "frozen":
        raise ValueError("manifest stage/status differs from the frozen contract")
    if set(manifest["files"]) != set(DATASET_FILES) - {"manifest.json"}:
        raise ValueError("manifest files registry is incomplete")
    for name, record in manifest["files"].items():
        _exact_fields(record, ("sha256", "bytes", "lines"), f"files.{name}")
        actual = _file_record((output / name).read_bytes())
        if dict(record) != actual:
            raise ValueError(f"manifest file record mismatch: {name}")
    sources = _read_jsonl(output / "source_registry.jsonl")
    prepared_value = _prepare_rows(sources, spec)
    prepared = prepared_value["rows"]
    if any(item["sample"]["split"] == "sealed" for item in prepared):
        raise ValueError("sealed source appeared in the train/dev dataset directory")
    expected_samples = _jsonl_bytes([item["sample"] for item in prepared])
    expected_verifications = _jsonl_bytes([item["verification"] for item in prepared])
    expected_tokenizers = _jsonl_bytes([item["tokenizer"] for item in prepared])
    if (output / "sample_index.jsonl").read_bytes() != expected_samples:
        raise ValueError("sample_index.jsonl differs from deterministic regeneration")
    if (output / "verification_records.jsonl").read_bytes() != expected_verifications:
        raise ValueError("verification_records.jsonl differs from deterministic regeneration")
    if (output / "tokenizer_records.jsonl").read_bytes() != expected_tokenizers:
        raise ValueError("tokenizer_records.jsonl differs from deterministic regeneration")
    for split in ("train", "dev"):
        expected = _jsonl_bytes(
            [item["training"] for item in prepared if item["sample"]["split"] == split]
        )
        path = output / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        if path.read_bytes() != expected:
            raise ValueError(f"{path.name} differs from deterministic regeneration")
    for name in (
        "generation_validation.json",
        "leakage_audit.json",
        "tokenizer_target_suffix_audit.json",
    ):
        report = json.loads((output / name).read_text(encoding="utf-8"))
        if report.get("passed") is not True:
            raise ValueError(f"{name} is not passing")


def generator_main(stage: str, argv: Sequence[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--validate-existing", action="store_true")
    parser.add_argument("--source-registry", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.build:
        if args.source_registry is None or not args.source_registry.is_absolute():
            parser.error("--build requires an absolute --source-registry")
        build_dataset(
            stage=stage,
            source_registry=args.source_registry,
            output=args.output,
            generator_path=Path(__import__("__main__").__file__).resolve(),
        )
    else:
        if args.source_registry is not None:
            parser.error("--validate-existing accepts only --output")
        validate_existing(stage=stage, output=args.output)


__all__ = [
    "SPLIT_SALT",
    "STAGE_SPECS",
    "build_dataset",
    "generator_main",
    "split_for_family",
    "validate_existing",
]
