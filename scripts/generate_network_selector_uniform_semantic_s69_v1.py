#!/usr/bin/env python3
"""Generate the preregistered all-label S69 semantic Selector corpus."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_SELECTOR_UNIFORM_SEMANTIC_S69_V1_20260831"
)
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
BASE_GENERATOR = ROOT / "scripts/generate_network_selector_v2_contract_s67_v1.py"
S68 = ROOT / "data/datasets/rwkv_lh_network_selector_semantic_boundary_s68_v1"
S65 = ROOT / "data/datasets/rwkv_lh_network_selector_lexicon_diverse_s65_v1"
S68_LOCKED_RESULT = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_SEMANTIC_BOUNDARY_S68_V1_20260831"
    / "run_locked_test/RESULT.json"
)
S66_LOCKED_RESULT = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_DIVERSE_SOFT_MOE_S66_20260830"
    / "run_s66_m1_locked_tests/LOCKED_TEST_RESULT.json"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_uniform_semantic_s69_v1"

PREREGISTRATION_SHA256 = (
    "5a0547e4766ce61bd7a26b622518c05fe77e7976fa837307040913540d10391b"
)
BASE_GENERATOR_SHA256 = (
    "ed3d929824ffdc6fff7ad0af1466fa09f1ac5580ec3d91d92a5abb7583c65987"
)
S68_CASES_SHA256 = (
    "8b0f1a17f25863f448858d082c7b6cf7dec5cb76414f635f5f2ab8416566d218"
)
S68_MANIFEST_SHA256 = (
    "4a6e201e3d1dc6dff63f72660a08455ae619c1186b45c95c7f9d86ffc985ea0c"
)
S65_CASES_SHA256 = (
    "28cbec6cce980e1835ff04529a6b6f555557e3514f8c9f259b65ee6478a23830"
)
S65_MANIFEST_SHA256 = (
    "dc1c166dbad6f5283a6cfc4571b6e17ca107d329b12456d330e18eabfa4bd582"
)
S68_LOCKED_RESULT_SHA256 = (
    "b3e33b98e9ba7d5d9742fbb805331ae273142e94124e6dd1770f2ee0a6904c0a"
)
S66_LOCKED_RESULT_SHA256 = (
    "5d24d7abedaa54d0cb586e5500a39ffb8a62f918f1fbb7bd3e418b78f153ed0d"
)

DATASET_VERSION = "rwkv-lh.network-selector-uniform-semantic-s69.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-uniform-semantic-prefix.s69.v1"
STATE_ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s69.v1"
SPLIT_PATTERN = re.compile(r'"split":"(train|dev|test)"')
SOURCE_COUNTS = {
    "train": {"s68": 40, "s65": 40},
    "dev": {"s68": 10, "s65": 10},
    "test": {"s69-definition": 20},
}

TEST_ROOTS = (
    "aurora-bridge",
    "basalt-canyon",
    "cedar-district",
    "driftwood-esplanade",
    "equinox-farm",
    "frost-garden",
    "galena-heights",
    "hemlock-island",
)
TEST_EN_MODIFIERS = (
    "For this bounded next step",
    "Within the declared local scope",
    "For the current operation only",
    "Inside this isolated responsibility",
    "At this exact stage of the task",
)
TEST_ZH_MODIFIERS = (
    "针对当前有界步骤",
    "在声明的本地范围内",
    "只处理当前这一项操作",
    "在这项隔离职责中",
    "处于任务的这个准确阶段",
)

TEST_EN: dict[str, tuple[str, str]] = {
    "list_directory": (
        "collect only child names, entry kinds, and byte sizes below {directory}, without opening any file body",
        "return bounded directory metadata for {directory}; no contents from the listed files may be read",
    ),
    "search_text": (
        "look through local UTF-8 text under {directory} and report lines matching {marker}, without using the public internet",
        "find the exact workspace occurrences of {marker} beneath {directory} and preserve their line locations",
    ),
    "read_file": (
        "open a bounded byte range from the ordinary text file {text_path} without changing it",
        "observe the UTF-8 body stored in {text_path}; it is not a JSON document and must remain untouched",
    ),
    "read_json": (
        "decode the structured JSON document at {json_path} and inspect its canonical value without editing keys",
        "load the existing object or array from {json_path} as JSON rather than as unstructured text",
    ),
    "file_digest": (
        "identify {text_path} by SHA-256 and byte length without reading its body or changing the file",
        "measure only the content hash and size metadata of {text_path}",
    ),
    "write_file": (
        "set every byte of the complete non-JSON UTF-8 artifact at {text_path}, replacing an old body if present",
        "materialize {text_path} as one whole text file, not as JSON, an append, or a fragment edit",
    ),
    "write_json": (
        "serialize one complete structured JSON value into {json_path}, replacing the prior document as a whole",
        "create {json_path} from the full requested object or array rather than patching selected keys",
    ),
    "patch_json": (
        "merge only the named top-level fields into the existing JSON at {json_path} and retain every unspecified key",
        "apply a partial key update to {json_path}; do not replace the complete JSON document",
    ),
    "replace_text": (
        "perform one literal substitution from {old_marker} to {new_marker} inside {text_path} while preserving all surrounding bytes",
        "edit only a single exact matching span in {text_path}, changing it to {new_marker}",
    ),
    "remove_line": (
        "excise exactly one whole line equal to {old_marker} from {text_path}, leaving the file and every other line in place",
        "drop the specified complete UTF-8 line from {text_path}; do not delete the path itself",
    ),
    "append_file": (
        "preserve all existing bytes in {text_path} and concatenate {new_marker} at the end",
        "extend {text_path} with one trailing record {new_marker} instead of rewriting the previous content",
    ),
    "make_directory": (
        "allocate the workspace folder {directory}; the requested object is a directory, not a file",
        "create the scoped directory hierarchy at {directory} without writing a document there",
    ),
    "copy_file": (
        "leave {source_path} intact while duplicating its exact bytes into {dest_path}",
        "produce a second identical file at {dest_path} from {source_path}, so both paths remain afterward",
    ),
    "move_file": (
        "relocate {source_path} to {dest_path} so the origin path is absent after the bytes arrive",
        "rename the existing file from {source_path} into {dest_path}; do not retain a source copy",
    ),
    "delete_file": (
        "erase the explicitly scoped workspace path {text_path} itself, not merely a line within it",
        "remove the complete named artifact {text_path} from the workspace",
    ),
    "bind_evidence": (
        "turn an already observed exact line span from {text_path} into cited evidence with its locator and quote",
        "bind the known source excerpt from {text_path} to its precise location without rereading or searching",
    ),
    "check_command": (
        "launch the non-mutating validator argv python {check_path} and capture its process result",
        "run python {check_path} only as a read-only test or inspection, with no intended workspace writes",
    ),
    "run_command": (
        "invoke the local generator argv python {script_path}, which is allowed to update workspace artifacts",
        "execute the scoped potentially mutating build program python {script_path}",
    ),
    "web_search": (
        "discover current evidence about {query} from public web pages rather than local files",
        "search and fetch open internet sources relevant to {query}",
    ),
    "connector_lookup": (
        "retrieve the typed public record for {repository} from a structured repository or registry source",
        "query a structured public catalog for package {package}, not general web pages",
    ),
    "calculator": (
        "derive the exact numeric value of {expression} from the already known operands without lookup",
        "evaluate the arithmetic formula {expression} locally",
    ),
    "date_diff": (
        "count the calendar days separating the known ISO dates {date_a} and {date_b}",
        "compute the absolute day distance from {date_a} to {date_b}",
    ),
    "current_time": (
        "read the live wall clock for the IANA timezone {timezone}",
        "obtain the present time specifically in zone {timezone}",
    ),
    "final_answer": (
        "all contract duties and evidence checks are already satisfied, so return the grounded user-facing response with no tool call",
        "nothing remains to execute or observe; synthesize the final answer from the accepted evidence now",
    ),
    "ABSTAIN": (
        "the requested private capability is unavailable and the described operations provide no safe applicable next step, so choose none",
        "there is not enough observable or supported information to select any listed operation safely",
    ),
}

TEST_ZH: dict[str, tuple[str, str]] = {
    "list_directory": ("只取得 {directory} 下子项的名称、类型和字节大小，不得打开任何文件正文", "返回 {directory} 的有界目录元数据，所列文件的内容必须保持未读取"),
    "search_text": ("在 {directory} 的本地 UTF-8 文本中查找 {marker} 的匹配行，不得使用公网", "找出 {directory} 下 {marker} 的精确工作区出现位置并保留行号"),
    "read_file": ("打开普通文本文件 {text_path} 的有界字节范围且不修改它", "观察 {text_path} 保存的 UTF-8 正文；它不是 JSON 文档并且必须保持不变"),
    "read_json": ("把 {json_path} 作为结构化 JSON 解码并检查规范值，不编辑任何键", "从 {json_path} 读取现有对象或数组，不能当成无结构文本处理"),
    "file_digest": ("只用 SHA-256 和字节长度识别 {text_path}，不读取正文也不改变文件", "仅测量 {text_path} 的内容哈希与大小元数据"),
    "write_file": ("完整设置 {text_path} 这个非 JSON UTF-8 产物的全部字节，如有旧正文则整体替换", "把 {text_path} 生成为一个完整文本文件，而不是 JSON、追加或片段编辑"),
    "write_json": ("把一个完整结构化 JSON 值序列化到 {json_path}，整体替换此前文档", "用请求的完整对象或数组创建 {json_path}，而不是只补若干键"),
    "patch_json": ("仅把指定顶层字段合并进 {json_path} 的现有 JSON，并保留所有未指定键", "对 {json_path} 应用局部键更新，不得替换整份 JSON 文档"),
    "replace_text": ("在 {text_path} 内把一个字面值 {old_marker} 换成 {new_marker}，周围字节全部保留", "只编辑 {text_path} 中一个精确匹配范围并改为 {new_marker}"),
    "remove_line": ("从 {text_path} 精确移除完整等于 {old_marker} 的一行，文件路径和其他行都保留", "删除 {text_path} 中指定的完整 UTF-8 行，不得删除文件本身"),
    "append_file": ("保留 {text_path} 的全部已有字节，并把 {new_marker} 拼到末尾", "给 {text_path} 增加末尾记录 {new_marker}，不要重写此前内容"),
    "make_directory": ("在工作区创建文件夹 {directory}；目标是目录而不是文件", "建立 {directory} 的限定目录层级，不在该位置写文档"),
    "copy_file": ("保留 {source_path}，同时把精确字节复制到 {dest_path}", "由 {source_path} 在 {dest_path} 生成第二个相同文件，完成后两个路径都存在"),
    "move_file": ("把 {source_path} 迁移到 {dest_path}，字节到达后原路径必须消失", "将现有文件从 {source_path} 重命名到 {dest_path}，不得保留源副本"),
    "delete_file": ("删除明确限定的工作区路径 {text_path} 本身，而不是只删其中一行", "从工作区移除完整的命名产物 {text_path}"),
    "bind_evidence": ("把已观察的 {text_path} 精确行范围连同定位和引文绑定为证据", "将已知的 {text_path} 来源摘录绑定到准确位置，不重新读取或搜索"),
    "check_command": ("启动不产生变更的校验 argv：python {check_path}，并记录进程结果", "只把 python {check_path} 作为只读测试或检查运行，不应写工作区"),
    "run_command": ("调用允许更新工作区产物的本地生成 argv：python {script_path}", "执行限定范围、可能产生变更的构建程序 python {script_path}"),
    "web_search": ("从公开网页发现关于 {query} 的当前证据，而不是查本地文件", "在开放互联网来源中检索并获取与 {query} 有关的页面"),
    "connector_lookup": ("从结构化仓库或注册表取得 {repository} 的类型化公开记录", "在结构化公共目录查询包 {package}，而不是搜索普通网页"),
    "calculator": ("根据已知操作数精确算出 {expression} 的数值，不做外部查询", "在本地求值算术公式 {expression}"),
    "date_diff": ("计算已知 ISO 日期 {date_a} 与 {date_b} 之间相隔的日历天数", "求出从 {date_a} 到 {date_b} 的绝对天数距离"),
    "current_time": ("读取 IANA 时区 {timezone} 的实时墙上时钟", "取得 {timezone} 时区此刻的准确时间"),
    "final_answer": ("全部合同职责和证据检查都已满足，不再调用工具，直接返回有依据的用户答复", "已经没有待执行或待观察事项，现在根据已验收证据综合最终答案"),
    "ABSTAIN": ("请求依赖不可用的私有能力，所描述操作都没有安全适用的下一步，因此不选工具", "可观察或受支持的信息不足，无法安全选择任何一个已列操作"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_json(row) + "\n")


def load_base() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rwkv_lh_s69_base", BASE_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen S67 generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_source_pools(
    path: Path,
) -> tuple[dict[str, dict[str, dict[str, list[dict[str, Any]]]]], dict[str, int]]:
    pools: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {
        split: {
            label: {"en": [], "zh": []} for label in NETWORK_EXACT_TOOL_LABELS
        }
        for split in ("train", "dev")
    }
    parsed: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            match = SPLIT_PATTERN.search(line)
            if match is None:
                raise RuntimeError(f"source split marker missing: {path}")
            split = match.group(1)
            if split == "test":
                skipped[split] += 1
                continue
            row = json.loads(line)
            label = str(row["label"])
            language = str(row["language"])
            pools[split][label][language].append(row)
            parsed[split] += 1
    if parsed != Counter({"train": 2000, "dev": 500}) or skipped != Counter(
        {"test": 500}
    ):
        raise RuntimeError(f"source isolation changed: {path}:{parsed}/{skipped}")
    for split in ("train", "dev"):
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                pools[split][label][language].sort(
                    key=lambda row: (
                        str(row.get("cohort")) != "focus",
                        str(row["sample_id"]),
                    )
                )
    return pools, {
        "train_rows_json_parsed": parsed["train"],
        "dev_rows_json_parsed": parsed["dev"],
        "test_rows_skipped_before_json_parse": skipped["test"],
        "test_rows_json_parsed": 0,
        "test_labels_accessed": 0,
    }


def source_for(
    sources: Mapping[str, Any],
    split: str,
    label: str,
    index: int,
    language: str,
) -> tuple[str, Mapping[str, Any] | None, int]:
    if split == "test":
        return "s69-definition", None, (index // 2) % 2
    first_count = SOURCE_COUNTS[split]["s68"]
    source_id = "s68" if index < first_count else "s65"
    local_index = index if source_id == "s68" else index - first_count
    occurrence = local_index // 2
    pool = sources[source_id][split][label][language]
    required = first_count // 2 if source_id == "s68" else SOURCE_COUNTS[split]["s65"] // 2
    if len(pool) < required:
        raise RuntimeError(
            f"insufficient {source_id} source pool: {split}/{label}/{language}/{len(pool)}"
        )
    return source_id, pool[occurrence], occurrence


def install_construction(base: ModuleType, sources: Mapping[str, Any]) -> None:
    original_context_for = base.context_for
    original_prior_actions_for = base.prior_actions_for

    def context_for(split: str, label: str, index: int) -> dict[str, str]:
        if split != "test":
            value = dict(original_context_for(split, label, index))
        else:
            token = base.stable_hex("S69-test-frame", split, index)[:14]
            root = TEST_ROOTS[index % len(TEST_ROOTS)]
            stem = f"scopes/{root}/{token}"
            value = {
                "token": token,
                "root": root,
                "text_path": stem + (".txt" if index % 2 == 0 else ".md"),
                "json_path": stem + ".json",
                "directory": stem + "-folder",
                "source_path": f"incoming/{root}/{token}-source.dat",
                "dest_path": f"outgoing/{root}/{token}-destination.dat",
                "check_path": f"checks/{root}/{token}-verify.py",
                "script_path": f"build/{root}/{token}-generate.py",
                "marker": f"needle-{token[:8]}",
                "old_marker": f"obsolete-{token[:8]}",
                "new_marker": f"current-{token[:8]}",
                "query": f"public release status {root} {token[:8]}",
                "repository": f"{root}/{token[:8]}-repository",
                "package": f"{root}-{token[:8]}-package",
                "expression": f"({index + 29} * 4) - 7",
                "date_a": f"2024-{(index % 9) + 1:02d}-{(index % 18) + 1:02d}",
                "date_b": f"2026-{((index + 4) % 9) + 1:02d}-{((index + 7) % 18) + 1:02d}",
                "timezone": "Europe/Amsterdam" if index % 2 == 0 else "Asia/Shanghai",
            }
        value["_s69_split"] = split
        return value

    def request_for(
        split: str,
        label: str,
        index: int,
        language: str,
        context: Mapping[str, str],
    ) -> str:
        source_id, source, variant = source_for(
            sources, split, label, index, language
        )
        if source is not None:
            return str(source["task_request"])
        inventory = TEST_EN if language == "en" else TEST_ZH
        core = inventory[label][variant].format(**context)
        occurrence = index // 2
        modifier = (
            TEST_EN_MODIFIERS if language == "en" else TEST_ZH_MODIFIERS
        )[occurrence % 5]
        if language == "en":
            return (
                f"{modifier}, {core}. Scope token {context['token']}; "
                "select only the operation matching this boundary."
            )
        return (
            f"{modifier}，{core}。范围标识 {context['token']}；"
            "只选择符合该边界的一项操作。"
        )

    def prior_actions_for(
        label: str,
        index: int,
        context: Mapping[str, str],
        contract: Any,
    ) -> tuple[list[Any], int]:
        split = str(context["_s69_split"])
        language = "en" if index % 2 == 0 else "zh"
        _source_id, source, _variant = source_for(
            sources, split, label, index, language
        )
        if source is None:
            return original_prior_actions_for(label, index, context, contract)
        progress = source.get("progress") or {}
        succeeded = [str(value) for value in progress.get("succeeded_operations") or ()]
        failed = [str(value) for value in progress.get("failed_operations") or ()]
        actions = []
        for sequence, operation in enumerate(succeeded, start=1):
            actions.append(
                base.action_record(
                    sequence=sequence,
                    operation=operation,
                    arguments=base.operation_arguments(operation, context),
                    contract_digest=contract.contract_digest,
                    success=True,
                )
            )
        for operation in failed:
            actions.append(
                base.action_record(
                    sequence=len(actions) + 1,
                    operation=operation,
                    arguments=base.operation_arguments(operation, context),
                    contract_digest=contract.contract_digest,
                    success=False,
                )
            )
        if len(actions) > 3:
            raise RuntimeError("S69 source progress exceeds action budget")
        return actions, int(progress.get("protocol_rejection_count") or 0)

    base.context_for = context_for
    base.request_for = request_for
    base.prior_actions_for = prior_actions_for


def build_row(
    base: ModuleType,
    sources: Mapping[str, Any],
    split: str,
    label: str,
    index: int,
) -> dict[str, Any]:
    row = dict(base.build_row(split, label, index))
    language = str(row["language"])
    source_id, source, variant = source_for(
        sources, split, label, index, language
    )
    token = base.stable_hex(
        "S69-row", split, label, index, row["rendered_input_sha256"]
    )[:24]
    source_sample = str(source["sample_id"]) if source is not None else ""
    row.update(
        {
            "schema_version": ROW_SCHEMA,
            "dataset_version": DATASET_VERSION,
            "sample_id": f"S69-{split.upper()}-{token}",
            "trajectory_id": f"S69-TRAJECTORY-{token}",
            "source_family_id": f"s69:{split}:{label}:{token}",
            "source_dataset": source_id,
            "source_split": split,
            "source_sample_id": source_sample,
            "source_cohort": str(source.get("cohort") or "") if source else "",
            "semantic_core_variant": variant,
            "contrastive_frame_id": (
                f"S69-TEST-FRAME-{index:03d}"
                if split == "test"
                else f"S69-SOURCE-{split}-{label}-{index:03d}"
            ),
            "label_generation": (
                "independent_tool-description-semantic-definition"
                if split == "test"
                else "frozen_train-dev-request-plus-current-v2-contract-progress"
            ),
        }
    )
    context = base.context_for(split, label, index)
    if split == "test":
        occurrence = index // 2
        modifier = (
            TEST_EN_MODIFIERS if language == "en" else TEST_ZH_MODIFIERS
        )[occurrence % 5]
        shared = {
            "root": context["root"],
            "token": context["token"],
            "text_path": context["text_path"],
            "source_path": context["source_path"],
            "dest_path": context["dest_path"],
            "modifier": modifier,
            "language": language,
        }
    else:
        shared = {
            "source_dataset": source_id,
            "source_sample_id": source_sample,
            "language": language,
        }
    row["contrastive_context_sha256"] = hashlib.sha256(
        canonical_json(shared).encode("utf-8")
    ).hexdigest()
    return row


def validate_rows(
    base: ModuleType,
    rows_by_split: Mapping[str, list[dict[str, Any]]],
) -> None:
    if {split: len(rows) for split, rows in rows_by_split.items()} != base.EXPECTED_COUNTS:
        raise RuntimeError("S69 split counts changed")
    for split, rows in rows_by_split.items():
        expected_labels = Counter(
            {
                label: base.COUNTS_PER_LABEL[split]
                for label in NETWORK_EXACT_TOOL_LABELS
            }
        )
        if Counter(str(row["label"]) for row in rows) != expected_labels:
            raise RuntimeError(f"S69 label balance changed: {split}")
        if Counter(str(row["language"]) for row in rows) != Counter(
            {"en": len(rows) // 2, "zh": len(rows) // 2}
        ):
            raise RuntimeError(f"S69 language balance changed: {split}")
        for label in NETWORK_EXACT_TOOL_LABELS:
            source_counts = Counter(
                str(row["source_dataset"])
                for row in rows
                if row["label"] == label
            )
            if source_counts != Counter(SOURCE_COUNTS[split]):
                raise RuntimeError(
                    f"S69 source balance changed: {split}/{label}/{source_counts}"
                )
    test_rows = rows_by_split["test"]
    for label in NETWORK_EXACT_TOOL_LABELS:
        for language in ("en", "zh"):
            variants = {
                int(row["semantic_core_variant"])
                for row in test_rows
                if row["label"] == label and row["language"] == language
            }
            if variants != {0, 1}:
                raise RuntimeError(
                    f"S69 test variants changed: {label}/{language}/{variants}"
                )
    frames: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in test_rows:
        frames[str(row["contrastive_frame_id"])].append(row)
    if len(frames) != 20:
        raise RuntimeError("S69 test frame count changed")
    for frame, members in frames.items():
        if {str(row["label"]) for row in members} != set(
            NETWORK_EXACT_TOOL_LABELS
        ):
            raise RuntimeError(f"S69 test frame labels changed: {frame}")
        if len({str(row["contrastive_context_sha256"]) for row in members}) != 1:
            raise RuntimeError(f"S69 test frame context changed: {frame}")

    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]
    for key in ("sample_id", "source_family_id", "rendered_input_sha256"):
        if len({str(row[key]) for row in all_rows}) != len(all_rows):
            raise RuntimeError(f"S69 {key} values are not unique")
    purity_fields = (
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "contains_planner_raw_json",
        "generated_rwkv_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in all_rows for field in purity_fields):
        raise RuntimeError("S69 role purity changed")
    for left_index, left in enumerate(base.SPLITS):
        for right in base.SPLITS[left_index + 1 :]:
            for key in ("task_request", "source_family_id", "rendered_input_sha256"):
                left_values = {str(row[key]) for row in rows_by_split[left]}
                right_values = {str(row[key]) for row in rows_by_split[right]}
                if left_values & right_values:
                    raise RuntimeError(f"S69 {key} overlap: {left}/{right}")


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    if not dot:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm)


def s68_locked_requests() -> tuple[
    list[tuple[str, Counter[bytes]]], set[str], dict[str, int]
]:
    values: list[tuple[str, Counter[bytes]]] = []
    digests: set[str] = set()
    parsed = 0
    skipped: Counter[str] = Counter()
    with (S68 / "cases.jsonl").open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            match = SPLIT_PATTERN.search(line)
            if match is None:
                raise RuntimeError("S68 isolation split marker missing")
            split = match.group(1)
            if split != "test":
                skipped[split] += 1
                continue
            row = json.loads(line)
            request = str(row["task_request"])
            encoded = request.encode("utf-8")
            values.append(
                (
                    f"s68-test-line-{line_number}",
                    Counter(
                        encoded[index : index + 5]
                        for index in range(max(0, len(encoded) - 4))
                    ),
                )
            )
            digests.add(hashlib.sha256(encoded).hexdigest())
            parsed += 1
    if parsed != 500 or skipped != Counter({"train": 2000, "dev": 500}):
        raise RuntimeError("S68 locked isolation scan changed")
    return values, digests, {
        "s68_test_rows_json_parsed_for_similarity_only": parsed,
        "s68_test_labels_accessed": 0,
        "s68_test_requests_persisted": 0,
    }


def main() -> None:
    frozen = {
        PREREGISTRATION: PREREGISTRATION_SHA256,
        BASE_GENERATOR: BASE_GENERATOR_SHA256,
        S68 / "cases.jsonl": S68_CASES_SHA256,
        S68 / "manifest.json": S68_MANIFEST_SHA256,
        S65 / "cases.jsonl": S65_CASES_SHA256,
        S65 / "manifest.json": S65_MANIFEST_SHA256,
        S68_LOCKED_RESULT: S68_LOCKED_RESULT_SHA256,
        S66_LOCKED_RESULT: S66_LOCKED_RESULT_SHA256,
    }
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S69 dataset")
    for path, expected in frozen.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S69 frozen input changed: {path}: {actual}")
    if set(TEST_EN) != set(NETWORK_EXACT_TOOL_LABELS) or set(TEST_ZH) != set(
        NETWORK_EXACT_TOOL_LABELS
    ):
        raise RuntimeError("S69 test semantic labels changed")
    if any(len(value) != 2 for value in [*TEST_EN.values(), *TEST_ZH.values()]):
        raise RuntimeError("S69 test semantic variant count changed")

    s68_pools, s68_isolation = load_source_pools(S68 / "cases.jsonl")
    s65_pools, s65_isolation = load_source_pools(S65 / "cases.jsonl")
    sources = {"s68": s68_pools, "s65": s65_pools}
    base = load_base()
    install_construction(base, sources)
    if set(TEST_ROOTS) & set().union(*(set(base.LEXICONS[split]) for split in base.SPLITS)):
        raise RuntimeError("S69 test roots overlap S67 roots")
    rows_by_split = {
        split: [
            build_row(base, sources, split, label, index)
            for label in NETWORK_EXACT_TOOL_LABELS
            for index in range(base.COUNTS_PER_LABEL[split])
        ]
        for split in base.SPLITS
    }
    validate_rows(base, rows_by_split)
    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]

    references, forbidden_paths, task_ids, audit_hashes = base.holdout_contract()
    forbidden_literals = {
        value for value in forbidden_paths | task_ids if len(value) >= 6
    }
    for row in all_rows:
        matches = [
            value for value in forbidden_literals if value in str(row["task_request"])
        ]
        if matches:
            raise RuntimeError(
                f"S69 row contains holdout literal: {row['sample_id']}:{matches[:3]}"
            )
    ladder_references = [
        (identity, base.byte_ngrams(text)) for identity, text in references
    ]
    maximum_ladder: dict[str, Any] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in all_rows:
        grams = base.byte_ngrams(str(row["task_request"]))
        for identity, reference in ladder_references:
            score = base.cosine(grams, reference)
            if score > float(maximum_ladder["score"]):
                maximum_ladder = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": identity,
                }
    if float(maximum_ladder["score"]) >= 0.95:
        raise RuntimeError(f"S69 Ladder holdout similarity failed: {maximum_ladder}")

    locked_references, exact_locked_digests, locked_isolation = (
        s68_locked_requests()
    )
    maximum_locked: dict[str, Any] = {
        "score": -1.0,
        "sample_id": "",
        "holdout_id": "",
    }
    for row in all_rows:
        request = str(row["task_request"])
        if hashlib.sha256(request.encode("utf-8")).hexdigest() in exact_locked_digests:
            raise RuntimeError(f"S69 reused an S68 locked request: {row['sample_id']}")
        grams = base.byte_ngrams(request)
        for identity, reference in locked_references:
            score = cosine(grams, reference)
            if score > float(maximum_locked["score"]):
                maximum_locked = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": identity,
                }
    if float(maximum_locked["score"]) >= 0.95:
        raise RuntimeError(f"S69 S68-locked similarity failed: {maximum_locked}")

    base.DATASET_VERSION = DATASET_VERSION
    base.STATE_ROW_SCHEMA = STATE_ROW_SCHEMA
    exported, token_stats = base.state_rows(RWKVTokenizer(), rows_by_split)
    for split, rows in exported.items():
        for index, row in enumerate(rows):
            row["schema_version"] = STATE_ROW_SCHEMA
            row["dataset_version"] = DATASET_VERSION
            row["sample_id"] = f"S69-STATE-{split.upper()}-{index:04d}"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, all_rows)
    state_paths = {
        split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in ("train", "dev")
    }
    for split, path in state_paths.items():
        write_jsonl(path, exported[split])
    manifest = {
        "schema_version": "rwkv-lh.network-selector-uniform-semantic-manifest.s69.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "uniformly diversify all 25 CurrentDirectStageV2 operation semantics without reusing any prior locked-test row",
        "counts": base.EXPECTED_COUNTS,
        "label_counts": {
            split: dict(sorted(Counter(str(row["label"]) for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "language_counts": {
            split: dict(sorted(Counter(str(row["language"]) for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "source_counts_by_label": {
            split: {
                label: dict(
                    sorted(
                        Counter(
                            str(row["source_dataset"])
                            for row in rows_by_split[split]
                            if row["label"] == label
                        ).items()
                    )
                )
                for label in NETWORK_EXACT_TOOL_LABELS
            }
            for split in base.SPLITS
        },
        "sources": {
            "s68": {
                "cases_sha256": S68_CASES_SHA256,
                "manifest_sha256": S68_MANIFEST_SHA256,
                "allowed_splits": ["train", "dev"],
                "isolation": s68_isolation,
            },
            "s65": {
                "cases_sha256": S65_CASES_SHA256,
                "manifest_sha256": S65_MANIFEST_SHA256,
                "allowed_splits": ["train", "dev"],
                "isolation": s65_isolation,
            },
            "s69_test": {
                "source": "independent formal tool descriptions",
                "variants_per_label_language": 2,
                "shared_contrastive_frames": 20,
                "root_pool": list(TEST_ROOTS),
            },
        },
        "protocol": {
            "compact_schema_version": base.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "contract_projection_version": base.SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION,
            "renderer": str(base.RENDERER.relative_to(ROOT)),
            "renderer_sha256": base.FROZEN[base.RENDERER],
            "runtime_projection": str(base.RUNTIME_PROJECTION.relative_to(ROOT)),
            "runtime_projection_sha256": base.FROZEN[base.RUNTIME_PROJECTION],
            "contract_progress": str(base.CONTRACT_PROGRESS.relative_to(ROOT)),
            "contract_progress_sha256": base.FROZEN[base.CONTRACT_PROGRESS],
            "canonical_runtime_construction": True,
            "literal_requirement_byte_tail": True,
            "persistent_history_replayed": True,
        },
        "state_training_contract": {
            "train_rows": len(exported["train"]),
            "dev_rows": len(exported["dev"]),
            "dev_optimizer_use": False,
            "loss_mask": "target_suffix",
            "target_prefix": base.TARGET_PREFIX,
            "jsonl_bos_token_id": 0,
            "ctx_len": base.CTX_LEN,
            "seed": base.SEED,
            "physical_gpu": 0,
            **token_stats,
            "target_boundary_additive": True,
            "target_truncation_count": 0,
        },
        "holdout": {
            "ladder_tasks_sha256": base.FROZEN[base.LADDER / "tasks.json"],
            "ladder_acceptance_sha256": base.FROZEN[base.LADDER / "acceptance.json"],
            "e3_results_sha256": base.FROZEN[base.E3_RUN / "results.json"],
            "e3_audit_sha256": dict(sorted(audit_hashes.items())),
            "similarity_algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold_exclusive": 0.95,
            "maximum_ladder_similarity": maximum_ladder,
            "s68_locked_result_sha256": S68_LOCKED_RESULT_SHA256,
            "maximum_s68_locked_similarity": maximum_locked,
            "exact_s68_locked_request_overlap": 0,
            **locked_isolation,
            "optimizer_use": False,
            "candidate_selection_use": False,
        },
        "split_integrity": {
            "exact_request_overlap": 0,
            "source_family_overlap": 0,
            "rendered_input_overlap": 0,
            "test_root_overlap": 0,
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
            "sha256": PREREGISTRATION_SHA256,
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "frozen_base_path": str(BASE_GENERATOR.relative_to(ROOT)),
            "frozen_base_sha256": BASE_GENERATOR_SHA256,
        },
        "files": {
            "cases.jsonl": {
                "rows": len(all_rows),
                "bytes": cases_path.stat().st_size,
                "sha256": sha256_file(cases_path),
            },
            **{
                path.name: {
                    "rows": len(exported[split]),
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
        "# S69 uniform semantic Selector corpus\n\n"
        "A balanced bilingual CurrentDirectStageV2 corpus mixing only S68/S65 "
        "train-dev sources and a new independent all-label locked test.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s69_uniform_semantic_dataset_finalized",
                "counts": base.EXPECTED_COUNTS,
                "maximum_ladder_similarity": maximum_ladder,
                "maximum_s68_locked_similarity": maximum_locked,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
