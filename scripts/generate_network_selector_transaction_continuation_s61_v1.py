#!/usr/bin/env python3
"""Generate the preregistered S61 Selector continuation/retention corpus."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from rwkv_lh.exact_tool_selector.compact_protocol_v7 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    SELECTOR_CURRENT_QUESTION,
    compact_selector_input_digest,
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SELECTOR_STAGE_PROJECTION_VERSION,
    render_selector_stage_objective,
)
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_TRANSACTION_CONTINUATION_S61_20260830"
)
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
S60 = (
    ROOT
    / "data/datasets/rwkv_lh_network_selector_requirement_byte_tail_s60_v1"
)
RENDERER = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v7.py"
LADDER = ROOT / "benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1"
OUTPUT = (
    ROOT
    / "data/datasets/rwkv_lh_network_selector_transaction_continuation_s61_v1"
)

DATASET_VERSION = "rwkv-lh.network-selector.transaction-continuation-s61.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-transaction-continuation-prefix.s61.v1"
STATE_ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s61.v1"
TARGET_PREFIX = "\nSelectorLabelV7: "
CTX_LEN = 2496
SEED = 1061
FOCUS_COUNTS = {"train": 1000, "dev": 250, "test": 250}
RETENTION_COUNTS = {"train": 1000, "dev": 250, "test": 250}
RETENTION_PER_LABEL_LANGUAGE = {"train": 20, "dev": 5, "test": 5}
SPLITS = ("train", "dev", "test")
FOCUS_SCENARIOS = (
    "initial_text_write",
    "initial_json_write",
    "json_after_text",
    "text_after_json",
    "third_text_root",
    "replace_after_list",
    "patch_after_json_read",
    "repair_after_failed_check",
    "check_after_writes",
    "check_after_mutation",
    "finish_after_check",
    "rejected_early_finish",
    "retry_failed_writer",
    "write_web_evidence",
    "write_connector_record",
    "write_after_file_read",
)

FROZEN = {
    PREREGISTRATION: (
        "53f5ae53f2459d760631aa93f9cf7fd693ee43274dc767455b9634fdfda5d8b0"
    ),
    S60 / "cases.jsonl": (
        "3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf"
    ),
    S60 / "manifest.json": (
        "16d05f9a7e4e5c94f3f314ec5848384b96b95045609fde25d92cfb3d497be76f"
    ),
    RENDERER: (
        "312e490f92fcc0d20dc8a78038291d15e298e6c8e27ae20eaff41fe7f38686f0"
    ),
    LADDER / "tasks.json": (
        "23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb"
    ),
    LADDER / "acceptance.json": (
        "f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06"
    ),
}

SPLIT_LEXICON = {
    "train": {
        "root": "quartz-workshop",
        "subject": "raven capsule",
        "zh_subject": "石英工坊批次",
    },
    "dev": {
        "root": "indigo-foundry",
        "subject": "tern packet",
        "zh_subject": "靛蓝铸造批次",
    },
    "test": {
        "root": "saffron-studio",
        "subject": "lynx parcel",
        "zh_subject": "藏红花工作室批次",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hex(*parts: object) -> str:
    return hashlib.sha256(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()


def canonical_row(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_row(row) + "\n")


def parse_v7_step(text: str) -> dict[str, Any]:
    prefix = "SelectorStepV7: "
    if not text.startswith(prefix):
        raise RuntimeError("S61 requires a V7 Selector step")
    payload = json.loads(text.removeprefix(prefix))
    question = payload.get("current_question")
    if not (
        list(payload)[-1] == "current_question"
        and isinstance(question, Mapping)
        and list(question) == ["question", "current_stage", "complete_requirement"]
        and question.get("question") == SELECTOR_CURRENT_QUESTION
    ):
        raise RuntimeError("S61 current question contract changed")
    return payload


def task_from_step(text: str) -> str:
    return str(parse_v7_step(text)["current_question"]["complete_requirement"])


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    raw = text.encode("utf-8")
    return Counter(raw[index : index + n] for index in range(max(0, len(raw) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return dot / math.sqrt(
        sum(value * value for value in left.values())
        * sum(value * value for value in right.values())
    )


def walk_forbidden_paths(value: Any, result: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "path" and isinstance(item, str) and item not in {"", "."}:
                result.add(item)
            if key == "files" and isinstance(item, list):
                result.update(
                    str(path) for path in item if isinstance(path, str) and path
                )
            walk_forbidden_paths(item, result)
    elif isinstance(value, list):
        for item in value:
            walk_forbidden_paths(item, result)


def ladder_contract() -> tuple[list[tuple[str, str]], set[str], set[str]]:
    tasks = json.loads((LADDER / "tasks.json").read_text(encoding="utf-8"))
    acceptance = json.loads(
        (LADDER / "acceptance.json").read_text(encoding="utf-8")
    )
    references = [
        (str(item["task_id"]), str(item["user_request"]))
        for item in tasks["tasks"]
    ]
    forbidden_paths: set[str] = set()
    walk_forbidden_paths(tasks, forbidden_paths)
    walk_forbidden_paths(acceptance, forbidden_paths)
    task_ids = {identity for identity, _request in references}
    return references, forbidden_paths, task_ids


def contains_holdout_literal(
    request: str,
    *,
    forbidden_paths: set[str],
    task_ids: set[str],
) -> bool:
    return any(value in request for value in forbidden_paths | task_ids)


@dataclass(frozen=True)
class ActionFact:
    operation: str
    success: bool = True
    outcome_type: str = "success"
    complete: bool | None = None
    truncated: bool | None = None

    def latest(self, sequence: int) -> dict[str, object]:
        value: dict[str, object] = {
            "sequence": sequence,
            "operation": self.operation,
            "success": self.success,
            "outcome_type": self.outcome_type,
        }
        if self.complete is not None:
            value["complete"] = self.complete
        if self.truncated is not None:
            value["truncated"] = self.truncated
        return value


@dataclass(frozen=True)
class FocusCase:
    request: str
    actions: tuple[ActionFact, ...]
    label: str
    rejected_selection: bool = False


def focus_case(scenario: str, split: str, index: int, language: str) -> FocusCase:
    lexicon = SPLIT_LEXICON[split]
    token = stable_hex("S61", split, scenario, index)[:12]
    root = str(lexicon["root"])
    text_a = f"drafts/{root}/{token}-brief.txt"
    text_b = f"reports/{root}/{token}-note.txt"
    text_c = f"evidence/{root}/{token}-source.txt"
    json_a = f"records/{root}/{token}-config.json"
    json_b = f"catalog/{root}/{token}-entry.json"
    source_text = f"inputs/{root}/{token}-source.txt"
    source_json = f"inputs/{root}/{token}-source.json"
    target_text = f"modules/{root}/{token}-module.txt"
    check = f"checks/{root}/{token}-audit.py"
    directory = f"packages/{root}/{token}"
    query = f"public release notice {root} {token}"
    repository = f"{root}/{token}-registry"
    subject = str(lexicon["subject"] if language == "en" else lexicon["zh_subject"])

    if language == "en":
        templates = {
            "initial_text_write": (
                f"For {subject} {token}, first create the complete text artifact {text_a}; "
                f"then create JSON {json_a}; finally run python {check} and finish only on success."
            ),
            "initial_json_write": (
                f"For {subject} {token}, first create the complete JSON record {json_a}; "
                f"then create text {text_a}; run python {check}, then report completion."
            ),
            "json_after_text": (
                f"Complete {subject} {token} in order: write text {text_a}, next write JSON "
                f"{json_a}, then run python {check}; do not finish before all three steps."
            ),
            "text_after_json": (
                f"Complete {subject} {token} in order: write JSON {json_a}, next write text "
                f"{text_a}, then run python {check}; finish only after the check passes."
            ),
            "third_text_root": (
                f"Build three ordered roots for {subject} {token}: text {text_a}, JSON {json_a}, "
                f"then text {text_b}. Run python {check} only after all three exist."
            ),
            "replace_after_list": (
                f"First list bounded metadata under {directory}; then replace exactly one old "
                f"marker in {target_text}; next run python {check} and finish after success."
            ),
            "patch_after_json_read": (
                f"First read JSON {source_json}; then update its explicit top-level status key "
                f"while preserving other keys; run python {check} and finish after success."
            ),
            "repair_after_failed_check": (
                f"Read {target_text}, run python {check}, and if that check fails replace the "
                f"single stale line in {target_text}; rerun the check before finishing."
            ),
            "check_after_writes": (
                f"Write text {text_a}, then JSON {json_a}, then run python {check}. Only a "
                f"successful check permits the final response for {subject} {token}."
            ),
            "check_after_mutation": (
                f"List {directory}, replace one exact token in {target_text}, then run python "
                f"{check}; do not stop after the replacement."
            ),
            "finish_after_check": (
                f"Create text {text_a} and JSON {json_a}, run python {check}, and return the "
                f"final result only when that check succeeds for {subject} {token}."
            ),
            "rejected_early_finish": (
                f"Create text {text_a} first and JSON {json_a} second. Both roots are mandatory "
                f"before any final response for {subject} {token}."
            ),
            "retry_failed_writer": (
                f"Create the mandatory complete text file {text_a}; if that write fails, retry "
                f"the same text-file responsibility before running python {check}."
            ),
            "write_web_evidence": (
                f"Search the public web for '{query}', then preserve the evidence as text in "
                f"{text_c}; run python {check} before reporting completion."
            ),
            "write_connector_record": (
                f"Query the structured repository source for {repository}, then save the record "
                f"as complete JSON {json_b}; run python {check} before finishing."
            ),
            "write_after_file_read": (
                f"Read source text {source_text}, then create the derived text artifact {text_b}; "
                f"run python {check} and finish only after it passes."
            ),
        }
    else:
        templates = {
            "initial_text_write": (
                f"处理{subject}{token}：先完整创建文本文件 {text_a}，再创建 JSON {json_a}，"
                f"最后运行 python {check}，成功后才能结束。"
            ),
            "initial_json_write": (
                f"处理{subject}{token}：先完整创建 JSON {json_a}，再创建文本 {text_a}，"
                f"运行 python {check} 后再汇报完成。"
            ),
            "json_after_text": (
                f"按顺序完成{subject}{token}：写入文本 {text_a}，接着写入 JSON {json_a}，"
                f"然后运行 python {check}；三步未完成不得结束。"
            ),
            "text_after_json": (
                f"按顺序完成{subject}{token}：写入 JSON {json_a}，接着写入文本 {text_a}，"
                f"然后运行 python {check}，校验通过后才能结束。"
            ),
            "third_text_root": (
                f"为{subject}{token}依次创建三个根：文本 {text_a}、JSON {json_a}、文本 {text_b}；"
                f"三个都存在后再运行 python {check}。"
            ),
            "replace_after_list": (
                f"先列出 {directory} 的有界元数据，再替换 {target_text} 中唯一的旧标记，"
                f"随后运行 python {check}，成功后结束。"
            ),
            "patch_after_json_read": (
                f"先读取 JSON {source_json}，再只更新其顶层 status 键并保留其他键，"
                f"之后运行 python {check}，成功后结束。"
            ),
            "repair_after_failed_check": (
                f"读取 {target_text} 并运行 python {check}；若检查失败，替换 {target_text} "
                f"中的一行旧内容，重新检查通过后才能结束。"
            ),
            "check_after_writes": (
                f"先写文本 {text_a}，再写 JSON {json_a}，然后运行 python {check}；"
                f"只有检查成功才能给出{subject}{token}的最终答复。"
            ),
            "check_after_mutation": (
                f"列出 {directory}，替换 {target_text} 中一个精确标记，然后运行 python {check}；"
                f"不能在替换后直接结束。"
            ),
            "finish_after_check": (
                f"创建文本 {text_a} 和 JSON {json_a}，运行 python {check}；"
                f"检查成功且全部完成后才返回{subject}{token}的最终结果。"
            ),
            "rejected_early_finish": (
                f"先创建文本 {text_a}，再创建 JSON {json_a}；两个根都是{subject}{token}的"
                f"强制要求，完成前不得给出最终答复。"
            ),
            "retry_failed_writer": (
                f"必须完整创建文本文件 {text_a}；如果写入失败，先重试同一文本写入职责，"
                f"之后才能运行 python {check}。"
            ),
            "write_web_evidence": (
                f"先在公开网络检索“{query}”，再把证据写入文本 {text_c}，"
                f"运行 python {check} 后才能汇报完成。"
            ),
            "write_connector_record": (
                f"先从结构化仓库源查询 {repository}，再把记录完整写成 JSON {json_b}，"
                f"运行 python {check} 后才能结束。"
            ),
            "write_after_file_read": (
                f"先读取源文本 {source_text}，再创建派生文本 {text_b}，"
                f"运行 python {check} 通过后才能结束。"
            ),
        }

    actions: tuple[ActionFact, ...]
    label: str
    rejected = False
    if scenario == "initial_text_write":
        actions, label = (), "write_file"
    elif scenario == "initial_json_write":
        actions, label = (), "write_json"
    elif scenario == "json_after_text":
        actions, label = (ActionFact("write_file"),), "write_json"
    elif scenario == "text_after_json":
        actions, label = (ActionFact("write_json"),), "write_file"
    elif scenario == "third_text_root":
        actions = (ActionFact("write_file"), ActionFact("write_json"))
        label = "write_file"
    elif scenario == "replace_after_list":
        actions = (ActionFact("list_directory", complete=True, truncated=False),)
        label = "replace_text"
    elif scenario == "patch_after_json_read":
        actions, label = (ActionFact("read_json", complete=True, truncated=False),), "patch_json"
    elif scenario == "repair_after_failed_check":
        actions = (
            ActionFact("read_file", complete=True, truncated=False),
            ActionFact("check_command", success=False, outcome_type="nonzero"),
        )
        label = "replace_text"
    elif scenario == "check_after_writes":
        actions = (ActionFact("write_file"), ActionFact("write_json"))
        label = "check_command"
    elif scenario == "check_after_mutation":
        actions = (
            ActionFact("list_directory", complete=True, truncated=False),
            ActionFact("replace_text"),
        )
        label = "check_command"
    elif scenario == "finish_after_check":
        actions = (
            ActionFact("write_file"),
            ActionFact("write_json"),
            ActionFact("check_command"),
        )
        label = "final_answer"
    elif scenario == "rejected_early_finish":
        actions, label, rejected = (ActionFact("write_file"),), "write_json", True
    elif scenario == "retry_failed_writer":
        actions = (ActionFact("write_file", success=False, outcome_type="error"),)
        label = "write_file"
    elif scenario == "write_web_evidence":
        actions, label = (ActionFact("web_search"),), "write_file"
    elif scenario == "write_connector_record":
        actions, label = (ActionFact("connector_lookup"),), "write_json"
    elif scenario == "write_after_file_read":
        actions, label = (ActionFact("read_file", complete=True, truncated=False),), "write_file"
    else:
        raise ValueError(scenario)
    return FocusCase(
        request=templates[scenario],
        actions=actions,
        label=label,
        rejected_selection=rejected,
    )


def selector_input(
    request: str,
    actions: tuple[ActionFact, ...],
    *,
    parent_action_index: int,
    protocol_rejection_count: int,
) -> NetworkSelectorInput:
    latest = actions[-1] if actions else None
    latest_fact = latest.latest(len(actions)) if latest is not None else None
    new_actions = actions[parent_action_index:]
    return NetworkSelectorInput.create(
        task_request=request,
        stage_objective=render_selector_stage_objective(latest_fact),
        stage_role="work",
        progress=NetworkSelectorProgress(
            completed_stage_count=len(actions),
            action_index=len(actions),
            succeeded_operations=tuple(item.operation for item in new_actions if item.success),
            failed_operations=tuple(item.operation for item in new_actions if not item.success),
            protocol_rejection_count=protocol_rejection_count,
        ),
    )


def focus_row(split: str, index: int) -> dict[str, Any]:
    scenario = FOCUS_SCENARIOS[index % len(FOCUS_SCENARIOS)]
    language = "en" if index % 2 == 0 else "zh"
    case = focus_case(scenario, split, index, language)
    inputs: list[NetworkSelectorInput] = []
    for position in range(len(case.actions) + 1):
        inputs.append(
            selector_input(
                case.request,
                case.actions[:position],
                parent_action_index=max(0, position - 1),
                protocol_rejection_count=0,
            )
        )
    if case.rejected_selection:
        current = selector_input(
            case.request,
            case.actions,
            parent_action_index=len(case.actions),
            protocol_rejection_count=1,
        )
        prior_inputs = inputs
    else:
        current = inputs[-1]
        prior_inputs = inputs[:-1]
    bootstrap = render_compact_selector_bootstrap(current)
    prior_steps = [render_compact_selector_step(item) for item in prior_inputs]
    step = render_compact_selector_step(current)
    rendered = bootstrap + "".join("\n" + item for item in [*prior_steps, step])
    expected_tail = json.dumps(
        case.request,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "}}"
    if not rendered.endswith(expected_tail):
        raise RuntimeError("S61 focus request is not the literal byte tail")
    token = stable_hex("S61-focus", split, scenario, index)[:24]
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": DATASET_VERSION,
        "sample_id": f"S61-F-{token}",
        "trajectory_id": f"S61-FOCUS-{token}",
        "trajectory_position": len(prior_steps),
        "split": split,
        "cohort": "focus",
        "focus_scenario": scenario,
        "continuation_boundary": (
            "final" if case.label == "final_answer" else "continue"
        ),
        "source_kind": "synthetic_mechanical_current_trajectory",
        "source_family_id": f"s61-focus:{split}:{scenario}:{token}",
        "source_sample_id": "",
        "retention_source_dataset": "",
        "language": language,
        "label": case.label,
        "task_request": case.request,
        "stage_objective": current.stage_objective,
        "progress": current.progress.to_dict(),
        "selector_input_sha256": compact_selector_input_digest(current),
        "bootstrap": bootstrap,
        "prior_steps": prior_steps,
        "step": step,
        "rendered_input": rendered,
        "rendered_input_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "compact_menu_digest": compact_selector_menu_digest(),
        "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
        "complete_requirement_byte_tail": True,
        "current_requirement_is_full_task": True,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
        "contains_planner_text": False,
        "generated_rwkv_text": False,
        "hidden_acceptance_used": False,
        "label_generation": "mechanical_ordered_workflow_position",
    }


def retention_row(source: Mapping[str, Any]) -> dict[str, Any]:
    payload = parse_v7_step(str(source["step"]))
    question = payload["current_question"]
    request = str(question["complete_requirement"])
    progress = dict(payload["progress"])
    source_id = str(source["sample_id"])
    token = stable_hex("S61-retention", source_id)[:24]
    label = str(source["label"])
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": DATASET_VERSION,
        "sample_id": f"S61-R-{token}",
        "trajectory_id": f"S61-RETENTION-{token}",
        "trajectory_position": len(source["prior_steps"]),
        "split": str(source["split"]),
        "cohort": "retention",
        "focus_scenario": "",
        "continuation_boundary": "final" if label == "final_answer" else "continue",
        "source_kind": "frozen_s60_balanced_retention",
        "source_family_id": (
            "s60-retention:"
            + str(source.get("source_dataset") or "unknown")
            + ":"
            + str(source.get("source_trajectory_id") or source["trajectory_id"])
        ),
        "source_sample_id": source_id,
        "retention_source_dataset": str(source.get("source_dataset") or ""),
        "language": str(source["language"]),
        "label": label,
        "task_request": request,
        "stage_objective": str(question["current_stage"]),
        "progress": progress,
        "selector_input_sha256": str(source["input_digest"]),
        "bootstrap": str(source["bootstrap"]),
        "prior_steps": list(source["prior_steps"]),
        "step": str(source["step"]),
        "rendered_input": str(source["rendered_input"]),
        "rendered_input_sha256": str(source["rendered_input_sha256"]),
        "compact_input_schema_version": str(source["compact_input_schema_version"]),
        "compact_menu_digest": str(source["compact_menu_digest"]),
        "projection_version": str(source.get("projection_version") or "inherited-s60"),
        "complete_requirement_byte_tail": True,
        "current_requirement_is_full_task": True,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
        "contains_planner_text": False,
        "generated_rwkv_text": False,
        "hidden_acceptance_used": False,
        "label_generation": "frozen_s60_label_unchanged",
    }


def select_retention(
    tokenizer: RWKVTokenizer,
    *,
    forbidden_paths: set[str],
    task_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_requests: dict[str, set[str]] = {split: set() for split in SPLITS}
    with (S60 / "cases.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            source = json.loads(line)
            split = str(source["split"])
            label = str(source["label"])
            language = str(source["language"])
            key = (split, label, language)
            quota = RETENTION_PER_LABEL_LANGUAGE[split]
            if len(selected[key]) >= quota:
                continue
            request = task_from_step(str(source["step"]))
            if (
                request in seen_requests[split]
                or contains_holdout_literal(
                    request,
                    forbidden_paths=forbidden_paths,
                    task_ids=task_ids,
                )
            ):
                continue
            target = TARGET_PREFIX + label
            prompt = str(source["rendered_input"])
            prompt_tokens = tokenizer.encode(prompt)
            target_tokens = tokenizer.encode(target)
            if tokenizer.encode(prompt + target) != prompt_tokens + target_tokens:
                continue
            if 1 + len(prompt_tokens) + len(target_tokens) > CTX_LEN + 1:
                continue
            selected[key].append(retention_row(source))
            seen_requests[split].add(request)
    result = {split: [] for split in SPLITS}
    for split in SPLITS:
        quota = RETENTION_PER_LABEL_LANGUAGE[split]
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                rows = selected[(split, label, language)]
                if len(rows) != quota:
                    raise RuntimeError(
                        f"S61 retention quota unavailable: {split}:{label}:{language}:"
                        f"{len(rows)}/{quota}"
                    )
                result[split].extend(rows)
        if len(result[split]) != RETENTION_COUNTS[split]:
            raise RuntimeError(f"S61 retention count changed: {split}")
    return result


def validate_and_export_state_rows(
    tokenizer: RWKVTokenizer,
    rows_by_split: Mapping[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    exports: dict[str, list[dict[str, Any]]] = {"train": [], "dev": []}
    minimum = 10**9
    maximum_prompt = 0
    maximum_text = 0
    for split in ("train", "dev"):
        for index, row in enumerate(rows_by_split[split]):
            prompt = str(row["rendered_input"])
            target = TARGET_PREFIX + str(row["label"])
            prompt_tokens = tokenizer.encode(prompt)
            target_tokens = tokenizer.encode(target)
            text_tokens = tokenizer.encode(prompt + target)
            if text_tokens != prompt_tokens + target_tokens:
                raise RuntimeError(f"S61 target boundary is not additive: {row['sample_id']}")
            if 1 + len(text_tokens) > CTX_LEN + 1:
                raise RuntimeError(f"S61 target would be truncated: {row['sample_id']}")
            minimum = min(minimum, 1 + len(prompt_tokens))
            maximum_prompt = max(maximum_prompt, 1 + len(prompt_tokens))
            maximum_text = max(maximum_text, 1 + len(text_tokens))
            exports[split].append(
                {
                    "schema_version": STATE_ROW_SCHEMA,
                    "dataset_version": DATASET_VERSION,
                    "sample_id": f"S61-STATE-{split.upper()}-{index:04d}",
                    "source_sample_id": row["sample_id"],
                    "source_family_id": row["source_family_id"],
                    "split": split,
                    "cohort": row["cohort"],
                    "focus_scenario": row["focus_scenario"],
                    "label": row["label"],
                    "language": row["language"],
                    "prompt": prompt,
                    "prompt_sha256": row["rendered_input_sha256"],
                    "target": target,
                    "text": prompt + target,
                    "prompt_tokens_including_bos": 1 + len(prompt_tokens),
                    "target_tokens": len(target_tokens),
                    "text_tokens_including_bos": 1 + len(text_tokens),
                    "loss_mask": "target_suffix",
                    "jsonl_bos_token_id": 0,
                    "persistent_history_replayed": True,
                    "request_last": True,
                    "generated_rwkv_text": False,
                    "raw_rwkv_output_modified": False,
                }
            )
    return exports, {
        "minimum_prompt_tokens_including_bos": minimum,
        "maximum_prompt_tokens_including_bos": maximum_prompt,
        "maximum_text_tokens_including_bos": maximum_text,
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S61 dataset")
    for path, expected in FROZEN.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S61 frozen input changed: {path}: {actual}")

    tokenizer = RWKVTokenizer()
    holdout_references, forbidden_paths, task_ids = ladder_contract()
    focus = {
        split: [focus_row(split, index) for index in range(FOCUS_COUNTS[split])]
        for split in SPLITS
    }
    for split, rows in focus.items():
        if Counter(row["language"] for row in rows) != Counter(
            {"en": len(rows) // 2, "zh": len(rows) // 2}
        ):
            raise RuntimeError(f"S61 focus language balance changed: {split}")
        for row in rows:
            if contains_holdout_literal(
                str(row["task_request"]),
                forbidden_paths=forbidden_paths,
                task_ids=task_ids,
            ):
                raise RuntimeError(f"S61 focus contains Ladder literal: {row['sample_id']}")
    retention = select_retention(
        tokenizer,
        forbidden_paths=forbidden_paths,
        task_ids=task_ids,
    )

    rows_by_split = {
        split: focus[split] + retention[split]
        for split in SPLITS
    }
    expected_counts = {"train": 2000, "dev": 500, "test": 500}
    if {split: len(rows) for split, rows in rows_by_split.items()} != expected_counts:
        raise RuntimeError("S61 split counts changed")
    all_rows = [row for split in SPLITS for row in rows_by_split[split]]
    if len({str(row["sample_id"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S61 sample ids are not unique")
    if len({str(row["rendered_input_sha256"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S61 rendered prompts are not unique")
    role_fields = (
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "contains_planner_text",
        "generated_rwkv_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in all_rows for field in role_fields):
        raise RuntimeError("S61 role purity changed")
    if any(row["label"] not in NETWORK_EXACT_TOOL_LABELS for row in all_rows):
        raise RuntimeError("S61 label set changed")

    request_splits: dict[str, set[str]] = {
        split: {str(row["task_request"]) for row in rows_by_split[split]}
        for split in SPLITS
    }
    family_splits: dict[str, set[str]] = {
        split: {str(row["source_family_id"]) for row in rows_by_split[split]}
        for split in SPLITS
    }
    for left_index, left in enumerate(SPLITS):
        for right in SPLITS[left_index + 1 :]:
            if request_splits[left] & request_splits[right]:
                raise RuntimeError(f"S61 request overlap: {left}/{right}")
            if family_splits[left] & family_splits[right]:
                raise RuntimeError(f"S61 source-family overlap: {left}/{right}")

    reference_grams = [
        (identity, byte_ngrams(request))
        for identity, request in holdout_references
    ]
    maximum_similarity: dict[str, Any] = {
        "score": -1.0,
        "sample_id": "",
        "holdout_id": "",
    }
    request_gram_cache: dict[str, Counter[bytes]] = {}
    for row in all_rows:
        request = str(row["task_request"])
        grams = request_gram_cache.setdefault(request, byte_ngrams(request))
        for holdout_id, reference in reference_grams:
            score = cosine(grams, reference)
            if score > float(maximum_similarity["score"]):
                maximum_similarity = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": holdout_id,
                }
    if float(maximum_similarity["score"]) >= 0.95:
        raise RuntimeError(f"S61 Ladder similarity gate failed: {maximum_similarity}")

    state_rows, token_stats = validate_and_export_state_rows(tokenizer, rows_by_split)
    if {split: len(rows) for split, rows in state_rows.items()} != {
        "train": 2000,
        "dev": 500,
    }:
        raise RuntimeError("S61 state export counts changed")

    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, all_rows)
    state_paths = {
        split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in ("train", "dev")
    }
    for split, path in state_paths.items():
        write_jsonl(path, state_rows[split])

    manifest = {
        "schema_version": "rwkv-lh.network-selector-transaction-continuation-manifest.s61.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": (
            "production V7 continuation/final boundary recovery with balanced "
            "S60 capability retention"
        ),
        "counts": expected_counts,
        "cohort_counts": {
            split: dict(sorted(Counter(row["cohort"] for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "label_counts": {
            split: dict(sorted(Counter(row["label"] for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "focus_label_counts": {
            split: dict(sorted(Counter(row["label"] for row in focus[split]).items()))
            for split in SPLITS
        },
        "focus_scenario_counts": {
            split: dict(
                sorted(Counter(row["focus_scenario"] for row in focus[split]).items())
            )
            for split in SPLITS
        },
        "language_counts": {
            split: dict(sorted(Counter(row["language"] for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "retention": {
            "source": str(S60.relative_to(ROOT)),
            "cases_sha256": FROZEN[S60 / "cases.jsonl"],
            "manifest_sha256": FROZEN[S60 / "manifest.json"],
            "per_label_language": RETENTION_PER_LABEL_LANGUAGE,
            "labels_changed": False,
        },
        "protocol": {
            "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "renderer": str(RENDERER.relative_to(ROOT)),
            "renderer_sha256": FROZEN[RENDERER],
            "complete_requirement_final_semantic_field": True,
            "persistent_history_replayed": True,
            "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
        },
        "state_training_contract": {
            "train_rows": 2000,
            "dev_rows": 500,
            "dev_optimizer_use": False,
            "loss_mask": "target_suffix",
            "target_prefix": TARGET_PREFIX,
            "jsonl_bos_token_id": 0,
            "ctx_len": CTX_LEN,
            "steps": 2000,
            "save_steps": [500, 1000, 1500, 2000],
            "seed": SEED,
            "parent_state": "zero",
            "physical_gpu": 0,
            **token_stats,
            "target_boundary_additive": True,
            "target_truncation_count": 0,
        },
        "holdout": {
            "tasks_path": str((LADDER / "tasks.json").relative_to(ROOT)),
            "tasks_sha256": FROZEN[LADDER / "tasks.json"],
            "acceptance_path": str((LADDER / "acceptance.json").relative_to(ROOT)),
            "acceptance_sha256": FROZEN[LADDER / "acceptance.json"],
            "optimizer_use": False,
            "candidate_selection_use": False,
            "exact_task_id_count": 0,
            "exact_workspace_path_count": 0,
            "similarity_algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold_exclusive": 0.95,
            "maximum_similarity": maximum_similarity,
        },
        "split_integrity": {
            "exact_request_overlap": 0,
            "source_family_overlap": 0,
            "split_specific_entity_and_path_lexicons": True,
        },
        "role_purity": {
            "parameter_schema_count": 0,
            "full_tool_result_count": 0,
            "executor_text_count": 0,
            "planner_text_count": 0,
            "generated_rwkv_text_count": 0,
            "hidden_acceptance_count": 0,
            "sampling_invoked": False,
            "raw_rwkv_output_modified": False,
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": FROZEN[PREREGISTRATION],
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "files": {
            "cases.jsonl": {
                "rows": len(all_rows),
                "bytes": cases_path.stat().st_size,
                "sha256": sha256_file(cases_path),
            },
            **{
                path.name: {
                    "rows": len(state_rows[split]),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for split, path in state_paths.items()
            },
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S61 transaction-continuation Selector corpus\n\n"
        "2,000 train, 500 dev, and 500 locked-test V7 prefixes. Each split is "
        "half failure-focused current trajectories and half balanced frozen S60 "
        "retention. Labels are mechanical; no RWKV text was generated.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s61_dataset_finalized",
                "counts": expected_counts,
                "focus_accuracy_target": 0.95,
                "maximum_ladder_similarity": maximum_similarity,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
