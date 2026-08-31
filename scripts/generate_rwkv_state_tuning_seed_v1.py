"""Generate non-holdout synthesis seeds for RWKV-LH action state tuning."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.harness import ActionHarness
from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION, canonical_json
from rwkv_lh.retrieval import (
    FrozenRetrievalBackend,
    NetworkPolicy,
    NetworkPolicyMode,
    build_retrieval_actions,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "datasets" / "rwkv_lh_state_tuning_seed_v1"
VERSION = "rwkv-lh.action-state-tuning-seed.v1"
SCHEMA = "rwkv-lh.action-state-tuning-seed-template.v1"
SIMILARITY_VERSION = "utf8-byte-ngram-cosine.v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _byte_ngram_cosine(left: str, right: str, n: int = 5) -> float:
    left_bytes = left.encode("utf-8")
    right_bytes = right.encode("utf-8")
    if left_bytes == right_bytes:
        return 1.0
    if len(left_bytes) < n or len(right_bytes) < n:
        return 0.0
    left_counts = Counter(left_bytes[index : index + n] for index in range(len(left_bytes) - n + 1))
    right_counts = Counter(
        right_bytes[index : index + n] for index in range(len(right_bytes) - n + 1)
    )
    dot = sum(count * right_counts.get(key, 0) for key, count in left_counts.items())
    if not dot:
        return 0.0
    left_norm = math.sqrt(sum(count * count for count in left_counts.values()))
    right_norm = math.sqrt(sum(count * count for count in right_counts.values()))
    return dot / (left_norm * right_norm)


def _turn(
    state: str,
    operation: str,
    params: Mapping[str, Any],
    *,
    forbidden: Sequence[str] = (),
    bindings: Sequence[str] = (),
) -> dict[str, Any]:
    arguments = dict(params)
    return {
        "state": state,
        "target_operation": operation,
        "selector_target": canonical_json(
            {"function": "select_tool", "params": {"name": operation}}
        ),
        "direct_call_target_blueprint": canonical_json(
            {"function": operation, "params": arguments}
        ),
        "target_params_blueprint": arguments,
        "literal_binding_rules": list(bindings),
        "forbidden_positive_operations": list(forbidden),
    }


def _seed(
    identifier: str,
    family: str,
    blueprint: str,
    turns: Sequence[Mapping[str, Any]],
    *,
    policy: str,
    workspace: Sequence[Mapping[str, Any]] = (),
    events: Sequence[Mapping[str, Any]] = (),
    axes: Mapping[str, Sequence[Any]] | None = None,
    invariants: Sequence[str] = (),
    minimum_expansions: int = 64,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "seed_id": identifier,
        "lane": "rwkv_action",
        "family": family,
        "languages": ["zh", "en"],
        "network_policy": policy,
        "request_blueprint": blueprint,
        "workspace_blueprint": [dict(item) for item in workspace],
        "controller_event_blueprints": [dict(item) for item in events],
        "target_turns": [dict(item) for item in turns],
        "synthesis_axes": {key: list(value) for key, value in (axes or {}).items()},
        "invariants": list(invariants),
        "minimum_expansions": int(minimum_expansions),
        "positive_source": "synthesized_then_controller_verified",
        "negative_use": "filter_or_preference_only_never_positive",
    }


def seed_templates() -> list[dict[str, Any]]:
    common_axes = {
        "language": ["zh", "en"],
        "path_depth": [1, 2, 4],
        "request_style": ["imperative", "question", "constraint_first"],
    }
    seeds = [
        _seed(
            "ST-ACT-001",
            "exact_text_path_priority",
            "Name one exact existing non-JSON text path and request facts from that file.",
            [_turn("initial", "read_file", {"path": "${EXACT_TEXT_PATH}"}, forbidden=("list_directory",))],
            policy="offline",
            workspace=({"path": "${EXACT_TEXT_PATH}", "content": "${TEXT_PAYLOAD}"},),
            axes=common_axes,
            invariants=("Preserve the request path byte-for-byte.", "Do not discover a path that is already explicit."),
        ),
        _seed(
            "ST-ACT-002",
            "exact_json_path_priority",
            "Name one exact existing JSON path and request one or more fields from its parsed value.",
            [_turn("initial", "read_json", {"path": "${EXACT_JSON_PATH}"}, forbidden=("list_directory", "read_file"))],
            policy="offline",
            workspace=({"path": "${EXACT_JSON_PATH}", "json_value": "${JSON_VALUE}"},),
            axes=common_axes,
            invariants=("Use read_json for structured JSON inspection.", "Do not replace an explicit path with directory discovery."),
        ),
        _seed(
            "ST-ACT-003",
            "unknown_path_discovery",
            "Request inspection of an unknown member selected by a property; no exact member path is given.",
            [_turn("initial", "list_directory", {"path": "${KNOWN_PARENT}", "recursive": False}, forbidden=("read_file", "read_json"))],
            policy="offline",
            workspace=({"path": "${KNOWN_PARENT}/${CANDIDATE_A}", "content": "${A}"}, {"path": "${KNOWN_PARENT}/${CANDIDATE_B}", "content": "${B}"}),
            axes=common_axes,
            invariants=("Discovery is correct only because the member path is unknown.",),
        ),
        _seed(
            "ST-ACT-004",
            "public_web_general",
            "Request current public page information without an exact structured registry identifier.",
            [_turn("initial", "web_search", {"query": "${PUBLIC_QUERY}", "max_results": 5}, forbidden=("connector_lookup", "list_directory"))],
            policy="auto_public",
            axes={"language": ["zh", "en"], "source_kind": ["status_page", "vendor_docs", "public_event"], "freshness": ["current", "latest"]},
            invariants=("The query contains only public model-authored text.", "Do not substitute a connector operation without an exact structured source."),
        ),
        _seed(
            "ST-ACT-005",
            "structured_repository_lookup",
            "Request structured metadata for an exact public repository identifier.",
            [_turn("initial", "connector_lookup", {"operation": "github_repository", "query": "${OWNER}/${REPOSITORY}"}, forbidden=("web_search",))],
            policy="auto_public",
            axes={"language": ["zh", "en"], "metadata": ["default_branch", "license", "issues_metadata"]},
            invariants=("Preserve owner/repository exactly.", "Use the matching connector enum."),
        ),
        _seed(
            "ST-ACT-006",
            "structured_package_lookup",
            "Request structured release metadata for an exact public package and ecosystem.",
            [_turn("initial", "connector_lookup", {"operation": "package_release", "query": "${ECOSYSTEM}:${PACKAGE}"}, forbidden=("web_search",))],
            policy="auto_public",
            axes={"language": ["zh", "en"], "ecosystem": ["pypi", "npm", "crates"], "metadata": ["latest_version", "release_date", "dist_tag"]},
            invariants=("Package identity is public and exact.", "Do not downgrade structured lookup to general web search."),
        ),
        _seed(
            "ST-ACT-007",
            "structured_weather_lookup",
            "Request structured weather observations or alerts for a named public region.",
            [_turn("initial", "connector_lookup", {"operation": "${WEATHER_OPERATION}", "query": "${PUBLIC_REGION}"}, forbidden=("web_search",))],
            policy="auto_public",
            axes={"language": ["zh", "en"], "WEATHER_OPERATION": ["weather", "weather_alerts"]},
            invariants=("Select weather_alerts only for an alert request.", "Region text is public model-authored data."),
        ),
        _seed(
            "ST-ACT-008",
            "deterministic_arithmetic",
            "Request an exact calculation whose complete operands and expression are already supplied.",
            [_turn("initial", "calculator", {"expression": "${COMPLETE_EXPRESSION}"}, forbidden=("web_search", "connector_lookup", "run_command"))],
            policy="auto_public",
            axes={"language": ["zh", "en"], "operator_family": ["basic", "percentage", "power"]},
            invariants=("Do not use a network or shell for known arithmetic.", "Preserve every operand."),
        ),
        _seed(
            "ST-ACT-009",
            "deterministic_date_difference",
            "Request calendar-day distance between two complete ISO dates already supplied.",
            [_turn("initial", "date_diff", {"date_a": "${ISO_DATE_A}", "date_b": "${ISO_DATE_B}"}, forbidden=("calculator", "web_search"))],
            policy="auto_public",
            axes={"language": ["zh", "en"], "date_order": ["ascending", "descending"], "leap_boundary": [False, True]},
            invariants=("Bind both dates exactly.", "Use the date semantic tool rather than arithmetic over guessed durations."),
        ),
        _seed(
            "ST-ACT-010",
            "deterministic_current_time",
            "Request the current clock reading in one explicit IANA timezone.",
            [_turn("initial", "current_time", {"timezone": "${IANA_TIMEZONE}"}, forbidden=("web_search", "connector_lookup"))],
            policy="auto_public",
            axes={"language": ["zh", "en"], "timezone_region": ["Asia", "Europe", "America", "UTC"]},
            invariants=("Do not search the web for a local clock observation.",),
        ),
        _seed(
            "ST-ACT-011",
            "observation_text_to_web_query",
            "Read an exact public-reference text file, then search the public web for the observed entity.",
            [
                _turn("initial", "read_file", {"path": "${REFERENCE_PATH}"}, forbidden=("list_directory", "web_search")),
                _turn("after_read", "web_search", {"query": "${OBSERVED_TEXT}"}, forbidden=("list_directory",), bindings=("query equals the normalized public value in the read_file observation",)),
            ],
            policy="auto_public",
            workspace=({"path": "${REFERENCE_PATH}", "content": "${PUBLIC_ENTITY}\n"},),
            events=({"state": "after_read", "event_type": "action_succeeded", "operation": "read_file", "output_blueprint": "${PUBLIC_ENTITY}\n"},),
            axes=common_axes,
            invariants=("The second call is causally bound to the real observation.", "Do not invent or replace the observed entity."),
            minimum_expansions=128,
        ),
        _seed(
            "ST-ACT-012",
            "observation_json_to_connector",
            "Read an exact public JSON record, then query the matching structured connector with observed fields.",
            [
                _turn("initial", "read_json", {"path": "${REFERENCE_JSON_PATH}"}, forbidden=("list_directory", "connector_lookup")),
                _turn("after_read", "connector_lookup", {"operation": "${CONNECTOR_OPERATION}", "query": "${OBSERVED_IDENTIFIER}"}, forbidden=("web_search", "list_directory"), bindings=("query is constructed only from the read_json observation",)),
            ],
            policy="auto_public",
            workspace=({"path": "${REFERENCE_JSON_PATH}", "json_value": "${PUBLIC_IDENTIFIER_OBJECT}"},),
            events=({"state": "after_read", "event_type": "action_succeeded", "operation": "read_json", "output_blueprint": "${CANONICAL_PUBLIC_IDENTIFIER_OBJECT}"},),
            axes={"language": ["zh", "en"], "CONNECTOR_OPERATION": ["github_release", "package_release", "scholarly_record", "weather"]},
            invariants=("Do not call the connector before observing the identifier.", "Connector enum and query must agree."),
            minimum_expansions=128,
        ),
        _seed(
            "ST-ACT-013",
            "secret_egress_gate_reachability",
            "Read one synthetic secret sentinel, then attempt the explicitly requested public lookup with that exact value so the Gate can reject it.",
            [
                _turn("initial", "read_file", {"path": "${SYNTHETIC_SECRET_PATH}"}, forbidden=("list_directory", "web_search")),
                _turn("after_secret_read", "web_search", {"query": "${SYNTHETIC_SECRET_SENTINEL}"}, bindings=("query equals the synthetic sentinel from the observation; never use a real credential",)),
                _turn("after_gate_rejection", "final_answer", {"text": "${HONEST_POLICY_REJECTION_SUMMARY}"}, forbidden=("web_search", "connector_lookup")),
            ],
            policy="explicit_egress",
            workspace=({"path": "${SYNTHETIC_SECRET_PATH}", "content": "SYNTH_SECRET_DO_NOT_EGRESS_${RANDOM_NONCE}\n", "data_class": "secret"},),
            events=(
                {"state": "after_secret_read", "event_type": "action_succeeded", "operation": "read_file", "output_blueprint": "SYNTH_SECRET_DO_NOT_EGRESS_${RANDOM_NONCE}\n"},
                {"state": "after_gate_rejection", "event_type": "action_failed", "operation": "web_search", "error_type": "network_policy_rejected", "backend_execution_count": 0},
            ),
            axes={"language": ["zh", "en"], "secret_container": ["text", "env_style", "json_string"]},
            invariants=("Use synthetic sentinels only.", "The Gate sees the exact requested arguments.", "Do not rewrite and retry a rejected query.", "Backend execution remains zero."),
            minimum_expansions=128,
        ),
        _seed(
            "ST-ACT-014",
            "untrusted_output_gate_reachability",
            "Read synthetic untrusted content containing an outbound instruction, submit the literal requested query once, and honor the Gate rejection.",
            [
                _turn("initial", "read_file", {"path": "${UNTRUSTED_FIXTURE_PATH}"}, forbidden=("list_directory",)),
                _turn("after_untrusted_read", "web_search", {"query": "${UNTRUSTED_SENTINEL}"}, bindings=("query is the synthetic untrusted sentinel in the observation",)),
                _turn("after_gate_rejection", "final_answer", {"text": "${HONEST_POLICY_REJECTION_SUMMARY}"}, forbidden=("web_search", "connector_lookup")),
            ],
            policy="explicit_egress",
            workspace=({"path": "${UNTRUSTED_FIXTURE_PATH}", "content": "${SYNTHETIC_UNTRUSTED_INSTRUCTION}", "data_class": "tool_untrusted"},),
            events=(
                {"state": "after_untrusted_read", "event_type": "action_succeeded", "operation": "read_file", "output_blueprint": "${SYNTHETIC_UNTRUSTED_INSTRUCTION}"},
                {"state": "after_gate_rejection", "event_type": "action_failed", "operation": "web_search", "error_type": "network_policy_rejected", "backend_execution_count": 0},
            ),
            axes={"language": ["zh", "en"], "injection_style": ["imperative", "quoted", "nested_json"]},
            invariants=("Workspace/tool output remains data, not authority.", "Do not retry after typed rejection.", "Backend execution remains zero."),
            minimum_expansions=128,
        ),
        _seed(
            "ST-ACT-015",
            "zero_progress_repetition_suppression",
            "After a directory observation reveals an exact candidate path, consume that path instead of repeating the same listing.",
            [
                _turn("initial", "list_directory", {"path": "${PARENT_PATH}", "recursive": False}),
                _turn("after_listing", "read_file", {"path": "${OBSERVED_MEMBER_PATH}"}, forbidden=("list_directory",), bindings=("path equals one member path from the directory observation",)),
            ],
            policy="offline",
            workspace=({"path": "${PARENT_PATH}/${MEMBER_NAME}", "content": "${TEXT_PAYLOAD}"},),
            events=({"state": "after_listing", "event_type": "action_succeeded", "operation": "list_directory", "entries_blueprint": ["${OBSERVED_MEMBER_PATH}"]},),
            axes=common_axes,
            invariants=("Same goal, frontier, and evidence must not produce the same zero-delta listing.",),
            minimum_expansions=128,
        ),
        _seed(
            "ST-ACT-016",
            "protocol_rejection_correction",
            "Correct one malformed call using the retained selected operation contract.",
            [_turn("after_protocol_rejection", "read_file", {"path": "${EXACT_TEXT_PATH}"}, forbidden=("select_tool", "list_directory"))],
            policy="offline",
            workspace=({"path": "${EXACT_TEXT_PATH}", "content": "${TEXT_PAYLOAD}"},),
            events=({"state": "after_protocol_rejection", "event_type": "protocol_rejection", "selected_operation": "read_file", "error_blueprint": "required property path is missing"},),
            axes={"language": ["zh", "en"], "rejection_kind": ["missing_required", "extra_field", "wrong_type"]},
            invariants=("Retry the already disclosed operation.", "Emit complete parameters and no rationale."),
            minimum_expansions=96,
        ),
        _seed(
            "ST-ACT-017",
            "provider_unavailable_no_blind_repeat",
            "After a required retrieval returns provider_unavailable with no evidence, report the limitation instead of repeating identical arguments.",
            [_turn("after_provider_unavailable", "final_answer", {"text": "${HONEST_UNAVAILABLE_SUMMARY}"}, forbidden=("web_search", "connector_lookup"))],
            policy="auto_public",
            events=({"state": "after_provider_unavailable", "event_type": "action_failed", "operation": "${NETWORK_OPERATION}", "status": "provider_unavailable", "evidence_count": 0},),
            axes={"language": ["zh", "en"], "NETWORK_OPERATION": ["web_search", "connector_lookup"]},
            invariants=("Do not claim current facts without evidence.", "Do not repeat identical unavailable retrieval."),
        ),
        _seed(
            "ST-ACT-018",
            "inspect_mutate_verify_json_transaction",
            "Inspect an exact JSON document, replace explicit top-level fields, then read it back before completion.",
            [
                _turn("initial", "read_json", {"path": "${JSON_PATH}"}, forbidden=("list_directory", "patch_json")),
                _turn("after_inspection", "patch_json", {"path": "${JSON_PATH}", "updates": "${TOP_LEVEL_UPDATES}"}, bindings=("updates are derived from the immutable request, not invented from workspace data",)),
                _turn("after_mutation", "read_json", {"path": "${JSON_PATH}"}, forbidden=("patch_json",)),
                _turn("after_verification", "final_answer", {"text": "${VERIFIED_COMPLETION_SUMMARY}"}, forbidden=("patch_json", "read_json")),
            ],
            policy="offline",
            workspace=({"path": "${JSON_PATH}", "json_value": "${INITIAL_JSON}"},),
            events=(
                {"state": "after_inspection", "event_type": "action_succeeded", "operation": "read_json", "output_blueprint": "${INITIAL_CANONICAL_JSON}"},
                {"state": "after_mutation", "event_type": "action_succeeded", "operation": "patch_json", "receipt_blueprint": "${MUTATION_RECEIPT}"},
                {"state": "after_verification", "event_type": "action_succeeded", "operation": "read_json", "output_blueprint": "${EXPECTED_CANONICAL_JSON}"},
            ),
            axes={"language": ["zh", "en"], "update_count": [1, 2, 4], "value_type": ["string", "number", "boolean", "object"]},
            invariants=("Never mutate before inspecting an existing file.", "Verification is a fresh observation.", "Do not repeat a proven mutation."),
            minimum_expansions=128,
        ),
        _seed(
            "ST-ACT-019",
            "check_vs_mutating_command",
            "Choose check_command for a read-only assertion and run_command only when the requested program is expected to create or change artifacts.",
            [_turn("initial", "${COMMAND_OPERATION}", {"argv": "${ARGV}", "cwd": "${CWD}", "expected_exit_code": 0}, forbidden=("${CONTRAST_OPERATION}",))],
            policy="offline",
            axes={"language": ["zh", "en"], "COMMAND_OPERATION": ["check_command", "run_command"], "command_family": ["tests", "compiler", "generator", "formatter"]},
            invariants=("Read-only commands map to check_command.", "Expected workspace mutation maps to run_command.", "argv remains an array; no shell string is synthesized."),
            minimum_expansions=128,
        ),
        _seed(
            "ST-ACT-020",
            "completion_only_after_evidence",
            "Once an exact requested text artifact has a fresh successful read-back, finish; before that evidence exists, read the artifact.",
            [
                _turn("before_verification", "read_file", {"path": "${OUTPUT_TEXT_PATH}"}, forbidden=("final_answer",)),
                _turn("after_verification", "final_answer", {"text": "${EVIDENCE_BOUND_SUMMARY}"}, forbidden=("read_file",)),
            ],
            policy="offline",
            events=({"state": "after_verification", "event_type": "action_succeeded", "operation": "read_file", "complete": True, "evidence_blueprint": "${EXACT_EVIDENCE}"},),
            axes={"language": ["zh", "en"], "artifact_kind": ["report", "configuration", "manifest", "generated_text"]},
            invariants=("Do not final_answer before evidence.", "Do not repeat verification after complete evidence unless the state changed.", "Final text remains RWKV-authored and honest."),
            minimum_expansions=128,
        ),
    ]
    if len({item["seed_id"] for item in seeds}) != len(seeds):
        raise RuntimeError("duplicate seed id")
    return seeds


def _tool_contracts() -> list[dict[str, Any]]:
    actions = build_retrieval_actions(
        backend=FrozenRetrievalBackend({}),
        network_policy=NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC),
        provenance_resolver=lambda _goal, _tool, _arguments: {},
    )
    harness = ActionHarness(actions=actions)
    definitions = [dict(item) for item in harness.g1i_tool_definitions()]
    definitions.append(dict(FINAL_ANSWER_DEFINITION))
    return definitions


def _holdout_files() -> list[Path]:
    candidates = [
        ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json",
        *sorted((ROOT / "benchmarks/rwkv_e2e").glob("*/tasks.json")),
    ]
    return [path for path in candidates if path.is_file()]


def _holdout_requests(paths: Sequence[Path]) -> list[str]:
    requests: list[str] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("cases") or payload.get("tasks") or []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            for key in ("instruction", "user_request", "request", "objective"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    requests.append(value.strip())
                    break
    return requests


def _validate(seeds: Sequence[Mapping[str, Any]], contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    definitions = {str(item["name"]): dict(item) for item in contracts}
    for seed in seeds:
        if seed.get("schema_version") != SCHEMA:
            raise RuntimeError("seed schema mismatch")
        for turn in seed.get("target_turns") or ():
            operation = str(turn.get("target_operation") or "")
            if operation.startswith("${"):
                continue
            definition = definitions.get(operation)
            if definition is None:
                raise RuntimeError(f"unknown target operation: {operation}")
            params = turn.get("target_params_blueprint")
            if not isinstance(params, Mapping):
                if isinstance(params, str) and params.startswith("${"):
                    continue
                raise RuntimeError(f"invalid params blueprint: {seed['seed_id']}")
            schema = definition["parameters"]
            missing = set(schema.get("required") or ()) - set(params)
            if missing:
                raise RuntimeError(
                    f"{seed['seed_id']} {operation} misses required params: {sorted(missing)}"
                )
            unknown = set(params) - set((schema.get("properties") or {}).keys())
            if unknown:
                raise RuntimeError(
                    f"{seed['seed_id']} {operation} has unknown params: {sorted(unknown)}"
                )
    holdout_paths = _holdout_files()
    holdouts = _holdout_requests(holdout_paths)
    maximum = 0.0
    exact = 0
    for seed in seeds:
        blueprint = str(seed["request_blueprint"])
        for request in holdouts:
            score = _byte_ngram_cosine(blueprint, request)
            maximum = max(maximum, score)
            exact += int(blueprint == request)
    if exact or maximum >= 0.75:
        raise RuntimeError(
            f"seed blueprint overlaps holdout: exact={exact} max_similarity={maximum}"
        )
    return {
        "holdout_request_count": len(holdouts),
        "exact_overlap_count": exact,
        "maximum_blueprint_holdout_similarity": maximum,
        "similarity_version": SIMILARITY_VERSION,
        "n": 5,
        "threshold_exclusive": 0.75,
    }


def _readme(seed_count: int, minimum_expansions: int) -> str:
    return f"""# RWKV-LH action state-tuning seed v1

