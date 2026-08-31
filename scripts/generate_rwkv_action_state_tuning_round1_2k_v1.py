"""Build the first failure-grounded 2K RWKV-LH action state-tuning corpus.

The corpus supervises only next-state decisions observed at real progressive G1i
generation boundaries.  Historical reports define the failure signatures; a
deterministic private oracle defines actions and parameters; the current Controller
and ActionHarness render and verify every exported prompt.  No benchmark request or
reference answer is used as training content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from rwkv_lh.model_io import canonical_json, parse_model_command, parse_tool_selection

from scripts import generate_rwkv_action_state_tuning_v1 as pilot


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_ACTION_STATE_TUNING_ROUND1_2K_V1_20260826"
REGISTRY_PATH = EXPERIMENT / "failure_registry.jsonl"
EXCLUDED_PATH = EXPERIMENT / "excluded_engineering_failures.jsonl"
VERSION = "rwkv-lh.action-state-tuning.round1-2k.v1"
SCHEMA = "rwkv-lh.failure-grounded-action-state-candidate.v1"
STAGE_SCHEMA = "rwkv-lh.failure-grounded-action-stage-sft.v1"
TRAIN_COUNTS = {
    "protocol_correction": 400,
    "no_progress_recovery": 450,
    "observation_binding": 400,
    "coverage_focus": 350,
    "completion_evidence": 300,
    "privacy_gate": 100,
}
DEV_COUNTS = {
    "protocol_correction": 40,
    "no_progress_recovery": 45,
    "observation_binding": 40,
    "coverage_focus": 35,
    "completion_evidence": 30,
    "privacy_gate": 10,
}
CLUSTER_CODE = {
    "protocol_correction": "PC",
    "no_progress_recovery": "NP",
    "observation_binding": "OB",
    "coverage_focus": "CF",
    "completion_evidence": "CE",
    "privacy_gate": "PG",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _strip_pilot_padding(request: str) -> str:
    for marker in (" 这是海岸", " 这是流动", " 这是高原", " 这是夜间", " 这是社区", " 这是沙漠", " This is a coastal", " This is a traveling", " This is a highland", " This is a night", " This is a community", " This is a desert"):
        if marker in request:
            return request.split(marker, 1)[0].strip()
    return request.strip()


def _group(split: str, ordinal: int, divisor: int = 5) -> int:
    """Return a split-disjoint fixture group without adding irrelevant padding."""

    return ordinal // divisor + (0 if split == "train" else 10000)


def _registry() -> dict[str, dict[str, Any]]:
    rows = _read_jsonl(REGISTRY_PATH)
    registry = {str(row["failure_signature_id"]): row for row in rows}
    if len(registry) != 13 or not all(row.get("training_eligible") is True for row in rows):
        raise RuntimeError("failure registry is incomplete or contains ineligible labels")
    for row in rows:
        source = ROOT / str(row["source"]["path"])
        if not source.is_file() or _sha256(source) != row["source"]["sha256"]:
            raise RuntimeError(f"failure source changed: {source}")
    return registry


def _oracle_digest(candidate: Mapping[str, Any]) -> str:
    return pilot._digest_value(
        {
            "schema_version": pilot.ORACLE_SCHEMA,
            "trajectory_id": candidate["trajectory_id"],
            "source_seed_id": candidate["source_seed_id"],
            "turns": candidate["turns"],
            "prelude": candidate["prelude"],
            "expected_backend_executions": candidate["expected_backend_executions"],
        }
    )


def _finish_candidate(
    candidate: dict[str, Any],
    *,
    split: str,
    cluster: str,
    ordinal: int,
    signature_id: str,
    target_turn: int,
    target_reason: str,
    state_cells: Mapping[str, Any],
) -> dict[str, Any]:
    code = CLUSTER_CODE[cluster]
    family = ordinal // 5
    variant = ordinal % 5
    candidate.update(
        {
            "schema_version": SCHEMA,
            "trajectory_id": f"AST-R1-{code}-{split.upper()}-{ordinal + 1:04d}",
            "semantic_family_id": f"AST-R1-SF-{code}-{split.upper()}-{family + 1:04d}",
            "split": split,
            "failure_cluster": cluster,
            "failure_signature_id": signature_id,
            "state_cells": dict(state_cells),
            "target_turn": target_turn,
            "target_reason": target_reason,
            "surface_variant": variant,
        }
    )
    candidate["private_oracle_digest"] = _oracle_digest(candidate)
    return candidate


def _protocol_candidate(split: str, ordinal: int) -> dict[str, Any]:
    language = "zh" if ordinal % 2 == 0 else "en"
    slot = ordinal + (0 if split == "train" else 10000)
    operation_index = ordinal % 7
    base = pilot._base_candidate("ST-ACT-016", ordinal // 5, ordinal % 5)
    files: list[dict[str, str]] = []
    if operation_index == 0:
        path = f"protocol/{split}/note-{slot:05d}.txt"
        files = [pilot._workspace_file(path, f"protocol note {slot}\n")]
        operation, params = "read_file", {"path": path}
    elif operation_index == 1:
        path = f"protocol/{split}/record-{slot:05d}.json"
        files = [pilot._workspace_file(path, json.dumps({"slot": slot}) + "\n")]
        operation, params = "read_json", {"path": path}
    elif operation_index == 2:
        parent = f"protocol/{split}/folder-{slot:05d}"
        files = [pilot._workspace_file(f"{parent}/member.txt", f"member {slot}\n")]
        operation, params = "list_directory", {"path": parent, "recursive": False}
    elif operation_index == 3:
        path = f"protocol/{split}/check-{slot:05d}.txt"
        files = [pilot._workspace_file(path, f"ok {slot}\n")]
        operation, params = "check_command", {
            "argv": ["python", "-c", f"from pathlib import Path; assert Path('{path}').exists()"],
            "cwd": ".",
            "expected_exit_code": 0,
        }
    elif operation_index == 4:
        operation, params = "calculator", {"expression": f"({slot % 97 + 3}*7)+2"}
    elif operation_index == 5:
        operation, params = "date_diff", {"date_a": "2026-01-03", "date_b": f"2026-02-{slot % 20 + 1:02d}"}
    else:
        operation, params = "current_time", {"timezone": ("UTC", "Asia/Shanghai", "Europe/Oslo")[slot % 3]}

    error_kind = ("missing_required", "extra_field", "wrong_type")[ordinal % 3]
    # list_directory.path and current_time.timezone have safe normalizer defaults;
    # omitting them is therefore not a protocol rejection.  Use an actually invalid
    # extra-field boundary so the replay contains the historical rejected state.
    if error_kind == "missing_required" and operation in {"list_directory", "current_time"}:
        error_kind = "extra_field"
    if error_kind == "missing_required":
        malformed: dict[str, Any] = {}
    elif error_kind == "extra_field":
        malformed = {**params, "invented_parameter": True}
    else:
        first_key = next(iter(params))
        malformed = {**params, first_key: 17 if not isinstance(params[first_key], int) else "wrong"}
    request = (
        f"执行编号 {slot} 的 `{operation}` 局部步骤，目标参数是 {canonical_json(params)}。若刚才的 direct 参数被协议拒绝，只依据已经披露的合同纠正参数，不要重新选择工具。"
        if language == "zh"
        else f"Perform local `{operation}` step {slot} with target arguments {canonical_json(params)}. If the direct arguments are rejected, correct them under the already disclosed contract without selecting a tool again."
    )
    base.update(
        {
            "language": language,
            "network_policy": "offline",
            "request": request,
            "workspace_files": files,
            "prelude": [{
                "kind": "malformed_direct_call",
                "operation": operation,
                "params": malformed,
                "failure_class": error_kind,
            }],
            "turns": [pilot._turn(operation, params, "after_protocol_rejection")],
            "expected_backend_executions": 0,
        }
    )
    return _finish_candidate(
        base,
        split=split,
        cluster="protocol_correction",
        ordinal=ordinal,
        signature_id="FST-R1-001",
        target_turn=0,
        target_reason="correct the rejected direct arguments under the retained disclosed contract",
        state_cells={"operation": operation, "error_kind": error_kind, "selector_must_repeat": False},
    )


def _repeat_failure_candidate(split: str, ordinal: int) -> dict[str, Any]:
    language = "zh" if ordinal % 2 == 0 else "en"
    slot = ordinal + (0 if split == "train" else 10000)
    path = f"recovery/{split}/worker-{slot:05d}.py"
    content = f"VALUE = {slot % 13}\n"
    base = pilot._base_candidate("ST-ACT-020", ordinal // 5, ordinal % 5)
    argv = ["python", "-c", f"raise AssertionError('stable verifier signature {slot % 9}')"]
    base.update(
        {
            "language": language,
            "network_policy": "offline",
            "request": (
                f"验证失败签名保持不变。不要再次运行同一失败命令；读取其引用的 `{path}` 以获得新的修复证据。"
                if language == "zh"
                else f"The verifier failure signature is unchanged. Do not run the same failed command again; inspect cited source `{path}` for new repair evidence."
            ),
            "workspace_files": [pilot._workspace_file(path, content)],
            "prelude": [{
                "kind": "failed_verifier_observation",
                "operation": "check_command",
                "params": {"argv": argv, "cwd": ".", "expected_exit_code": 0},
            }],
            "turns": [pilot._turn("read_file", {"path": path}, "after_repeated_failure")],
            "expected_backend_executions": 0,
        }
    )
    return _finish_candidate(
        base,
        split=split,
        cluster="no_progress_recovery",
        ordinal=ordinal,
        signature_id="FST-R1-003",
        target_turn=0,
        target_reason="change evidence-gathering strategy after an unchanged verifier failure",
        state_cells={"normalized_failure": f"stable-{slot % 9}", "repeat_class": ordinal % 4 + 2, "next_strategy": "inspect_source"},
    )


def _no_progress_candidate(split: str, ordinal: int) -> dict[str, Any]:
    mode = ordinal % 5
    if mode == 0:
        return _repeat_failure_candidate(split, ordinal)
    seed = "ST-ACT-017" if mode == 1 else "ST-ACT-015"
    candidate = pilot._instantiate(seed, _group(split, ordinal), ordinal % 5)
    candidate["request"] = _strip_pilot_padding(str(candidate["request"]))
    signature = "FST-R1-004" if seed == "ST-ACT-017" else "FST-R1-002"
    target_turn = 0 if seed == "ST-ACT-017" else 1
    cells = (
        {"provider_status": "provider_unavailable", "evidence_count": 0, "identical_retry_allowed": False}
        if seed == "ST-ACT-017"
        else {"observation_delta": 0, "member_visible": True, "identical_repeat_allowed": False}
    )
    return _finish_candidate(
        candidate,
        split=split,
        cluster="no_progress_recovery",
        ordinal=ordinal,
        signature_id=signature,
        target_turn=target_turn,
        target_reason="advance the unresolved frontier instead of repeating an unchanged action",
        state_cells=cells,
    )


def _text_to_calculator_candidate(split: str, ordinal: int) -> dict[str, Any]:
    language = "zh" if ordinal % 2 == 0 else "en"
    slot = ordinal + (0 if split == "train" else 10000)
    expression = f"({slot % 41 + 2}*{slot % 7 + 3})-{slot % 5}"
    path = f"observed/{split}/expression-{slot:05d}.txt"
    base = pilot._base_candidate("ST-ACT-020", ordinal // 5, ordinal % 5)
    base.update(
        {
            "language": language,
            "network_policy": "offline",
            "request": (
                f"先读取文本 `{path}`。它是完整算式；下一步把观察到的字面值交给 calculator，不要把文本改用 read_json。"
                if language == "zh"
                else f"Read text `{path}` first. It contains a complete expression; pass the observed literal to calculator next instead of treating the text as JSON."
            ),
            "workspace_files": [pilot._workspace_file(path, expression + "\n")],
            "prelude": [],
            "turns": [
                pilot._turn("read_file", {"path": path}, "initial"),
                pilot._turn("calculator", {"expression": expression}, "after_text_observation"),
            ],
            "expected_backend_executions": 0,
        }
    )
    return _finish_candidate(
        base,
        split=split,
        cluster="observation_binding",
        ordinal=ordinal,
        signature_id="FST-R1-007",
        target_turn=1,
        target_reason="consume a complete text observation with a type-compatible next tool",
        state_cells={"observed_media_type": "text", "complete": True, "next_parameter": "expression"},
    )


def _observation_candidate(split: str, ordinal: int) -> dict[str, Any]:
    mode = ordinal % 8
    if mode == 0:
        seed = "ST-ACT-001" if ordinal % 2 == 0 else "ST-ACT-002"
        candidate = pilot._instantiate(seed, _group(split, ordinal), ordinal % 5)
        signature, target_turn = "FST-R1-005", 0
        cells = {"path_is_explicit": True, "discovery_needed": False, "media": "text" if seed.endswith("001") else "json"}
    elif mode == 1:
        return _text_to_calculator_candidate(split, ordinal)
    else:
        seed = "ST-ACT-011" if ordinal % 2 == 0 else "ST-ACT-012"
        candidate = pilot._instantiate(seed, _group(split, ordinal), ordinal % 5)
        signature, target_turn = "FST-R1-006", 1
        cells = {"latest_observation_complete": True, "binding_kind": "text_scalar" if seed.endswith("011") else "json_fields", "stale_value_allowed": False}
    candidate["request"] = _strip_pilot_padding(str(candidate["request"]))
    return _finish_candidate(
        candidate,
        split=split,
        cluster="observation_binding",
        ordinal=ordinal,
        signature_id=signature,
        target_turn=target_turn,
        target_reason="select the applicable tool and bind exact current observation values",
        state_cells=cells,
    )


def _coverage_candidate(split: str, ordinal: int) -> dict[str, Any]:
    language = "zh" if ordinal % 2 == 0 else "en"
    slot = ordinal + (0 if split == "train" else 10000)
    total = 3 + ordinal % 3
    already_read = 1 + (ordinal // 3) % (total - 1)
    parent = f"coverage/{split}/batch-{slot:05d}"
    paths = [f"{parent}/member-{index + 1:02d}.txt" for index in range(total)]
    base = pilot._base_candidate("ST-ACT-015", ordinal // 5, ordinal % 5)
    turns = [pilot._turn("list_directory", {"path": parent, "recursive": False}, "initial")]
    for index, path in enumerate(paths[: already_read + 1]):
        turns.append(
            pilot._turn(
                "read_file",
                {"path": path},
                "after_listing" if index == 0 else "partial_coverage",
                bindings=({"target_pointer": "/path", "source_event": "prior list_directory action_result", "source_pointer": "/payload/result/output/entries/path"},),
            )
        )
    target_turn = len(turns) - 1
    base.update(
        {
            "language": language,
            "network_policy": "offline",
            "request": (
                f"非递归观察 `{parent}` 后逐个读取已发现成员且不得重读。当前按覆盖顺序继续到下一个未读成员；全部覆盖后才进入汇总。"
                if language == "zh"
                else f"After listing `{parent}` non-recursively, read discovered members once each. Continue to the next unread member in coverage order; aggregate only after full coverage."
            ),
            "workspace_files": [pilot._workspace_file(path, f"coverage value {slot}-{index + 1}\n") for index, path in enumerate(paths)],
            "prelude": [],
            "turns": turns,
            "expected_backend_executions": 0,
        }
    )
    signature = "FST-R1-008" if already_read < total - 1 else "FST-R1-009"
    return _finish_candidate(
        base,
        split=split,
        cluster="coverage_focus",
        ordinal=ordinal,
        signature_id=signature,
        target_turn=target_turn,
        target_reason="continue from the cumulative member ledger without restarting discovery",
        state_cells={"total_members": total, "already_read_before_target": already_read, "coverage_complete_after_target": already_read + 1 == total},
    )


def _completion_candidate(split: str, ordinal: int) -> dict[str, Any]:
    mode = ordinal % 4
    seed = "ST-ACT-018" if mode < 3 else "ST-ACT-020"
    candidate = pilot._instantiate(seed, _group(split, ordinal, 4), ordinal % 4)
    candidate["request"] = _strip_pilot_padding(str(candidate["request"]))
    if seed == "ST-ACT-020":
        signature, target_turn = "FST-R1-012", 1
        cells = {"latest_complete_view": True, "remaining_obligations": 0, "redundant_verification_allowed": False}
    elif mode == 0:
        signature, target_turn = "FST-R1-010", 1
        cells = {"mutation_seen": False, "remaining_obligations": 2, "final_allowed": False}
    elif mode == 1:
        signature, target_turn = "FST-R1-011", 2
        cells = {"mutation_seen": True, "fresh_read_seen": False, "final_allowed": False}
    else:
        signature, target_turn = "FST-R1-012", 3
        cells = {"mutation_seen": True, "fresh_read_seen": True, "remaining_obligations": 0, "final_allowed": True}
    return _finish_candidate(
        candidate,
        split=split,
        cluster="completion_evidence",
        ordinal=ordinal,
        signature_id=signature,
        target_turn=target_turn,
        target_reason="respect remaining obligations and finish only from a fresh complete evidence view",
        state_cells=cells,
    )


def _privacy_candidate(split: str, ordinal: int) -> dict[str, Any]:
    seed = "ST-ACT-013" if ordinal % 2 == 0 else "ST-ACT-014"
    candidate = pilot._instantiate(seed, _group(split, ordinal), ordinal % 5)
    candidate["request"] = _strip_pilot_padding(str(candidate["request"]))
    target_turn = 1 if ordinal % 4 < 2 else 2
    cells = {
        "provenance": "secret" if seed.endswith("013") else "tool_untrusted",
        "gate_reached": target_turn == 2,
        "backend_execution": 0,
        "rewrite_allowed": False,
    }
    return _finish_candidate(
        candidate,
        split=split,
        cluster="privacy_gate",
        ordinal=ordinal,
        signature_id="FST-R1-013",
        target_turn=target_turn,
        target_reason="reach the policy Gate with literal arguments once, then honor typed rejection",
        state_cells=cells,
    )


BUILDERS = {
    "protocol_correction": _protocol_candidate,
    "no_progress_recovery": _no_progress_candidate,
    "observation_binding": _observation_candidate,
    "coverage_focus": _coverage_candidate,
    "completion_evidence": _completion_candidate,
    "privacy_gate": _privacy_candidate,
}


def _selected_stages(
    positive: Sequence[Mapping[str, Any]], candidate: Mapping[str, Any], remaining: int
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in positive if int(row["turn_index"]) == int(candidate["target_turn"])]
    order = {"selector": 0, "direct": 1}
    rows.sort(key=lambda row: order[str(row["stage"])])
    if candidate["failure_cluster"] == "protocol_correction":
        rows = [row for row in rows if row["stage"] == "direct"]
    if remaining == 1 and len(rows) > 1:
        rows = [next(row for row in rows if row["stage"] == "direct")]
    if not rows or len(rows) > remaining:
        raise AssertionError(f"cannot select stages for {candidate['trajectory_id']}")
    enriched: list[dict[str, Any]] = []
    for row in rows:
        raw = str(row["target"])
        if row["stage"] == "selector":
            assert parse_tool_selection(raw) == row["target_operation"]
        else:
            assert parse_model_command(raw).name == row["target_operation"]
        row.update(
            {
                "schema_version": STAGE_SCHEMA,
                "failure_cluster": candidate["failure_cluster"],
                "failure_signature_id": candidate["failure_signature_id"],
                "state_cells": candidate["state_cells"],
                "target_reason": candidate["target_reason"],
                "training_intent": "next_state_transition_not_generic_task_sft",
            }
        )
        enriched.append(row)
    return enriched


def _hard_negative(stage: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    signature = registry[str(stage["failure_signature_id"])]
    return {
        "schema_version": "rwkv-lh.failure-grounded-preference-seed.v1",
        "trajectory_id": stage["trajectory_id"],
        "stage": stage["stage"],
        "prompt_sha256": stage["prompt_sha256"],
        "chosen": stage["target"],
        "rejected_transition_classes": signature["hard_negatives"],
        "failure_signature_id": stage["failure_signature_id"],
        "positive_use": False,
        "note": "Transition-class negative only; render a concrete rejected target under the current contract before preference training.",
    }


def _holdout_contamination(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    paths = pilot._holdout_files()
    holdouts = pilot._holdout_requests(paths)
    holdout_counts = [(row, pilot._byte_ngram_counts(row["text"])) for row in holdouts]
    maximum = 0.0
    nearest: dict[str, Any] | None = None
    exact = 0
    requests = [str(candidate["request"]) for candidate in candidates]
    for candidate, request in zip(candidates, requests):
        counts = pilot._byte_ngram_counts(request)
        for holdout, other in holdout_counts:
            if request == holdout["text"]:
                exact += 1
            score = pilot._counter_cosine(counts, other)
            if score > maximum:
                maximum = score
                nearest = {"trajectory_id": candidate["trajectory_id"], "holdout_id": holdout["id"], "score": score}
    if exact or maximum >= 0.75:
        raise AssertionError({"exact_holdout_overlap": exact, "maximum_holdout_similarity": maximum})
    return {
        "similarity_version": pilot.SIMILARITY_VERSION,
        "n": 5,
        "threshold_exclusive": 0.75,
        "holdout_request_count": len(holdouts),
        "exact_holdout_overlap_count": exact,
        "maximum_holdout_similarity": maximum,
        "nearest_holdout": nearest,
        "holdout_files": {str(path.relative_to(ROOT)): {"sha256": _sha256(path)} for path in paths},
    }


def _public_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in candidate.items()
        if key not in {"prelude", "private_oracle_digest"}
    } | {"private_oracle_digest": candidate["private_oracle_digest"]}


def _private_oracle(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return pilot._private_oracle(candidate)


def _readme(manifest: Mapping[str, Any]) -> str:
    return f"""# RWKV-LH Action State Tuning Round1 2K v1

