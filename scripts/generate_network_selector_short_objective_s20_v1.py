#!/usr/bin/env python3
"""Generate the balanced 3K short-objective corpus for NET-SEL-2P9-S20."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    network_selector_menu_digest,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "data/datasets/rwkv_lh_network_selector_description_s5_v1/tool_descriptions.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S20_SHORT_OBJECTIVE_DESCRIPTION_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_short_objective_s20_v1"
EXPECTED = {
    "tools": "97218a227f31623136962a6506cc52a01638c98986d4089f52dca2b97a60dfca",
    "ecra": "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a",
}
VERSION = "rwkv-lh.network-selector.short-objective-s20.v1"
FRAMES = (
    ("train", "zh", "原子步骤：{action_zh}{target}；{guard_zh}"),
    ("train", "en", "Atomic step: {action_en} {target}; {guard_en}"),
    ("train", "zh", "现在只做一件事——{action_zh}{target}。"),
    ("train", "en", "Use the one operation that will {action_en_lower} {target}, and then stop."),
    ("dev", "zh", "下一步需要{action_zh}{target}，不要执行其他动作。"),
    ("test", "en", "For the next single action, {action_en_lower} {target}."),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    value = text.encode("utf-8")
    return Counter(value[index:index + n] for index in range(max(0, len(value) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return dot / math.sqrt(sum(value * value for value in left.values()) * sum(value * value for value in right.values()))


def targets(label: str) -> list[str]:
    local_paths = [
        "src", "tests", "docs", "assets", "configs", "examples", "scripts",
        "packages", "benchmarks", "reports", "fixtures", "templates", "data/raw",
        "data/cache", "modules/core", "modules/api", "notes", "artifacts", "build/logs",
        "workspace/input",
    ]
    text_files = [
        "README.md", "pyproject.toml", "notes/design.txt", "src/main.py", "docs/guide.md",
        "CHANGELOG.md", "configs/app.env", "tests/cases.txt", "scripts/build.sh", "LICENSE",
        "release_target.txt", "repository_name.txt", "private/token.txt", "private/customer.tsv",
        "product_name.txt", "public_url.txt", "numbers.txt", "destination.txt", "vendor.txt",
        "alert_region.txt",
    ]
    json_files = [
        "config.json", "data/items.json", "package.json", "settings.json", "schema.json",
        "request.json", "repo.json", "paper.json", "dates.json", "timezone.json",
        "private/credentials.json", "city.json", "manifest.json", "service.json", "release.json",
        "advisory.json", "profile.json", "build.json", "metadata.json", "targets.json",
    ]
    if label == "list_directory":
        return [f"列出本地 `{path}/` 的直接子项" if i % 2 == 0 else f"list direct entries under `{path}/`" for i, path in enumerate(local_paths)]
    if label == "search_text":
        return [f"在 `{local_paths[i]}/` 内定位文本 `marker_{i:02d}` 的行号" if i % 2 == 0 else f"find local lines containing `symbol_{i:02d}` below `{local_paths[i]}/`" for i in range(20)]
    if label == "read_file":
        return [f"读取本地 `{path}` 的指定文本片段" if i < 10 else f"read `{path}` locally before any later external lookup; never expose its literal private value" for i, path in enumerate(text_files)]
    if label == "read_json":
        return [f"解析本地 `{path}` 并查看指定字段" if i < 10 else f"read the requested field from local `{path}` before any dependent action" for i, path in enumerate(json_files)]
    if label == "file_digest":
        return [f"计算本地 `artifacts/file_{i:02d}.bin` 的 SHA-256 与字节数" if i % 2 == 0 else f"observe the SHA-256 and size of local `dist/archive_{i:02d}.tar`" for i in range(20)]
    if label == "write_file":
        return [f"把文本 `entry-{i:02d}` 原子写入 `output/text_{i:02d}.txt`" if i % 2 == 0 else f"atomically create `notes/result_{i:02d}.md` with the supplied UTF-8 body" for i in range(20)]
    if label == "write_json":
        return [f"用完整值 `{{\"item\":{i},\"ok\":true}}` 创建 `output/value_{i:02d}.json`" if i % 2 == 0 else f"atomically write the complete supplied JSON value to `data/result_{i:02d}.json`" for i in range(20)]
    if label == "patch_json":
        return [f"仅把 `configs/settings_{i:02d}.json` 顶层键 `enabled` 更新为 true" if i % 2 == 0 else f"update top-level key `retries` in `configs/job_{i:02d}.json` while preserving other keys" for i in range(20)]
    if label == "replace_text":
        return [f"将 `docs/page_{i:02d}.md` 中唯一的 `old_{i}` 精确替换为 `new_{i}`" if i % 2 == 0 else f"replace the single literal `before_{i}` with `after_{i}` in `templates/t_{i:02d}.txt`" for i in range(20)]
    if label == "remove_line":
        return [f"从 `configs/env_{i:02d}.txt` 删除完整行 `legacy_{i}=true`" if i % 2 == 0 else f"remove the exact whole line `obsolete-{i}` from `lists/items_{i:02d}.txt`" for i in range(20)]
    if label == "append_file":
        return [f"在 `logs/change_{i:02d}.txt` 末尾追加已给出的行 `done-{i}`" if i % 2 == 0 else f"append the supplied UTF-8 record to `reports/run_{i:02d}.log`" for i in range(20)]
    if label == "make_directory":
        return [f"在工作区内创建目录 `output/batch_{i:02d}`" if i % 2 == 0 else f"create workspace directory `cache/unit_{i:02d}`" for i in range(20)]
    if label == "copy_file":
        return [f"把本地 `source/file_{i:02d}.txt` 原样复制到 `backup/file_{i:02d}.txt`" if i % 2 == 0 else f"copy exact bytes from `assets/a_{i:02d}.bin` to `dist/a_{i:02d}.bin`" for i in range(20)]
    if label == "move_file":
        return [f"将 `draft/item_{i:02d}.md` 移动到 `archive/item_{i:02d}.md`" if i % 2 == 0 else f"rename `output/tmp_{i:02d}.csv` to `completed/final_{i:02d}.csv`" for i in range(20)]
    if label == "delete_file":
        return [f"删除明确指定的工作区文件 `temp/obsolete_{i:02d}.tmp`" if i % 2 == 0 else f"delete scoped workspace path `generated/run_{i:02d}.log`" for i in range(20)]
    if label == "bind_evidence":
        return [f"绑定本地 `evidence/source_{i:02d}.txt` 第 {i + 1}-{i + 3} 行及定位信息" if i % 2 == 0 else f"retain an exact quoted line span from `records/proof_{i:02d}.md` with its locator" for i in range(20)]
    if label == "check_command":
        commands = ["python -m pytest -q", "python -m compileall src", "ruff check src", "python -m unittest", "mypy src"]
        return [f"以无 shell 的只读检查方式运行 `{commands[i % len(commands)]}`，检查目标编号 {i}" if i % 2 == 0 else f"run read-only argv `{commands[i % len(commands)]}` for inspection target {i}" for i in range(20)]
    if label == "run_command":
        commands = ["python -m tools.generate", "python -m build", "uv run scripts/prepare.py", "python scripts/migrate.py", "make assets"]
        return [f"以 argv 且禁用 shell 执行可能写入文件的命令 `{commands[i % len(commands)]}`，任务编号 {i}" if i % 2 == 0 else f"run potentially mutating argv `{commands[i % len(commands)]}` for job {i} with shell disabled" for i in range(20)]
    if label == "web_search":
        items = [
            "Acme Cloud 当前公开状态页", "Northwind 博物馆今天的开放时间", "Orion 产品官网的支持政策",
            "公开 URL https://example.org/docs/current", "供应商网页上的最新兼容性表", "城市公共展览是否仍在举办",
            "航空公司官网今天的延误公告", "托管 API 当前公开条款", "标准组织最新解释页面", "公司的公开故障报告",
            "产品官网目前的价格说明", "公共博客的正式发布公告", "在线服务的官方 FAQ", "公开网页上的申请截止日期",
            "硬件厂商官网驱动支持矩阵", "公共赛事网页公布的最终结果", "服务状态网站当前事件", "未指定仓库的软件安装文档",
            "公开 changelog 页面", "用户给出的网页 URL 中的命令示例",
        ]
        return [f"搜索并获取 {item}" if i % 2 == 0 else f"search the general public web for {item}" for i, item in enumerate(items)]
    if label == "connector_lookup":
        items = [
            "GitHub `octocat/Hello-World` 的默认分支", "GitHub `pallets/flask` 最新 release", "PyPI 项目 `httpx` 当前版本",
            "npm 包 `lodash` 的 latest dist-tag", "crates.io crate `tokio` 的稳定版本", "DOI `10.1145/3581783.3611784` 的论文元数据",
            "arXiv `2401.04088` 的标题与日期", "Berlin 的结构化天气观测", "Ontario 当前有效的官方天气预警",
            "GitHub `python/cpython` 的提交元数据", "GitHub `astral-sh/uv` 中指定文件内容", "PyPI `numpy` 精确版本发布日期",
            "npm `typescript` 指定版本元数据", "DOI `10.1038/s41586-023-06747-5` 的作者", "GitHub `rust-lang/rust` 的许可证字段",
            "GitHub `psf/requests` 的开放 issue 元数据", "Osaka 未来三天结构化天气", "Queensland 活跃恶劣天气警报",
            "crates.io `serde_json` 最新稳定版本", "arXiv `1706.03762` 的期刊与发布日期",
        ]
        return [f"从精确结构化公共源查询 {item}" if i % 2 == 0 else f"query the exact structured public source for {item}" for i, item in enumerate(items)]
    if label == "calculator":
        expressions = ["(19*17+5)/4", "2**12+7*9", "7200/96-8", "43/125*100", "(6.75+9.5)*3", "(14+22+40)/4", "1048576**0.5", "81*73-17", "(5**6)/25", "9999-444*7", "17/32", "(88+12)*1.25", "3.14159*20", "144/12+31", "7**4-9", "(51-19)*8", "625**0.5+3", "1200*0.075", "(13+27+41)/9", "65535%127"]
        return [f"精确计算表达式 `{value}`" if i % 2 == 0 else f"evaluate the complete known expression `{value}` exactly" for i, value in enumerate(expressions)]
    if label == "date_diff":
        pairs = [(f"202{i % 7}-0{1 + i % 8}-{1 + i % 20:02d}", f"202{i % 7}-1{(i % 2)}-{5 + i % 20:02d}") for i in range(20)]
        return [f"计算已知日期 `{left}` 与 `{right}` 的绝对日历天数差" if i % 2 == 0 else f"calculate calendar-day distance between known dates `{left}` and `{right}`" for i, (left, right) in enumerate(pairs)]
    if label == "current_time":
        zones = ["Asia/Tokyo", "Europe/Paris", "UTC", "America/Chicago", "Australia/Sydney", "Asia/Singapore", "Europe/Berlin", "America/Denver", "Pacific/Auckland", "Asia/Kolkata", "Africa/Cairo", "America/Toronto", "Europe/Rome", "Asia/Dubai", "America/Sao_Paulo", "Pacific/Honolulu", "Europe/Warsaw", "Asia/Seoul", "America/Vancouver", "Africa/Johannesburg"]
        return [f"观察 IANA 时区 `{zone}` 当前钟表时间" if i % 2 == 0 else f"return the current clock reading for IANA timezone `{zone}`" for i, zone in enumerate(zones)]
    if label == "final_answer":
        return [f"依据已经绑定的证据直接回答结论 `summary-{i:02d}`，无需再调用工具" if i % 2 == 0 else f"give the final user-facing conclusion from sufficient existing evidence set {i:02d}; no tool remains" for i in range(20)]
    if label == "ABSTAIN":
        return [f"请求 `ambiguous-{i:02d}` 缺少唯一目标或必要可观察信息，停止并明确无法选择操作" if i % 2 == 0 else f"do not guess an operation for unsupported or unsafe stage `ambiguous-{i:02d}` with insufficient observable information" for i in range(20)]
    raise ValueError(label)


ACTIONS = {
    "list_directory": ("列出目录元数据：", "List directory metadata for"),
    "search_text": ("搜索本地文本：", "Search local text for"),
    "read_file": ("读取文件片段：", "Read a file range from"),
    "read_json": ("读取规范化 JSON：", "Read canonical JSON from"),
    "file_digest": ("观察文件摘要：", "Observe a file digest for"),
    "write_file": ("写入完整文本文件：", "Write the complete text file for"),
    "write_json": ("写入完整 JSON 值：", "Write the complete JSON value for"),
    "patch_json": ("更新 JSON 顶层键：", "Patch explicit JSON keys for"),
    "replace_text": ("精确替换一个文本：", "Replace one exact text occurrence for"),
    "remove_line": ("删除一整行：", "Remove one complete line from"),
    "append_file": ("追加文本：", "Append text to"),
    "make_directory": ("创建目录：", "Create a directory for"),
    "copy_file": ("复制文件字节：", "Copy exact file bytes for"),
    "move_file": ("移动或重命名文件：", "Move or rename a file for"),
    "delete_file": ("删除明确路径：", "Delete the explicit path for"),
    "bind_evidence": ("绑定本地证据：", "Bind local evidence from"),
    "check_command": ("运行只读检查命令：", "Run a read-only check command for"),
    "run_command": ("运行可能修改环境的命令：", "Run a potentially mutating command for"),
    "web_search": ("查询普通公开网页：", "Search or fetch the general public web for"),
    "connector_lookup": ("查询精确结构化公共源：", "Query an exact structured public source for"),
    "calculator": ("执行确定性算术：", "Calculate"),
    "date_diff": ("计算日期差：", "Calculate the date difference for"),
    "current_time": ("读取当前时钟：", "Observe the current time for"),
    "final_answer": ("直接结束并答复：", "Finish with the answer for"),
    "ABSTAIN": ("拒绝猜测工具：", "Abstain from choosing a tool for"),
}


def guard(label: str) -> tuple[str, str]:
    if label in {"web_search", "connector_lookup"}:
        return ("仅使用与目标匹配的公开来源。", "use only the matching public source type.")
    if label in {"calculator", "date_diff", "current_time"}:
        return ("不要浏览网页或修改工作区。", "do not browse or mutate the workspace.")
    if label in {"final_answer", "ABSTAIN"}:
        return ("不要调用额外工具。", "invoke no additional tool.")
    if label in {"write_file", "write_json", "patch_json", "replace_text", "remove_line", "append_file", "make_directory", "copy_file", "move_file", "delete_file", "run_command"}:
        return ("只执行这个明确的本地变更。", "perform only this explicit local change.")
    return ("只依据本地工作区，不要联网。", "use only the local workspace and never browse.")


def main() -> None:
    if OUTPUT.exists() or not PROTOCOL.is_file():
        raise RuntimeError("S20 output exists or preregistration is missing")
    if sha256_file(TOOLS) != EXPECTED["tools"] or sha256_file(ECRA) != EXPECTED["ecra"]:
        raise RuntimeError("S20 frozen source identity changed")
    tokenizer = RWKVTokenizer()
    rows: list[dict[str, object]] = []
    for label in NETWORK_EXACT_TOOL_LABELS:
        label_targets = targets(label)
        if len(label_targets) != 20 or len(set(label_targets)) != 20:
            raise RuntimeError(f"S20 target inventory changed for {label}")
        action_zh, action_en = ACTIONS[label]
        guard_zh, guard_en = guard(label)
        for frame_index, (split, language, frame) in enumerate(FRAMES):
            for target_index, target in enumerate(label_targets):
                objective = frame.format(
                    action_zh=action_zh,
                    action_en=action_en,
                    action_en_lower=action_en[0].lower() + action_en[1:],
                    target=target,
                    guard_zh=guard_zh,
                    guard_en=guard_en,
                )
                payload = {"schema_version": "rwkv-lh.selector-objective.s20.v1", "objective": objective}
                rendered = "SelectorObjectiveV4: " + canonical_json(payload)
                rows.append({
                    "schema_version": "rwkv-lh.network-selector-short-objective-row.s20.v1",
                    "dataset_version": VERSION,
                    "sample_id": f"NETSEL-S20-{split.upper()}-{label.upper()}-{frame_index:02d}-{target_index:02d}",
                    "semantic_family_id": f"S20-{label}-{frame_index:02d}-{target_index:02d}",
                    "split": split,
                    "label": label,
                    "language": language,
                    "stage_objective": objective,
                    "rendered_input": rendered,
                    "selector_input_sha256": canonical_digest(payload),
                    "prompt_tokens_including_bos": 1 + len(tokenizer.encode(rendered)),
                    "generated_rwkv_text": False,
                })
    expected_splits = Counter({"train": 2000, "dev": 500, "test": 500})
    if Counter(str(row["split"]) for row in rows) != expected_splits or len(rows) != 3000:
        raise RuntimeError("S20 split cardinality changed")
    for split, count in (("train", 80), ("dev", 20), ("test", 20)):
        if Counter(str(row["label"]) for row in rows if row["split"] == split) != Counter({label: count for label in NETWORK_EXACT_TOOL_LABELS}):
            raise RuntimeError(f"S20 class balance changed for {split}")
    for field in ("sample_id", "semantic_family_id", "stage_objective", "rendered_input"):
        if len({str(row[field]) for row in rows}) != len(rows):
            raise RuntimeError(f"S20 duplicate {field}")
    families = {split: {str(row["semantic_family_id"]) for row in rows if row["split"] == split} for split in expected_splits}
    if families["train"] & families["dev"] or families["train"] & families["test"] or families["dev"] & families["test"]:
        raise RuntimeError("S20 semantic families cross splits")
    if max(int(row["prompt_tokens_including_bos"]) for row in rows) > 128:
        raise RuntimeError("S20 compact query exceeds 128 tokens")
    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    references = [(case["case_id"], byte_ngrams(str(case["instruction"]))) for case in holdout]
    maximum = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in rows:
        grams = byte_ngrams(str(row["stage_objective"]))
        for holdout_id, reference in references:
            score = cosine(grams, reference)
            if score > float(maximum["score"]):
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if float(maximum["score"]) >= 0.75:
        raise RuntimeError(f"S20 ECRA contamination gate failed: {maximum}")
    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s20.", dir=OUTPUT.parent))
    cases = staging / "queries.jsonl"
    with cases.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    label_counts = {
        split: dict(sorted(Counter(str(row["label"]) for row in rows if row["split"] == split).items()))
        for split in expected_splits
    }
    language_counts = {
        split: dict(sorted(Counter(str(row["language"]) for row in rows if row["split"] == split).items()))
        for split in expected_splits
    }
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S20 short natural objective description-conditioned selector",
        "counts": dict(sorted(expected_splits.items())),
        "label_counts": label_counts,
        "language_counts": language_counts,
        "class_order": list(NETWORK_EXACT_TOOL_LABELS),
        "menu_digest": network_selector_menu_digest(),
        "query_protocol": "SelectorObjectiveV4 with schema_version and objective only",
        "sources": {
            "tool_descriptions": {"path": str(TOOLS.relative_to(ROOT)), "sha256": EXPECTED["tools"]},
            "ecra_contamination_reference": {"path": str(ECRA.relative_to(ROOT)), "sha256": EXPECTED["ecra"]},
        },
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generator_sha256": sha256_file(Path(__file__)),
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generated_rwkv_text_count": 0,
        "sampling_invocation_count": 0,
        "files": {"queries.jsonl": {"rows": len(rows), "sha256": sha256_file(cases)}},
        "validation": {
            "exact_objective_duplicates": 0,
            "exact_rendered_input_duplicates": 0,
            "cross_split_family_overlap": 0,
            "all_labels_balanced": True,
            "maximum_prompt_tokens_including_bos": max(int(row["prompt_tokens_including_bos"]) for row in rows),
            "holdout_similarity": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "threshold_exclusive": 0.75,
                "maximum": maximum,
                "holdout_sha256": EXPECTED["ecra"],
            },
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