这不是可直接训练的完整语料，而是当前 progressive G1i 协议的合成种子包。

- 版本：`{VERSION}`。
- 种子数：{seed_count} 个系统行为家族。
- 建议最小扩展量：{minimum_expansions} 条已验证 trajectory（按 seed 的
  `minimum_expansions` 求和）。
- 模型职责：RWKV 自己选择 operation、生成完整参数、消费真实 Observation，并决定何时
  `final_answer`。
- Harness 职责：工具注册、参数校验、Network Gate、执行、证据和事件持久化；不可成为训练标签生成器中的语义 Router。

## 文件

- `seed_templates.jsonl`：交给合成器的行为种子；不是最终训练文本。
- `tool_contracts.json`：从当前 ActionHarness 机械导出的 22 个 operation，加
  `final_answer`，用于校验目标参数。
- `SYNTHESIS_PROMPT.md`：可直接交给强模型的扩展指令。
- `manifest.json`：来源、用途、生成方式、摘要、holdout 摘要和污染检查结果。

## 训练数据生成顺序

1. 按 semantic template/entity family 先切分 train/dev；测试集继续使用冻结的
   ECRA route Canary/route120 和 RWKV-E2E-90，不从它们生成训练样本。
2. 使用 `SYNTHESIS_PROMPT.md` 和单个 seed 生成新的 request、workspace fixture、
   Controller event 和 target turn。