这是首轮失败驱动 state-tuning 数据，不是通用任务 SFT，也不是旧 pilot 的扩量副本。

- train：{manifest['counts']['train_stage_sft']} 条；dev：{manifest['counts']['dev_stage_sft']} 条。
- verified trajectory：{manifest['counts']['trajectories']}。
- 每条训练行都指向 `failure_registry.jsonl` 中的历史错误状态迁移。
- prompt 来自当前 progressive Controller/ModelSession 真实回放；target 由本地 oracle 和
  ActionHarness 验证。
- rollover 使用 `action-result-decision-state.v1` 单一历史投影；action result 不再同时以
  exact record 与 retained event 重复注入。
- 网络证据为冻结 `.invalid`；隐私 Gate 样本 backend execution 为 0。

## 训练入口

使用 `rwkv_state_tuning.train.requires_target_suffix.jsonl`，并固定：

```text
--data_type jsonl --loss_mask target_suffix --peft state --op fla
```

`dev`、private oracle、preference seed 和冻结 holdout 不得进入训练。远程 tokenizer/ctx 检查
通过前，manifest 的 `remote_tokenizer_validated` 保持 false，不得启动训练。
"""


def generate() -> dict[str, Any]:
    registry = _registry()
    staging = OUTPUT.with_name(OUTPUT.name + ".staging")
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset: {OUTPUT}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        candidates: list[dict[str, Any]] = []
        stages: list[dict[str, Any]] = []
        validations: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for split, quotas in (("train", TRAIN_COUNTS), ("dev", DEV_COUNTS)):
            for cluster, quota in quotas.items():
                ordinal = 0
                selected = 0
                while selected < quota:
                    candidate = BUILDERS[cluster](split, ordinal)
                    positive, validation, negative_rows = pilot._replay(candidate)
                    picked = _selected_stages(positive, candidate, quota - selected)
                    candidates.append(candidate)
                    stages.extend(picked)
                    validation.update(
                        {
                            "failure_cluster": cluster,
                            "failure_signature_id": candidate["failure_signature_id"],
                            "selected_stage_count": len(picked),
                        }
                    )
                    validations.append(validation)
                    rejected.extend(negative_rows)
                    selected += len(picked)
                    ordinal += 1
                    if ordinal % 50 == 0:
                        print(f"{split} {cluster}: {selected}/{quota} stages", flush=True)

        train_stages = [row for row in stages if row["split"] == "train"]
        dev_stages = [row for row in stages if row["split"] == "dev"]
        if len(train_stages) != 2000 or len(dev_stages) != 200:
            raise AssertionError((len(train_stages), len(dev_stages)))
        train_counts = Counter(str(row["failure_cluster"]) for row in train_stages)
        dev_counts = Counter(str(row["failure_cluster"]) for row in dev_stages)
        if dict(train_counts) != TRAIN_COUNTS or dict(dev_counts) != DEV_COUNTS:
            raise AssertionError({"train": train_counts, "dev": dev_counts})
        texts = [str(row["text"]) for row in stages]
        if len(set(texts)) != len(texts):
            raise AssertionError("exact stage text duplicate")
        train_families = {str(row["semantic_family_id"]) for row in train_stages}
        dev_families = {str(row["semantic_family_id"]) for row in dev_stages}
        if train_families & dev_families:
            raise AssertionError("semantic family crosses train/dev")
        if any(str(row["failure_signature_id"]) not in registry for row in stages):
            raise AssertionError("stage references unknown failure signature")

        contamination = _holdout_contamination(candidates)
        preference = [_hard_negative(row, registry) for row in stages]
        privacy_backend = sum(
            int(row["backend_execution_count"])
            for row in validations
            if row["failure_cluster"] == "privacy_gate"
        )
        if privacy_backend:
            raise AssertionError(f"privacy backend execution count={privacy_backend}")

        files = {
            "semantic_candidates.jsonl": [_public_candidate(row) for row in candidates],
            "private/oracle_trajectories.jsonl": [_private_oracle(row) for row in candidates],
            "validation.jsonl": validations,
            "rejected_attempts.jsonl": rejected,
            "preference_transition_seeds.jsonl": preference,
            "stage_sft.train.jsonl": train_stages,
            "stage_sft.dev.jsonl": dev_stages,
            "rwkv_state_tuning.train.requires_target_suffix.jsonl": [
                {
                    "prompt": row["prompt"],
                    "target": row["target"],
                    "text": row["text"],
                    "tier": 1,
                }
                for row in train_stages
            ],
            "rwkv_state_tuning.dev.requires_target_suffix.jsonl": [
                {
                    "prompt": row["prompt"],
                    "target": row["target"],
                    "text": row["text"],
                    "tier": 1,
                }
                for row in dev_stages
            ],
            "failure_registry.jsonl": list(registry.values()),
            "excluded_engineering_failures.jsonl": _read_jsonl(EXCLUDED_PATH),
        }
        for relative, rows in files.items():
            _write_jsonl(staging / relative, rows)

        counts = {
            "trajectories": len(candidates),
            "train_stage_sft": len(train_stages),
            "dev_stage_sft": len(dev_stages),
            "failure_signatures": len(registry),
            "train_semantic_families": len(train_families),
            "dev_semantic_families": len(dev_families),
            "protocol_rejected_attempts": len(rejected),
        }
        manifest: dict[str, Any] = {
            "schema_version": "rwkv-lh.dataset-manifest.v1",
            "dataset_version": VERSION,
            "artifact_kind": "failure_grounded_controller_verified_action_state_tuning",
            "training_ready": False,
            "local_validation_complete": True,
            "remote_tokenizer_validated": False,
            "purpose": "Round1: tune the recurrent state for the highest-frequency observed Harness transition failures, not generic task completion.",
            "generation": f"uv run python {ROOT / 'scripts/generate_rwkv_action_state_tuning_round1_2k_v1.py'}",
            "controller_replay": True,
            "strong_model_as_label_source": False,
            "live_network_used": False,
            "tool_disclosure_mode": "progressive",
            "training_file": "rwkv_state_tuning.train.requires_target_suffix.jsonl",
            "development_file": "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
            "loss_mask": "target_suffix",
            "counts": counts,
            "cluster_counts": {"train": TRAIN_COUNTS, "dev": DEV_COUNTS},
            "validation": {
                "accepted_trajectories": len(validations),
                "controller_replay_rate": 1.0,
                "positive_target_parse_rate": 1.0,
                "failure_signature_coverage_rate": 1.0,
                "privacy_backend_execution_count": privacy_backend,
                "exact_stage_text_duplicate_count": 0,
                "train_dev_family_overlap_count": 0,
                "contamination": contamination,
            },
            "remote": {
                "ssh_alias": "rwkv-8222",
                "project_dir": "/home/chase/chase/RWKV-PEFT",
                "upload_dir": "/home/chase/chase/RWKV-PEFT/data/rwkv_lh_action_state_tuning_round1_2k_v1",
                "gpu": 0,
                "ctx_len": 2496,
                "tokenizer_validation_required": True,
            },
            "source_files": {
                str(REGISTRY_PATH.relative_to(ROOT)): {"sha256": _sha256(REGISTRY_PATH)},
                str(EXCLUDED_PATH.relative_to(ROOT)): {"sha256": _sha256(EXCLUDED_PATH)},
                "scripts/generate_rwkv_action_state_tuning_v1.py": {"sha256": _sha256(ROOT / "scripts/generate_rwkv_action_state_tuning_v1.py")},
                "scripts/generate_rwkv_action_state_tuning_round1_2k_v1.py": {"sha256": _sha256(ROOT / "scripts/generate_rwkv_action_state_tuning_round1_2k_v1.py")},
                "rwkv_lh/model.py": {"sha256": _sha256(ROOT / "rwkv_lh/model.py")},
                "rwkv_lh/model_session.py": {"sha256": _sha256(ROOT / "rwkv_lh/model_session.py")},
                "rwkv_lh/model_io.py": {"sha256": _sha256(ROOT / "rwkv_lh/model_io.py")},
                "rwkv_lh/controller.py": {"sha256": _sha256(ROOT / "rwkv_lh/controller.py")},
                "rwkv_lh/harness.py": {"sha256": _sha256(ROOT / "rwkv_lh/harness.py")},
            },
        }
        (staging / "README.md").write_text(_readme(manifest), encoding="utf-8")
        artifact_paths = [staging / relative for relative in files] + [staging / "README.md"]
        manifest["files"] = {
            str(path.relative_to(staging)): {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in artifact_paths
        }
        _write_json(staging / "manifest.json", manifest)
        staging.rename(OUTPUT)
        return manifest
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def validate_existing() -> dict[str, Any]:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    if manifest["dataset_version"] != VERSION:
        raise AssertionError("unexpected dataset version")
    for relative, metadata in manifest["files"].items():
        path = OUTPUT / relative
        if not path.is_file() or _sha256(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
            raise AssertionError(f"artifact changed: {relative}")
    train = _read_jsonl(OUTPUT / "stage_sft.train.jsonl")
    dev = _read_jsonl(OUTPUT / "stage_sft.dev.jsonl")
    if len(train) != 2000 or len(dev) != 200:
        raise AssertionError("stage count changed")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-existing", action="store_true")
    args = parser.parse_args()
    manifest = validate_existing() if args.validate_existing else generate()
    print(json.dumps({
        "dataset_version": manifest["dataset_version"],
        "training_ready": manifest["training_ready"],
        "counts": manifest["counts"],
        "cluster_counts": manifest["cluster_counts"],
        "validation": manifest["validation"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
