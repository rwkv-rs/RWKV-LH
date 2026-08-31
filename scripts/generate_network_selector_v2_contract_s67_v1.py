#!/usr/bin/env python3
"""Generate the frozen 2K CurrentDirectStageV2 Selector corpus S67."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from rwkv_lh.atom_execution import (
    ATOM_EXECUTION_POLICY_KEY,
    AtomExecutionBinding,
    AtomExecutionContract,
)
from rwkv_lh.capability_projection import CAPABILITY_PROJECTION_VERSION
from rwkv_lh.exact_tool_selector.compact_protocol_v7 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    compact_selector_input_digest,
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION,
    build_network_selector_input,
)
from rwkv_lh.schema import (
    ActionRecord,
    ActionStatus,
    GoalState,
    ModelCheckpoint,
    ModelLaneKind,
    RunState,
)
from rwkv_lh.supervisor import SupervisorAtom
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_SELECTOR_V2_CONTRACT_S67_20260831"
)
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_v2_contract_s67_v1"
LADDER = ROOT / "benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1"
E3_RUN = (
    ROOT
    / "data/experiments/ENGINEERING_CLOSED_LOOP_RERUN_V3_20260830"
    / "run_e3_pending_resume_full_v1"
)
RENDERER = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v7.py"
RUNTIME_PROJECTION = ROOT / "rwkv_lh/exact_tool_selector/runtime_projection.py"
CONTRACT_PROGRESS = ROOT / "rwkv_lh/atom_execution.py"

DATASET_VERSION = "rwkv-lh.network-selector-v2-contract-s67.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-v2-contract-prefix.s67.v1"
STATE_ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s67.v1"
TARGET_PREFIX = "\nSelectorLabelV7: "
CTX_LEN = 2496
SEED = 1067
SPLITS = ("train", "dev", "test")
COUNTS_PER_LABEL = {"train": 80, "dev": 20, "test": 20}
EXPECTED_COUNTS = {"train": 2000, "dev": 500, "test": 500}

FROZEN = {
    PREREGISTRATION: "47d022c9b2c7e3a1329b66fea64a777eabf46afeff602b7f2e1d9197c8085b57",
    LADDER / "tasks.json": "23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb",
    LADDER / "acceptance.json": "f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06",
    E3_RUN / "results.json": "d7400d3bc2f9699feb3dab21ca3d7a734e159d23691b17bed191e7f14dc5c632",
    RENDERER: "312e490f92fcc0d20dc8a78038291d15e298e6c8e27ae20eaff41fe7f38686f0",
    RUNTIME_PROJECTION: "9be096e7c65e5efd63fe32282ca923fed195e5bc551937b39860ada1625d7e00",
    CONTRACT_PROGRESS: "1078d5905813ba8a809ff12dc72ea7a09c0d687bcd9fe2ae951c8b4cd7f2f043",
}

LEXICONS = {
    "train": (
        "amber-arch",
        "birch-court",
        "cobalt-field",
        "dahlia-grove",
        "ember-lane",
        "fir-harbor",
        "granite-isle",
        "hazel-junction",
        "ivory-keel",
        "juniper-mesa",
        "kelp-nook",
        "lilac-orchard",
        "maple-pier",
        "nickel-quay",
        "opal-ridge",
        "pine-summit",
    ),
    "dev": (
        "quartz-terrace",
        "russet-upland",
        "silver-valley",
        "topaz-wharf",
        "umber-xylem",
        "violet-yard",
        "willow-zenith",
        "xenon-basin",
    ),
    "test": (
        "saffron-cove",
        "yarrow-delta",
        "zircon-estuary",
        "acacia-fjord",
        "bronze-glade",
        "coral-heath",
        "denim-inlet",
        "elm-knoll",
    ),
}

EN_MODIFIERS = {
    "train": ("For the bounded audit", "Within the isolated batch", "For this single responsibility"),
    "dev": ("Inside the scoped review", "For the independent work item", "Within the current evidence pass"),
    "test": ("For the contained assignment", "Inside the declared workspace scope", "For the present atom only"),
}
ZH_MODIFIERS = {
    "train": ("针对当前有界审计", "在隔离批次内", "只处理这一项职责"),
    "dev": ("在限定检查范围内", "针对独立工作项", "在当前证据阶段"),
    "test": ("针对这项封闭任务", "在声明的工作区范围内", "只处理当前原子职责"),
}

EN_PHRASES: dict[str, tuple[str, str, str]] = {
    "list_directory": (
        "enumerate bounded names, types, and sizes under {directory} without opening file contents",
        "inspect directory-entry metadata beneath {directory}, but do not read any file body",
        "obtain a bounded path/type/size listing for {directory} and nothing more",
    ),
    "search_text": (
        "locate every workspace line containing the literal marker {marker} below {directory}",
        "find bounded UTF-8 line matches for {marker} in {directory}",
        "scan workspace text under {directory} for exact occurrences of {marker}",
    ),
    "read_file": (
        "observe the exact UTF-8 contents of {text_path}",
        "read a bounded tokenizer-safe byte range from {text_path}",
        "inspect the existing text file {text_path} without modifying it",
    ),
    "read_json": (
        "parse and inspect the structured JSON value in {json_path}",
        "load the canonical JSON representation stored at {json_path}",
        "observe the existing JSON object in {json_path} without changing keys",
    ),
    "file_digest": (
        "measure the SHA-256 identity and byte size of {text_path}",
        "obtain a content digest for the existing file {text_path}",
        "verify the exact file identity of {text_path} by digest and size",
    ),
    "write_file": (
        "create or replace the complete UTF-8 source file {text_path}",
        "write the full requested text artifact to {text_path}",
        "materialize the entire non-JSON file {text_path} atomically",
    ),
    "write_json": (
        "create the complete JSON value required at {json_path}",
        "write a full structured JSON record to {json_path}",
        "atomically replace {json_path} with the entire requested JSON value",
    ),
    "patch_json": (
        "update only the named top-level status field in {json_path} while preserving every other key",
        "apply a partial top-level key update to the existing object in {json_path}",
        "change the explicit revision key inside {json_path} without replacing unspecified fields",
    ),
    "replace_text": (
        "replace one exact stale token {old_marker} with {new_marker} in {text_path}",
        "substitute the single matching text occurrence in {text_path} and preserve the rest",
        "edit {text_path} by replacing exactly one declared old fragment with the new fragment",
    ),
    "remove_line": (
        "remove the complete line equal to {old_marker} from {text_path}",
        "delete one matching UTF-8 line from {text_path} while retaining all other lines",
        "drop the explicitly named obsolete line in {text_path}",
    ),
    "append_file": (
        "append the new UTF-8 record {new_marker} to {text_path}",
        "add the requested trailing text to the existing file {text_path}",
        "extend {text_path} with one new line without replacing prior content",
    ),
    "make_directory": (
        "create the directory hierarchy {directory}",
        "ensure the workspace folder {directory} exists",
        "materialize one scoped directory at {directory}",
    ),
    "copy_file": (
        "duplicate the exact bytes of {source_path} into {dest_path}",
        "preserve {source_path} and create an identical copy at {dest_path}",
        "copy the scoped source file {source_path} to the destination {dest_path}",
    ),
    "move_file": (
        "rename or move {source_path} to {dest_path}",
        "relocate the existing scoped file {source_path} into {dest_path}",
        "transfer {source_path} to the new path {dest_path} without keeping the old path",
    ),
    "delete_file": (
        "remove the explicitly scoped obsolete path {text_path}",
        "delete the declared workspace file {text_path}",
        "erase only the named stale artifact {text_path}",
    ),
    "bind_evidence": (
        "retain the exact supporting line span in {text_path} with its locator and quote",
        "bind a cited workspace excerpt from {text_path} as durable evidence",
        "capture the precise source lines in {text_path} together with their location",
    ),
    "check_command": (
        "run the fixed read-only validator argv python {check_path} and record its exit status",
        "execute the non-mutating test command python {check_path} as the verification step",
        "inspect correctness by running the declared read-only checker python {check_path}",
    ),
    "run_command": (
        "execute the declared local build argv python {script_path} that may update generated artifacts",
        "run the scoped potentially mutating command python {script_path}",
        "invoke the local generation program python {script_path} with shell expansion disabled",
    ),
    "web_search": (
        "discover current public web evidence for the query {query}",
        "search public sources for up-to-date information about {query}",
        "find and fetch public pages relevant to {query}",
    ),
    "connector_lookup": (
        "query the structured public repository source for {repository}",
        "look up the exact package record {package} from its public registry",
        "retrieve one structured scholarly or repository record for {repository}",
    ),
    "calculator": (
        "evaluate the complete arithmetic expression {expression}",
        "compute the known numeric formula {expression} without outside lookup",
        "calculate the exact result of {expression}",
    ),
    "date_diff": (
        "calculate the absolute calendar-day distance between {date_a} and {date_b}",
        "measure how many calendar days separate {date_a} from {date_b}",
        "obtain the day difference for the two known ISO dates {date_a} and {date_b}",
    ),
    "current_time": (
        "observe the current clock reading for timezone {timezone}",
        "obtain the present time in the IANA zone {timezone}",
        "report the live wall-clock value for {timezone}",
    ),
    "final_answer": (
        "all required evidence is complete, so provide the concise user-facing result with no further operation",
        "the contract is fully satisfied; return the grounded final response now",
        "no tool call remains necessary after the completed work, so finish with the answer",
    ),
    "ABSTAIN": (
        "the responsibility requires an unavailable private account and none of the described operations can perform it; select no operation",
        "the stage is unsupported and lacks enough observable information to choose any listed operation safely",
        "no described operation applies to this inaccessible private-system responsibility, so abstain",
    ),
}

ZH_PHRASES: dict[str, tuple[str, str, str]] = {
    "list_directory": ("只枚举 {directory} 下有界的名称、类型和大小，不打开文件正文", "检查 {directory} 下的目录项元数据，但不要读取文件内容", "仅取得 {directory} 的路径、类型和大小清单"),
    "search_text": ("在 {directory} 下定位包含字面标记 {marker} 的工作区文本行", "查找 {directory} 中与 {marker} 匹配的有界 UTF-8 行", "扫描 {directory} 下的文本并找出 {marker} 的精确出现位置"),
    "read_file": ("观察 {text_path} 的精确 UTF-8 内容", "读取 {text_path} 中受 tokenizer 约束的字节范围", "只检查现有文本文件 {text_path}，不要修改"),
    "read_json": ("解析并检查 {json_path} 中的结构化 JSON 值", "读取 {json_path} 保存的规范 JSON 表示", "观察 {json_path} 的现有 JSON 对象且不改动键"),
    "file_digest": ("取得 {text_path} 的 SHA-256 标识和字节大小", "计算现有文件 {text_path} 的内容摘要", "通过摘要和大小核验 {text_path} 的精确文件身份"),
    "write_file": ("完整创建或替换 UTF-8 源文件 {text_path}", "把完整文本产物写入 {text_path}", "原子化生成整个非 JSON 文件 {text_path}"),
    "write_json": ("在 {json_path} 创建完整 JSON 值", "把完整结构化 JSON 记录写入 {json_path}", "用全部请求的 JSON 值原子替换 {json_path}"),
    "patch_json": ("只更新 {json_path} 的顶层 status 字段并保留其他键", "对 {json_path} 的现有对象应用局部顶层键更新", "修改 {json_path} 中明确的 revision 键且不替换未指定字段"),
    "replace_text": ("在 {text_path} 中把唯一旧标记 {old_marker} 替换为 {new_marker}", "只替换 {text_path} 中一个匹配文本并保留其余内容", "在 {text_path} 中精确替换声明的旧片段"),
    "remove_line": ("从 {text_path} 删除完整等于 {old_marker} 的一行", "删除 {text_path} 中一条匹配的 UTF-8 行并保留其他行", "移除 {text_path} 中明确指定的过期行"),
    "append_file": ("把新的 UTF-8 记录 {new_marker} 追加到 {text_path}", "在现有文件 {text_path} 末尾加入请求文本", "给 {text_path} 增加一行且不替换已有内容"),
    "make_directory": ("创建目录层级 {directory}", "确保工作区文件夹 {directory} 存在", "在 {directory} 生成一个限定范围的目录"),
    "copy_file": ("把 {source_path} 的精确字节复制到 {dest_path}", "保留 {source_path} 并在 {dest_path} 创建相同副本", "将限定源文件 {source_path} 复制到 {dest_path}"),
    "move_file": ("把 {source_path} 移动或重命名为 {dest_path}", "将现有文件 {source_path} 迁移到 {dest_path}", "把 {source_path} 转移到新路径 {dest_path} 且不保留旧路径"),
    "delete_file": ("移除明确限定的过期路径 {text_path}", "删除声明的工作区文件 {text_path}", "只清除命名的陈旧产物 {text_path}"),
    "bind_evidence": ("保留 {text_path} 中精确的支持行范围、定位和引文", "把 {text_path} 的工作区摘录绑定为可持久证据", "捕获 {text_path} 的准确来源行及其位置"),
    "check_command": ("运行固定的只读校验 argv：python {check_path}，并记录退出状态", "执行非变更测试命令 python {check_path} 作为验证步骤", "运行声明的只读检查器 python {check_path} 来核验正确性"),
    "run_command": ("执行可能更新生成产物的本地构建 argv：python {script_path}", "运行限定范围、可能产生变更的命令 python {script_path}", "在禁用 shell 展开的情况下调用本地生成程序 python {script_path}"),
    "web_search": ("为查询 {query} 发现当前公开网络证据", "在公开来源中检索 {query} 的最新信息", "查找并获取与 {query} 有关的公开页面"),
    "connector_lookup": ("从结构化公开仓库源查询 {repository}", "从公开注册表精确查询包记录 {package}", "为 {repository} 取得一条结构化学术或仓库记录"),
    "calculator": ("计算完整算术表达式 {expression}", "在不外部检索的情况下求已知公式 {expression}", "得到表达式 {expression} 的精确结果"),
    "date_diff": ("计算 {date_a} 与 {date_b} 之间的绝对日历日距离", "求 {date_a} 和 {date_b} 相隔多少个日历日", "取得两个已知 ISO 日期 {date_a} 与 {date_b} 的日差"),
    "current_time": ("观察时区 {timezone} 的当前时钟", "取得 IANA 时区 {timezone} 的现在时间", "报告 {timezone} 的实时墙上时钟值"),
    "final_answer": ("全部所需证据已经完成，不再调用工具，直接给出简洁的面向用户结果", "合同义务已经全部满足，现在返回有依据的最终答复", "已完成工作且不再需要操作，以最终答案结束"),
    "ABSTAIN": ("该职责需要不可用的私有账户，任何已描述操作都不能完成，因此不选择操作", "当前阶段不受支持且缺少安全选择任一工具所需的可观察信息", "没有已描述操作适用于不可访问的私有系统职责，因此弃权"),
}

LOCAL_READ_OPERATIONS = (
    "list_directory",
    "search_text",
    "read_file",
    "read_json",
    "file_digest",
    "bind_evidence",
    "calculator",
    "date_diff",
    "current_time",
)
PUBLIC_READ_OPERATIONS = (*LOCAL_READ_OPERATIONS, "web_search", "connector_lookup")
PROCESS_READ_OPERATIONS = (*PUBLIC_READ_OPERATIONS, "check_command")
PATH_MUTATIONS = (
    "write_file",
    "write_json",
    "patch_json",
    "replace_text",
    "remove_line",
    "append_file",
    "make_directory",
    "copy_file",
    "move_file",
    "delete_file",
)
WORKSPACE_MUTATION_OPERATIONS = (*LOCAL_READ_OPERATIONS, *PATH_MUTATIONS)
PROCESS_MUTATION_OPERATIONS = (*PROCESS_READ_OPERATIONS, *PATH_MUTATIONS, "run_command")


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
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_row(row) + "\n")


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


def walk_paths(value: Any, result: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"path", "source", "destination"} and isinstance(item, str):
                if item not in {"", "."}:
                    result.add(item)
            if key in {"files", "read_roots", "write_roots"} and isinstance(item, list):
                result.update(str(path) for path in item if isinstance(path, str) and path not in {"", "."})
            walk_paths(item, result)
    elif isinstance(value, list):
        for item in value:
            walk_paths(item, result)


def holdout_contract() -> tuple[list[tuple[str, str]], set[str], set[str], dict[str, str]]:
    tasks_path = LADDER / "tasks.json"
    acceptance_path = LADDER / "acceptance.json"
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    references = [(str(item["task_id"]), str(item["user_request"])) for item in tasks["tasks"]]
    forbidden_paths: set[str] = set()
    walk_paths(tasks, forbidden_paths)
    walk_paths(acceptance, forbidden_paths)
    task_ids = {str(item["task_id"]) for item in tasks["tasks"]}
    audit_hashes: dict[str, str] = {}
    results = json.loads((E3_RUN / "results.json").read_text(encoding="utf-8"))
    for row in results.get("results") or ():
        task_id = str(row.get("task_id") or "")
        task_ids.add(task_id)
        audit_path = E3_RUN / str(row.get("audit") or "")
        audit_hashes[str(audit_path.relative_to(ROOT))] = sha256_file(audit_path)
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        request = str(audit.get("user_request") or "")
        if request:
            references.append((f"E3:{task_id}:request", request))
        for event in audit.get("events") or ():
            if event.get("type") != "contract_graph_patch_committed":
                continue
            patch = (event.get("data") or {}).get("patch") or {}
            for node in patch.get("new_nodes") or ():
                raw_atom = node.get("atom") if isinstance(node, Mapping) else None
                if not isinstance(raw_atom, Mapping):
                    continue
                atom_id = str(raw_atom.get("atom_id") or "")
                objective = str(raw_atom.get("objective") or "")
                if objective:
                    references.append((f"E3:{task_id}:{atom_id}", objective))
                walk_paths(raw_atom, forbidden_paths)
    unique: dict[str, str] = {}
    for identity, text in references:
        if text and text not in unique:
            unique[text] = identity
    return [(identity, text) for text, identity in unique.items()], forbidden_paths, task_ids, audit_hashes


def operation_arguments(label: str, context: Mapping[str, str]) -> dict[str, Any]:
    mapping: dict[str, dict[str, Any]] = {
        "list_directory": {"path": context["directory"]},
        "search_text": {"path": context["directory"], "query": context["marker"]},
        "read_file": {"path": context["text_path"]},
        "read_json": {"path": context["json_path"]},
        "file_digest": {"path": context["text_path"]},
        "write_file": {"path": context["text_path"], "content": "complete"},
        "write_json": {"path": context["json_path"], "value": {"status": "complete"}},
        "patch_json": {"path": context["json_path"], "patch": {"status": "complete"}},
        "replace_text": {"path": context["text_path"], "old": context["old_marker"], "new": context["new_marker"]},
        "remove_line": {"path": context["text_path"], "line": context["old_marker"]},
        "append_file": {"path": context["text_path"], "content": context["new_marker"]},
        "make_directory": {"path": context["directory"]},
        "copy_file": {"source": context["source_path"], "destination": context["dest_path"]},
        "move_file": {"source": context["source_path"], "destination": context["dest_path"]},
        "delete_file": {"path": context["text_path"]},
        "bind_evidence": {"path": context["text_path"], "start_line": 1, "end_line": 2},
        "check_command": {"argv": ["python", context["check_path"]]},
        "run_command": {"argv": ["python", context["script_path"]]},
        "web_search": {"query": context["query"]},
        "connector_lookup": {"operation": "repository", "query": context["repository"]},
        "calculator": {"expression": context["expression"]},
        "date_diff": {"start": context["date_a"], "end": context["date_b"]},
        "current_time": {"timezone": context["timezone"]},
    }
    return dict(mapping.get(label, {}))


def action_record(
    *,
    sequence: int,
    operation: str,
    arguments: Mapping[str, Any],
    contract_digest: str,
    success: bool,
) -> ActionRecord:
    identity = f"S67-A{sequence}-{stable_hex(operation, arguments, success)[:12]}"
    return ActionRecord(
        action_id=identity,
        sequence=sequence,
        status=ActionStatus.SUCCEEDED if success else ActionStatus.FAILED,
        action_type=operation,
        arguments=dict(arguments),
        wire_arguments=dict(arguments),
        action_fingerprint=stable_hex("fingerprint", identity),
        idempotency_key=stable_hex("idempotency", identity),
        decision_id=f"D-{identity}",
        request_id=f"R-{identity}",
        started_at="2026-08-31T00:00:00+00:00",
        ended_at="2026-08-31T00:00:01+00:00",
        result={
            "success": success,
            "outcome_type": "success" if success else "error",
            "metadata": {"complete": success, "truncated": False},
        },
        outcome_type="success" if success else "error",
        atom_execution_contract_digest=contract_digest,
    )


def dummy_parent(action_index: int) -> ModelCheckpoint | None:
    if action_index <= 0:
        return None
    return ModelCheckpoint(
        checkpoint_id=f"S67-PARENT-{action_index}",
        lane_id="selector",
        lane_kind=ModelLaneKind.SELECTOR,
        parent_checkpoint_id=None,
        model="rwkv7-g1i-2.9b-vllm-v1",
        transport="native_state",
        transcript="",
        transcript_digest="0" * 64,
        token_count=0,
        native_state_metadata={"action_index": action_index},
    )


def context_for(split: str, label: str, index: int) -> dict[str, str]:
    token = stable_hex("S67", split, label, index)[:14]
    roots = LEXICONS[split]
    root = roots[(index + NETWORK_EXACT_TOOL_LABELS.index(label) * 3) % len(roots)]
    base = f"scopes/{root}/{token}"
    return {
        "token": token,
        "root": root,
        "text_path": base + (".py" if index % 2 == 0 else ".md"),
        "json_path": base + ".json",
        "directory": base + "-bundle",
        "source_path": f"inputs/{root}/{token}-source.txt",
        "dest_path": f"outputs/{root}/{token}-copy.txt",
        "check_path": f"checks/{root}/{token}-verify.py",
        "script_path": f"build/{root}/{token}-generate.py",
        "marker": f"marker-{token[:8]}",
        "old_marker": f"old-{token[:8]}",
        "new_marker": f"new-{token[:8]}",
        "query": f"public release evidence {root} {token[:8]}",
        "repository": f"{root}/{token[:8]}-repository",
        "package": f"{root}-{token[:8]}-package",
        "expression": f"({index + 17} * 3) + {NETWORK_EXACT_TOOL_LABELS.index(label) + 5}",
        "date_a": f"2025-{(index % 9) + 1:02d}-{(index % 18) + 1:02d}",
        "date_b": f"2026-{((index + 3) % 9) + 1:02d}-{((index + 5) % 18) + 1:02d}",
        "timezone": ("Asia/Shanghai" if index % 2 == 0 else "Europe/Amsterdam"),
    }


def request_for(split: str, label: str, index: int, language: str, context: Mapping[str, str]) -> str:
    split_index = SPLITS.index(split)
    phrase = (EN_PHRASES if language == "en" else ZH_PHRASES)[label][split_index]
    modifier_pool = EN_MODIFIERS[split] if language == "en" else ZH_MODIFIERS[split]
    modifier = modifier_pool[(index + NETWORK_EXACT_TOOL_LABELS.index(label)) % len(modifier_pool)]
    core = phrase.format(**context)
    if language == "en":
        return f"{modifier}, {core}. Batch reference {context['token']}; do only this atom responsibility."
    return f"{modifier}，{core}。批次标识 {context['token']}；只完成这一原子职责。"


def contract_shape(label: str, index: int, context: Mapping[str, str]) -> dict[str, Any]:
    if label in PATH_MUTATIONS:
        root = context["directory"] if label == "make_directory" else context["dest_path"] if label in {"copy_file", "move_file"} else context["json_path"] if label in {"write_json", "patch_json"} else context["text_path"]
        return {
            "role": "work",
            "atom_kind": "mutate",
            "effect_ceiling": "workspace_mutation",
            "allowed_operations": WORKSPACE_MUTATION_OPERATIONS,
            "write_roots": (root,),
            "evidence_kinds": ("workspace_file",),
            "freshness": "current_workspace",
            "source_preferences": ("workspace",),
        }
    if label == "run_command":
        return {
            "role": "work",
            "atom_kind": "mutate",
            "effect_ceiling": "local_process_mutation",
            "allowed_operations": PROCESS_MUTATION_OPERATIONS,
            "write_roots": (),
            "evidence_kinds": ("process_result",),
            "freshness": "current_at_run_time",
            "source_preferences": ("local_process",),
        }
    if label == "check_command":
        return {
            "role": "work",
            "atom_kind": "verify",
            "effect_ceiling": "local_process_read_only",
            "allowed_operations": PROCESS_READ_OPERATIONS,
            "write_roots": (),
            "evidence_kinds": ("process_result",),
            "freshness": "current_workspace",
            "source_preferences": ("local_process",),
        }
    if label in {"web_search", "connector_lookup"}:
        return {
            "role": "work",
            "atom_kind": "investigate",
            "effect_ceiling": "public_read_only",
            "allowed_operations": PUBLIC_READ_OPERATIONS,
            "write_roots": (),
            "evidence_kinds": (("public_web",) if label == "web_search" else ("structured_registry",)),
            "freshness": "current_at_run_time",
            "source_preferences": (("public_web",) if label == "web_search" else ("structured_source",)),
        }
    if label == "final_answer":
        variant = index % 3
        if variant == 0:
            return {
                "role": "work",
                "atom_kind": "mutate",
                "effect_ceiling": "workspace_mutation",
                "allowed_operations": WORKSPACE_MUTATION_OPERATIONS,
                "write_roots": (context["text_path"],),
                "evidence_kinds": ("workspace_file",),
                "freshness": "current_workspace",
                "source_preferences": ("workspace",),
            }
        if variant == 1:
            return {
                "role": "work",
                "atom_kind": "investigate",
                "effect_ceiling": "local_read_only",
                "allowed_operations": LOCAL_READ_OPERATIONS,
                "write_roots": (),
                "evidence_kinds": ("workspace_file",),
                "freshness": "current_workspace",
                "source_preferences": ("workspace",),
            }
        return {
            "role": "finalizer",
            "atom_kind": "synthesize",
            "effect_ceiling": "local_read_only",
            "allowed_operations": LOCAL_READ_OPERATIONS,
            "write_roots": (),
            "evidence_kinds": ("workspace_file",),
            "freshness": "current_workspace",
            "source_preferences": ("workspace",),
        }
    return {
        "role": "work",
        "atom_kind": "verify" if label in {"file_digest", "bind_evidence"} else "investigate",
        "effect_ceiling": "local_read_only",
        "allowed_operations": LOCAL_READ_OPERATIONS,
        "write_roots": (),
        "evidence_kinds": (("deterministic_compute",) if label in {"calculator", "date_diff", "current_time"} else ("workspace_file",)),
        "freshness": "current_at_run_time" if label == "current_time" else "current_workspace",
        "source_preferences": (("deterministic",) if label in {"calculator", "date_diff", "current_time"} else ("workspace",)),
    }


def prior_actions_for(
    label: str,
    index: int,
    context: Mapping[str, str],
    contract: AtomExecutionContract,
) -> tuple[list[ActionRecord], int]:
    if label == "final_answer":
        if contract.atom_kind == "mutate":
            operation = "write_file"
            arguments = {"path": context["text_path"], "content": "complete"}
        else:
            operation = "read_file"
            arguments = {"path": context["text_path"]}
        return [
            action_record(
                sequence=1,
                operation=operation,
                arguments=arguments,
                contract_digest=contract.contract_digest,
                success=True,
            )
        ], 0
    if label == "ABSTAIN":
        return [], index % 2
    variant = index % 4
    if variant in {0, 3}:
        return [], int(variant == 3)
    if variant == 2 and contract.atom_kind == "mutate" and contract.atom.write_roots:
        operation = "list_directory"
        arguments = {"path": "."}
        success = True
    else:
        operation = label
        arguments = operation_arguments(label, context)
        success = False
    return [
        action_record(
            sequence=1,
            operation=operation,
            arguments=arguments,
            contract_digest=contract.contract_digest,
            success=success,
        )
    ], 0


def input_at(
    *,
    request: str,
    binding: AtomExecutionBinding,
    actions: Sequence[ActionRecord],
    protocol_rejections: int,
    parent_action_index: int,
    run_id: str,
):
    goal = GoalState.create(
        request=request,
        constraints=(),
        workspace_root=ROOT / "temp/s67-virtual-workspace",
        goal_id=f"G-{run_id}",
        runtime_policy={ATOM_EXECUTION_POLICY_KEY: binding.to_dict()},
    )
    state = RunState(run_id=run_id, goal=goal, protocol_rejections=protocol_rejections)
    state.actions = {action.action_id: action for action in actions}
    return build_network_selector_input(state, dummy_parent(parent_action_index))


def build_row(split: str, label: str, index: int) -> dict[str, Any]:
    language = "en" if index % 2 == 0 else "zh"
    context = context_for(split, label, index)
    request = request_for(split, label, index, language, context)
    shape = contract_shape(label, index, context)
    atom_id = f"S67-{split}-{NETWORK_EXACT_TOOL_LABELS.index(label):02d}-{index:03d}"
    atom = SupervisorAtom.create(
        immutable_request=request,
        atom_id=atom_id,
        objective=request,
        request_clauses=(request,),
        role=shape["role"],
        atom_kind=shape["atom_kind"],
        effect_ceiling=shape["effect_ceiling"],
        allowed_operations=shape["allowed_operations"],
        action_budget=4,
        minimum_actions=1,
        write_roots=shape["write_roots"],
        completion_checks=("The single declared responsibility is complete and grounded.",),
        evidence_kinds=shape["evidence_kinds"],
        freshness=shape["freshness"],
        source_preferences=shape["source_preferences"],
        operation_allowset_source=CAPABILITY_PROJECTION_VERSION,
    )
    contract = AtomExecutionContract.create(immutable_request=request, atom=atom)
    binding = AtomExecutionBinding(contract=contract)
    actions, protocol_rejections = prior_actions_for(label, index, context, contract)
    prior_inputs = []
    for position in range(len(actions)):
        prior_inputs.append(
            input_at(
                request=request,
                binding=binding,
                actions=actions[:position],
                protocol_rejections=0,
                parent_action_index=max(0, position - 1),
                run_id=f"{atom_id}-P{position}",
            )
        )
    current = input_at(
        request=request,
        binding=binding,
        actions=actions,
        protocol_rejections=protocol_rejections,
        parent_action_index=max(0, len(actions) - 1),
        run_id=f"{atom_id}-CURRENT",
    )
    if not current.stage_objective.startswith("CurrentDirectStageV2: "):
        raise RuntimeError("S67 did not use CurrentDirectStageV2")
    embedded = json.loads(current.stage_objective.removeprefix("CurrentDirectStageV2: "))
    completion_ready = bool((embedded.get("progress") or {}).get("completion_ready"))
    if completion_ready != (label == "final_answer"):
        raise RuntimeError(f"S67 completion/label mismatch: {atom_id}/{label}")
    bootstrap = render_compact_selector_bootstrap(current)
    prior_steps = [render_compact_selector_step(value) for value in prior_inputs]
    step = render_compact_selector_step(current)
    rendered = bootstrap + "".join("\n" + value for value in [*prior_steps, step])
    expected_tail = json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "}}"
    if not rendered.endswith(expected_tail):
        raise RuntimeError("S67 requirement is not the literal byte tail")
    token = stable_hex("S67-row", split, label, index)[:24]
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": DATASET_VERSION,
        "sample_id": f"S67-{split.upper()}-{token}",
        "trajectory_id": f"S67-TRAJECTORY-{token}",
        "trajectory_position": len(prior_steps),
        "split": split,
        "cohort": "v2_contract",
        "scenario": label,
        "source_family_id": f"s67:{split}:{label}:{context['root']}:{token}",
        "language": language,
        "label": label,
        "task_request": request,
        "stage_objective": current.stage_objective,
        "stage_role": current.stage_role,
        "progress": current.progress.to_dict(),
        "contract_progress": embedded,
        "selector_input_sha256": compact_selector_input_digest(current),
        "bootstrap": bootstrap,
        "prior_steps": prior_steps,
        "step": step,
        "rendered_input": rendered,
        "rendered_input_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "compact_menu_digest": compact_selector_menu_digest(),
        "projection_version": SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION,
        "complete_requirement_byte_tail": True,
        "current_requirement_is_atom_objective": True,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
        "contains_planner_raw_json": False,
        "generated_rwkv_text": False,
        "hidden_acceptance_used": False,
        "label_generation": "preregistered_semantic_scenario_plus_canonical_contract_progress",
    }


def state_rows(
    tokenizer: RWKVTokenizer,
    rows_by_split: Mapping[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    output: dict[str, list[dict[str, Any]]] = {"train": [], "dev": []}
    minimum_prompt = 10**9
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
                raise RuntimeError(f"S67 target boundary is not additive: {row['sample_id']}")
            if 1 + len(text_tokens) > CTX_LEN + 1:
                raise RuntimeError(f"S67 target would be truncated: {row['sample_id']}")
            minimum_prompt = min(minimum_prompt, 1 + len(prompt_tokens))
            maximum_prompt = max(maximum_prompt, 1 + len(prompt_tokens))
            maximum_text = max(maximum_text, 1 + len(text_tokens))
            output[split].append(
                {
                    "schema_version": STATE_ROW_SCHEMA,
                    "dataset_version": DATASET_VERSION,
                    "sample_id": f"S67-STATE-{split.upper()}-{index:04d}",
                    "source_sample_id": row["sample_id"],
                    "source_family_id": row["source_family_id"],
                    "split": split,
                    "cohort": row["cohort"],
                    "scenario": row["scenario"],
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
    return output, {
        "minimum_prompt_tokens_including_bos": minimum_prompt,
        "maximum_prompt_tokens_including_bos": maximum_prompt,
        "maximum_text_tokens_including_bos": maximum_text,
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S67 dataset")
    for path, expected in FROZEN.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S67 frozen input changed: {path}: {actual}")
    if set(EN_PHRASES) != set(NETWORK_EXACT_TOOL_LABELS) or set(ZH_PHRASES) != set(NETWORK_EXACT_TOOL_LABELS):
        raise RuntimeError("S67 phrase inventory differs from 25-class protocol")
    lexicon_sets = {split: set(values) for split, values in LEXICONS.items()}
    for left_index, left in enumerate(SPLITS):
        for right in SPLITS[left_index + 1 :]:
            if lexicon_sets[left] & lexicon_sets[right]:
                raise RuntimeError(f"S67 lexicon overlap: {left}/{right}")

    references, forbidden_paths, task_ids, audit_hashes = holdout_contract()
    rows_by_split = {
        split: [
            build_row(split, label, index)
            for label in NETWORK_EXACT_TOOL_LABELS
            for index in range(COUNTS_PER_LABEL[split])
        ]
        for split in SPLITS
    }
    if {split: len(rows) for split, rows in rows_by_split.items()} != EXPECTED_COUNTS:
        raise RuntimeError("S67 split counts changed")
    for split, rows in rows_by_split.items():
        expected_labels = Counter({label: COUNTS_PER_LABEL[split] for label in NETWORK_EXACT_TOOL_LABELS})
        if Counter(str(row["label"]) for row in rows) != expected_labels:
            raise RuntimeError(f"S67 label balance changed: {split}")
        if Counter(str(row["language"]) for row in rows) != Counter({"en": len(rows) // 2, "zh": len(rows) // 2}):
            raise RuntimeError(f"S67 language balance changed: {split}")

    all_rows = [row for split in SPLITS for row in rows_by_split[split]]
    if len({str(row["sample_id"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S67 sample IDs are not unique")
    if len({str(row["rendered_input_sha256"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S67 rendered prompts are not unique")
    purity_fields = (
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "contains_planner_raw_json",
        "generated_rwkv_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in all_rows for field in purity_fields):
        raise RuntimeError("S67 role purity changed")
    forbidden_literals = {value for value in forbidden_paths | task_ids if len(value) >= 6}
    for row in all_rows:
        request = str(row["task_request"])
        matches = [value for value in forbidden_literals if value in request]
        if matches:
            raise RuntimeError(f"S67 row contains holdout literal: {row['sample_id']}:{matches[:3]}")
    for left_index, left in enumerate(SPLITS):
        for right in SPLITS[left_index + 1 :]:
            for key in ("task_request", "source_family_id", "rendered_input_sha256"):
                left_values = {str(row[key]) for row in rows_by_split[left]}
                right_values = {str(row[key]) for row in rows_by_split[right]}
                if left_values & right_values:
                    raise RuntimeError(f"S67 {key} overlap: {left}/{right}")

    reference_grams = [(identity, byte_ngrams(text)) for identity, text in references]
    maximum_similarity: dict[str, Any] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in all_rows:
        grams = byte_ngrams(str(row["task_request"]))
        for identity, reference in reference_grams:
            score = cosine(grams, reference)
            if score > float(maximum_similarity["score"]):
                maximum_similarity = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": identity,
                }
    if float(maximum_similarity["score"]) >= 0.95:
        raise RuntimeError(f"S67 holdout similarity gate failed: {maximum_similarity}")

    tokenizer = RWKVTokenizer()
    exported_state_rows, token_stats = state_rows(tokenizer, rows_by_split)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, all_rows)
    state_paths = {
        split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in ("train", "dev")
    }
    for split, path in state_paths.items():
        write_jsonl(path, exported_state_rows[split])
    manifest = {
        "schema_version": "rwkv-lh.network-selector-v2-contract-manifest.s67.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "exact CurrentDirectStageV2 operation selection with 25-class retention",
        "counts": EXPECTED_COUNTS,
        "label_counts": {
            split: dict(sorted(Counter(str(row["label"]) for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "language_counts": {
            split: dict(sorted(Counter(str(row["language"]) for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "protocol": {
            "compact_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "contract_projection_version": SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION,
            "renderer": str(RENDERER.relative_to(ROOT)),
            "renderer_sha256": FROZEN[RENDERER],
            "runtime_projection": str(RUNTIME_PROJECTION.relative_to(ROOT)),
            "runtime_projection_sha256": FROZEN[RUNTIME_PROJECTION],
            "contract_progress": str(CONTRACT_PROGRESS.relative_to(ROOT)),
            "contract_progress_sha256": FROZEN[CONTRACT_PROGRESS],
            "canonical_runtime_construction": True,
            "literal_requirement_byte_tail": True,
            "persistent_history_replayed": True,
        },
        "state_training_contract": {
            "train_rows": len(exported_state_rows["train"]),
            "dev_rows": len(exported_state_rows["dev"]),
            "dev_optimizer_use": False,
            "loss_mask": "target_suffix",
            "target_prefix": TARGET_PREFIX,
            "jsonl_bos_token_id": 0,
            "ctx_len": CTX_LEN,
            "seed": SEED,
            "physical_gpu": 0,
            **token_stats,
            "target_boundary_additive": True,
            "target_truncation_count": 0,
        },
        "holdout": {
            "ladder_tasks_sha256": FROZEN[LADDER / "tasks.json"],
            "ladder_acceptance_sha256": FROZEN[LADDER / "acceptance.json"],
            "e3_results_sha256": FROZEN[E3_RUN / "results.json"],
            "e3_audit_sha256": dict(sorted(audit_hashes.items())),
            "reference_count": len(references),
            "similarity_algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold_exclusive": 0.95,
            "maximum_similarity": maximum_similarity,
            "optimizer_use": False,
            "candidate_selection_use": False,
        },
        "split_integrity": {
            "lexicon_pool_intersection_count": 0,
            "exact_request_overlap": 0,
            "source_family_overlap": 0,
            "rendered_input_overlap": 0,
        },
        "role_purity": {
            "parameter_schema_count": 0,
            "full_tool_result_count": 0,
            "executor_text_count": 0,
            "planner_raw_json_count": 0,
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
                    "rows": len(exported_state_rows[split]),
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
        "# S67 CurrentDirectStageV2 Selector corpus\n\n"
        "2,000 train, 500 dev, and 500 locked-test prefixes across all 25 labels. "
        "Rows are built through the current canonical atom contract/progress code; "
        "no model text, Executor arguments, or hidden acceptance data is present.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s67_dataset_finalized",
                "counts": EXPECTED_COUNTS,
                "maximum_holdout_similarity": maximum_similarity,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