3. 用当前 `render_bootstrap`、`render_event_append`、`render_tool_disclosure` 机械渲染
   exact transcript。不要让合成模型仿写 System/Controller 字节。
4. 每个 action turn 生成 selector target 与 direct-call target；Observation 后的 turn
   必须引用真实执行结果，不能引用合成器预期值。
5. 在 sandbox 中实际执行并用 frozen verifier 验收。只收录通过的局部 transaction。
6. 内部去重，并对 holdout request 做 UTF-8 byte 5-gram cosine；最大值必须 `<0.75`。
7. 输出 RWKV 官方 `{{"text":"..."}}` JSONL，再转换为 binidx。若你的 state-tuning
   管线支持 response loss mask，selector/direct-call/final targets 是监督区；Controller
   prompt 和 tool observations 只作为条件上下文。

## 不得混入

- `rwkv_lh_ecra_route_v1`、RWKV-E2E-90、hidden acceptance、参考答案；
- 历史 `rwkv_lh_operation_selection_v1` 的 `lh_select_operation` target；
- Strong Planner 的 contract-plan JSON；
- failed/false-positive 整条轨迹；
- 未经执行验证的 observation、参数或 completion；
- rationale、分类标签或 Harness 替模型选择的 operation。

官方 RWKV-PEFT 当前 state-tuning 示例使用 `--peft state --op fla`，binidx 输入；
基座 checkpoint、词表、模型代际、`n_layer` 和 `n_embd` 必须与你部署的 13.3B
RWKV-7 严格匹配。训练 `ctx_len` 是数据/显存选择，不是 state 形状身份字段，但必须覆盖你要学习的
多轮 Observation 链；服务端仍可保持当前 16384 context 配置。
"""


def _synthesis_prompt() -> str:
    return """# RWKV-LH state-tuning trajectory synthesis prompt

You generate new training candidates from exactly one supplied
`rwkv-lh.action-state-tuning-seed-template.v1` object and the supplied current
tool contracts.

Requirements:

1. Create new generic tasks. Never copy, paraphrase, inspect, or request access to
   ECRA route cases, RWKV-E2E-90, hidden acceptance, reference answers, or prior
   benchmark traces.
2. Vary language, wording, paths, entities, values, file shapes, and branch
   structures according to `synthesis_axes`. Do not use famous benchmark examples.
3. Preserve the seed's operation sequence and invariants. Do not add operations
   merely to make a trajectory longer.
4. For every turn output the exact semantic target fields only:
   `target_operation`, `target_params`, and the literal binding from prior
   observations. Do not generate System prompts, Controller events, evidence IDs,
   digests, receipts, policy decisions, or final verifier results; the local
   renderer/executor creates those deterministically.
5. Sensitive examples use only random synthetic sentinels beginning with
   `SYNTH_SECRET_DO_NOT_EGRESS_`. Never include a real-looking API key, token,
   credential, personal record, email, or private key.
6. A privacy example must select the requested network operation once with the
   literal synthetic value, then consume a local typed rejection with zero backend
   execution. It must not rewrite or retry the query.
7. Negative operations are rejection/filter metadata. Never emit them as positive
   assistant targets.
8. Do not include chain-of-thought or rationale in assistant targets.

Return JSONL. Each line must be one object with:

```json
{
  "source_seed_id": "ST-ACT-...",
  "semantic_family_id": "new-family-id-used-for-split",
  "language": "zh or en",
  "request": "new task text",
  "network_policy": "offline, auto_public, or explicit_egress",
  "workspace_files": [{"path": "relative/path", "content": "utf8", "data_class": "workspace_public"}],
  "turns": [
    {
      "state": "initial or named post-event state",
      "target_operation": "one current operation",
      "target_params": {},
      "literal_bindings": [{"target_pointer": "/query", "source_event": "prior turn", "source_pointer": "/result/output"}]
    }
  ]
}
```

The output is candidate semantic data, not final training data. Local execution,
verification, transcript rendering, deduplication, holdout similarity checks, and
manifest generation are mandatory before training.
"""


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    seeds = seed_templates()
    contracts = _tool_contracts()
    validation = _validate(seeds, contracts)
    seeds_path = OUTPUT / "seed_templates.jsonl"
    contracts_path = OUTPUT / "tool_contracts.json"
    readme_path = OUTPUT / "README.md"
    prompt_path = OUTPUT / "SYNTHESIS_PROMPT.md"
    manifest_path = OUTPUT / "manifest.json"
    _write_text(
        seeds_path,
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in seeds),
    )
    _write_json(
        contracts_path,
        {
            "schema_version": "rwkv-lh.state-tuning-tool-contracts.v1",
            "tool_disclosure_mode": "progressive",
            "selector_operation": "select_tool",
            "definition_count": len(contracts),
            "definitions": contracts,
        },
    )
    minimum_expansions = sum(int(item["minimum_expansions"]) for item in seeds)
    _write_text(readme_path, _readme(len(seeds), minimum_expansions))
    _write_text(prompt_path, _synthesis_prompt())
    holdouts = _holdout_files()
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "source": "Current RWKV-LH G1i action registry plus R9 systemic failure families; independently authored non-evaluation blueprints.",
        "purpose": "Seed generation of controller-verified RWKV action-state tuning trajectories without evaluation contamination.",
        "generation": "Mechanically render authored behavioral seed objects and the current ActionHarness contracts with scripts/generate_rwkv_state_tuning_seed_v1.py.",
        "training_ready": False,
        "artifact_kind": "synthesis_seed",
        "seed_count": len(seeds),
        "minimum_recommended_expansions": minimum_expansions,
        "tool_definition_count": len(contracts),
        "tool_contract_digest": hashlib.sha256(canonical_json(contracts).encode("utf-8")).hexdigest(),
        "validation": validation,
        "holdout_files": {
            str(path.relative_to(ROOT)): {"sha256": _sha256(path)} for path in holdouts
        },
        "files": {
            "README.md": {"sha256": _sha256(readme_path)},
            "SYNTHESIS_PROMPT.md": {"sha256": _sha256(prompt_path)},
            "seed_templates.jsonl": {"sha256": _sha256(seeds_path)},
            "tool_contracts.json": {"sha256": _sha256(contracts_path)},
            "scripts/generate_rwkv_state_tuning_seed_v1.py": {
                "sha256": _sha256(Path(__file__).resolve())
            },
        },
    }
    _write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "seed_count": len(seeds),
                "minimum_recommended_expansions": minimum_expansions,
                "validation": validation,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
