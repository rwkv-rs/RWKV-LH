"""Generate exactly 10,000 verified RWKV-LH progressive training stages."""

from __future__ import annotations

# ABORTED: this generator expands broad templates to meet a row count, but does
# not ground every sample in an observed RWKV failure transition.  It is kept
# only so the aborted experiment remains auditable and must fail closed.
raise SystemExit(
    "ABORTED generator: mechanical 10K expansion is not failure-grounded; "
    "see data/experiments/RWKV_ACTION_STATE_TUNING_10K_V1_20260826/ABORTED.md"
)

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import parse_model_command, parse_tool_selection
from rwkv_lh.token_budget import get_token_count
from scripts.generate_rwkv_action_state_tuning_v1 import (
    ORACLE_SCHEMA,
    ROOT,
    SEED_ROOT,
    SIMILARITY_VERSION,
    STAGE_SCHEMA,
    VALIDATION_SCHEMA,
    _digest_value,
    _holdout_files,
    _holdout_requests,
    _instantiate,
    _private_oracle,
    _public_candidate,
    _read_jsonl,
    _replay,
    _semantic_family_context,
    _sha256,
    _write_json,
    _write_jsonl,
    _write_text,
)


OUTPUT = ROOT / "data/datasets/rwkv_lh_action_state_tuning_10k_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_ACTION_STATE_TUNING_10K_V1_20260826"
SCANNER_SOURCE = ROOT / "scripts/scan_utf8_byte_ngram_cosine.cpp"
VERSION = "rwkv-lh.action-state-tuning-10k.v1"
OFFICIAL_TOTAL = 10_000
TRAIN_STAGE_COUNT = 9_000
DEV_STAGE_COUNT = 1_000
TRAIN_TRAJECTORY_COUNT = 2_947
DEV_TRAJECTORY_COUNT = 324
TRAJECTORY_COUNT = TRAIN_TRAJECTORY_COUNT + DEV_TRAJECTORY_COUNT
TRAIN_REDUCED_WEIGHT_TWO = {
    *(f"ST-ACT-{index:03d}" for index in range(1, 11)),
    "ST-ACT-017",
    "ST-ACT-019",
}

_SCENE_ADJECTIVES = (
    ("潮蓝", "tidal-blue"), ("琥珀", "amber"), ("苔绿", "moss-green"),
    ("银月", "silver-moon"), ("紫晶", "violet-crystal"), ("赤铜", "copper-red"),
    ("云白", "cloud-white"), ("玄武", "basalt"), ("珊瑚", "coral"),
    ("松烟", "pine-smoke"), ("靛青", "indigo"), ("沙金", "sand-gold"),
    ("霜灰", "frost-grey"), ("梨花", "pear-blossom"), ("海藻", "kelp-green"),
    ("陶红", "clay-red"), ("晨雾", "dawn-mist"), ("星墨", "star-ink"),
    ("蜂蜜", "honey"), ("石英", "quartz"), ("杉木", "cedar"),
    ("孔雀", "peacock"), ("萤火", "firefly"), ("雪松", "snow-cedar"),
)
_SCENE_PLACES = (
    ("潮汐档案亭", "tide archive kiosk"), ("巡展编目舱", "traveling catalog bay"),
    ("高原温室", "highland greenhouse"), ("午夜车辆库", "midnight rail depot"),
    ("声音图书塔", "audio library tower"), ("沙丘机械坊", "dune mechanics workshop"),
    ("浮岛气象室", "floating weather room"), ("地下种子库", "subterranean seed vault"),
    ("河口灯标站", "estuary beacon station"), ("陶片修复室", "pottery restoration room"),
    ("山脊信号屋", "ridge signal house"), ("纸鸢观测台", "kite observation deck"),
    ("盐湖样本馆", "salt-lake sample hall"), ("峡谷邮袋站", "canyon mailbag station"),
    ("松林测绘屋", "pinewood survey lodge"), ("冰原齿轮库", "icefield gear vault"),
    ("云层航海室", "cloud navigation room"), ("竹影校准间", "bamboo calibration room"),
    ("珊瑚票据所", "coral ledger office"), ("古钟维护廊", "clock maintenance gallery"),
    ("风车索引室", "windmill index room"), ("月桂实验棚", "laurel experiment shed"),
    ("远山磁带站", "far-mountain tape station"), ("砂岩清单舱", "sandstone checklist bay"),
)
_SCENE_ROLES = (
    ("浮标记录员", "buoy recorder"), ("巡展馆员", "itinerant curator"),
    ("灌溉调度员", "irrigation dispatcher"), ("车轮检修员", "wheel inspector"),
    ("口述档案员", "oral archivist"), ("轴承技师", "bearing technician"),
    ("云图抄录员", "cloud-chart scribe"), ("种子保管员", "seed custodian"),
    ("灯标校对员", "beacon proofreader"), ("陶片编号员", "sherd indexer"),
    ("信号测量员", "signal surveyor"), ("风向观察员", "wind observer"),
    ("晶体分类员", "crystal classifier"), ("邮袋审计员", "mailbag auditor"),
    ("林线制图员", "treeline cartographer"), ("齿轮验收员", "gear receiver"),
    ("航线核对员", "route reconciler"), ("刻度校准员", "scale calibrator"),
    ("票据装订员", "ledger binder"), ("钟摆测试员", "pendulum tester"),
    ("索引修订员", "index reviser"), ("样本登记员", "sample registrar"),
    ("磁带编目员", "tape cataloger"), ("清单复核员", "checklist reviewer"),
)
_SCENE_OBJECTS = (
    ("石英潮汐尺", "quartz tide ruler"), ("琥珀运输签", "amber transit tag"),
    ("玄武岩水槽", "basalt water trough"), ("钨钢探伤笔", "tungsten inspection pen"),
    ("软木回声板", "cork echo panel"), ("陶瓷轴承盒", "ceramic bearing case"),
    ("银丝云图框", "silver cloud-chart frame"), ("杉木种子盘", "cedar seed tray"),
    ("海藻罗盘", "kelp compass"), ("靛青陶片袋", "indigo sherd pouch"),
    ("黄铜信号镜", "brass signal mirror"), ("纸鸢风标", "kite wind vane"),
    ("盐晶样本管", "salt-crystal vial"), ("帆布邮袋扣", "canvas mail clasp"),
    ("松脂测绘板", "resin survey board"), ("霜纹齿轮规", "frost gear gauge"),
    ("云母航海片", "mica navigation tile"), ("竹节校准棒", "bamboo calibration rod"),
    ("珊瑚票据夹", "coral ledger clip"), ("月相钟摆锤", "lunar pendulum weight"),
    ("风车索引轮", "windmill index wheel"), ("月桂样本匣", "laurel sample drawer"),
    ("远山磁带盒", "mountain tape box"), ("砂岩清单牌", "sandstone checklist slate"),
)
_LABEL_STARTS = (
    "Aru", "Bel", "Cae", "Dru", "Eli", "Fen", "Gha", "Huo",
    "Ira", "Jem", "Kyo", "Lun", "Mav", "Nes", "Oru", "Pra",
    "Qin", "Rho", "Sae", "Tov", "Uma", "Vex", "Wen", "Xal",
    "Yori", "Zun", "Bran", "Ciri", "Doma", "Eris", "Faro", "Glen",
)
_LABEL_MIDDLES = (
    "la", "meri", "to", "savi", "nex", "palo", "runi", "dara",
    "kesi", "vora", "tani", "milo", "zeta", "quor", "beli", "cana",
    "firi", "galo", "hena", "jora", "lumi", "nori", "peta", "riva",
    "seno", "tula", "vani", "wero", "xeni", "yara", "zori", "brio",
)
_LABEL_ENDS = (
    "-arc", "-bay", "-crest", "-delta", "-ember", "-field", "-grove", "-harbor",
    "-isle", "-jetty", "-keep", "-loft", "-mesa", "-nook", "-orbit", "-pier",
    "-quay", "-ridge", "-spire", "-trace", "-upland", "-vale", "-wharf", "-yard",
    "-zenith", "-brook", "-cairn", "-drift", "-estuary", "-forge", "-glade", "-heath",
)


def _family_labels(seed_id: str, split: str, family_index: int) -> str:
    labels: list[str] = []
    for index in range(24):
        digest = hashlib.sha256(
            f"{seed_id}:{split}:{family_index}:label:{index}".encode("utf-8")
        ).digest()
        labels.append(
            _LABEL_STARTS[digest[0] % len(_LABEL_STARTS)]
            + _LABEL_MIDDLES[digest[1] % len(_LABEL_MIDDLES)]
            + _LABEL_ENDS[digest[2] % len(_LABEL_ENDS)]
        )
    return ", ".join(labels)


def _unique_family_context(
    seed_id: str,
    split: str,
    family_index: int,
    language: str,
) -> str:
    digest = hashlib.sha256(
        f"{seed_id}:{split}:{family_index}".encode("utf-8")
    ).digest()
    selected = []
    tables = (_SCENE_ADJECTIVES, _SCENE_PLACES, _SCENE_ROLES, _SCENE_OBJECTS)
    for offset in range(12):
        table = tables[offset % len(tables)]
        selected.append(table[digest[offset] % len(table)])
    side = 0 if language == "zh" else 1
    words = [item[side] for item in selected]
    labels = _family_labels(seed_id, split, family_index)
    if language == "zh":
        return (
            f"这是虚构的{words[0]}{words[1]}交接场景，{words[2]}使用{words[3]}核对合成记录。"
            f"第二工作台由{words[4]}{words[5]}管理，{words[6]}只接触{words[7]}编号。"
            f"收尾窗口位于{words[8]}{words[9]}，{words[10]}用{words[11]}复核结果。"
            f"该家族专用的虚构目录标签为：{labels}。"
            "所有名称、实体和值均为独立合成素材，不对应真实组织、人物或设备。"
        )
    return (
        f"This is a fictional {words[0]} {words[1]} handoff where a {words[2]} "
        f"checks synthetic records with a {words[3]}. A second desk in the {words[4]} "
        f"{words[5]} is managed by a {words[6]} handling only {words[7]} identifiers. "
        f"The closing window sits in the {words[8]} {words[9]}, where a {words[10]} "
        f"verifies results with a {words[11]}. Family-only fictional catalog labels are: "
        f"{labels}. Every name, entity, and value is "
        "independent synthetic material with no real organization, person, or device."
    )


def _seed_ids() -> list[str]:
    rows = _read_jsonl(SEED_ROOT / "seed_templates.jsonl")
    result = [str(row["seed_id"]) for row in rows]
    expected = [f"ST-ACT-{index:03d}" for index in range(1, 21)]
    if result != expected:
        raise RuntimeError("frozen state-tuning seed IDs changed")
    return result


def _train_count(seed_id: str) -> int:
    if seed_id in TRAIN_REDUCED_WEIGHT_TWO or seed_id == "ST-ACT-011":
        return 147
    return 148


def _dev_count(seed_id: str) -> int:
    return 20 if seed_id == "ST-ACT-013" else 16


def _refresh_oracle_digest(candidate: dict[str, Any]) -> None:
    oracle_identity = {
        "schema_version": ORACLE_SCHEMA,
        "trajectory_id": candidate["trajectory_id"],
        "source_seed_id": candidate["source_seed_id"],
        "turns": candidate["turns"],
        "prelude": candidate["prelude"],
        "expected_backend_executions": candidate["expected_backend_executions"],
    }
    candidate["private_oracle_digest"] = _digest_value(oracle_identity)


def _split_candidates(
    seed_id: str,
    split: str,
    count: int,
) -> list[dict[str, Any]]:
    seed_number = int(seed_id.rsplit("-", 1)[1])
    group_offset = 0 if split == "train" else 1_000
    split_label = "TR" if split == "train" else "DV"
    result: list[dict[str, Any]] = []
    remaining = count
    family_index = 0
    while remaining:
        family_size = min(4, remaining)
        source_group = group_offset + family_index
        semantic_family_id = (
            f"AST10K-SF-{seed_number:03d}-{split_label}-{family_index + 1:03d}"
        )
        for variant in range(family_size):
            candidate = _instantiate(seed_id, source_group, variant)
            prior_context = _semantic_family_context(
                seed_id,
                str(candidate["language"]),
                source_group,
            )
            request = str(candidate["request"])
            if not request.endswith(" " + prior_context):
                raise AssertionError("base candidate family context boundary changed")
            candidate["request"] = (
                request[: -len(prior_context)]
                + _unique_family_context(
                    seed_id,
                    split,
                    family_index,
                    str(candidate["language"]),
                )
            )
            candidate["trajectory_id"] = (
                f"AST10K-{seed_number:03d}-{split_label}-"
                f"{family_index + 1:03d}-{variant + 1:02d}"
            )
            candidate["semantic_family_id"] = semantic_family_id
            candidate["split"] = split
            _refresh_oracle_digest(candidate)
            result.append(candidate)
        remaining -= family_size
        family_index += 1
    return result


def build_candidates_10k() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for seed_id in _seed_ids():
        result.extend(_split_candidates(seed_id, "train", _train_count(seed_id)))
        result.extend(_split_candidates(seed_id, "dev", _dev_count(seed_id)))
    train = [item for item in result if item["split"] == "train"]
    dev = [item for item in result if item["split"] == "dev"]
    if len(result) != TRAJECTORY_COUNT:
        raise AssertionError(f"trajectory count {len(result)} != {TRAJECTORY_COUNT}")
    if (len(train), len(dev)) != (TRAIN_TRAJECTORY_COUNT, DEV_TRAJECTORY_COUNT):
        raise AssertionError("trajectory split count changed")
    requests = [str(item["request"]) for item in result]
    if len(requests) != len(set(requests)):
        raise AssertionError("10K candidate requests contain an exact duplicate")
    families = Counter(str(item["semantic_family_id"]) for item in result)
    if len(families) != 821 or not set(families.values()) <= {3, 4}:
        raise AssertionError("10K semantic-family structure changed")
    train_families = {
        str(item["semantic_family_id"]) for item in train
    }
    dev_families = {
        str(item["semantic_family_id"]) for item in dev
    }
    if train_families & dev_families:
        raise AssertionError("10K semantic family crosses train/dev")
    return result


def _hex_text(value: str) -> str:
    return value.encode("utf-8").hex()


def _compile_scanner(binary: Path) -> None:
    completed = subprocess.run(
        [
            "/usr/bin/g++",
            "-O3",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-pedantic",
            str(SCANNER_SOURCE),
            "-o",
            str(binary),
        ],
        cwd=ROOT,
        shell=False,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"cosine scanner compilation failed: {completed.stderr}")


def _scan_contamination_exact(
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    holdout_paths = _holdout_files()
    holdouts = _holdout_requests(holdout_paths)
    if len(holdouts) != 210:
        raise AssertionError(f"holdout request count {len(holdouts)} != 210")
    temp_root = ROOT / "temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rwkv-action-10k-cosine-",
        dir=temp_root,
    ) as temporary:
        work = Path(temporary)
        input_path = work / "requests.tsv"
        binary = work / "scan_utf8_byte_ngram_cosine"
        with input_path.open("w", encoding="ascii", newline="\n") as handle:
            for item in candidates:
                handle.write(
                    "\t".join(
                        (
                            "C",
                            str(item["trajectory_id"]),
                            str(item["semantic_family_id"]),
                            _hex_text(str(item["request"])),
                        )
                    )
                    + "\n"
                )
            for item in holdouts:
                handle.write(
                    "\t".join(("H", str(item["id"]), "-", _hex_text(item["text"])))
                    + "\n"
                )
        _compile_scanner(binary)
        completed = subprocess.run(
            [str(binary), str(input_path)],
            cwd=ROOT,
            shell=False,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"cosine scanner failed: {completed.stderr}")
    parsed: dict[str, list[str]] = {}
    for line in completed.stdout.splitlines():
        fields = line.split("\t")
        parsed[fields[0]] = fields[1:]
    candidate_count = int(parsed["candidate_count"][0])
    holdout_count = int(parsed["holdout_count"][0])
    exact_duplicates = int(parsed["exact_candidate_duplicates"][0])
    exact_holdout = int(parsed["exact_holdout_overlap"][0])
    maximum_cross = float(parsed["maximum_cross_family"][0])
    maximum_holdout = float(parsed["maximum_holdout"][0])
    if candidate_count != len(candidates) or holdout_count != len(holdouts):
        raise AssertionError("cosine scanner record count mismatch")
    if exact_duplicates or exact_holdout:
        raise AssertionError(
            f"exact duplicate/holdout overlap: internal={exact_duplicates}, holdout={exact_holdout}"
        )
    if maximum_cross >= 0.75 or maximum_holdout >= 0.75:
        raise AssertionError(
            f"cosine threshold failed: cross={maximum_cross}, holdout={maximum_holdout}"
        )
    return {
        "similarity_version": SIMILARITY_VERSION,
        "implementation": "exact-inverted-index-cpp.v1",
        "n": 5,
        "threshold_exclusive": 0.75,
        "candidate_request_count": candidate_count,
        "holdout_request_count": holdout_count,
        "internal_exact_request_duplicate_count": exact_duplicates,
        "exact_holdout_overlap_count": exact_holdout,
        "maximum_cross_semantic_family_similarity": maximum_cross,
        "nearest_cross_semantic_family": {
            "left": parsed["maximum_cross_family"][1],
            "right": parsed["maximum_cross_family"][2],
            "score": maximum_cross,
        },
        "maximum_holdout_similarity": maximum_holdout,
        "nearest_holdout": {
            "trajectory_id": parsed["maximum_holdout"][1],
            "holdout_id": parsed["maximum_holdout"][2],
            "score": maximum_holdout,
        },
        "holdout_files": {
            str(path.relative_to(ROOT)): {"sha256": _sha256(path)}
            for path in holdout_paths
        },
    }


def _jsonl_line(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True) + "\n"


def _readme(counts: Mapping[str, Any], token_stats: Mapping[str, Any]) -> str:
    return f"""# RWKV-LH Action State Tuning 10K v1

正式第一次微调数据：恰好 10,000 个经过当前 Controller/Harness 回放的 progressive G1i
监督 stage。

- official SFT：10,000（train 9,000 / dev 1,000）
- verified trajectory：{counts['trajectories']}（train {counts['train_trajectories']} / dev {counts['dev_trajectories']}）
- semantic family：{counts['semantic_families']}，train/dev overlap 为 0
- positive accepted：100%；真实联网：0；隐私后端执行：0
- token 最大值：{token_stats['max']}，建议首轮 `ctx_len=8192`

## 训练入口

- `rwkv_state_tuning.train.jsonl`：9,000 条官方 `{{"text":"..."}}`。
- `rwkv_state_tuning.dev.jsonl`：1,000 条官方 `{{"text":"..."}}`。
- `stage_sft.*.jsonl`：带 prompt/target 边界；支持 response loss mask 时优先使用。

`private/oracle_trajectories.jsonl`、`validation.jsonl` 和 `rejected_attempts.jsonl` 只用于审计，
不得拼入 train。训练前分别把 train/dev 转成 binidx；RWKV-PEFT 使用匹配部署基座的
`--peft state --op fla`。

生成与验收：

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_rwkv_action_state_tuning_10k_v1.py --validate-existing
```
"""


def generate(*, workers: int) -> dict[str, Any]:
    if OUTPUT.exists():
        raise FileExistsError(
            f"output already exists; validate it instead of overwriting: {OUTPUT}"
        )
    candidates = build_candidates_10k()
    print(
        f"built {len(candidates)} semantic trajectories; running exact contamination scan",
        flush=True,
    )
    contamination = _scan_contamination_exact(candidates)
    print(
        "contamination passed: "
        f"holdout={contamination['maximum_holdout_similarity']:.6f}, "
        f"cross_family={contamination['maximum_cross_semantic_family_similarity']:.6f}",
        flush=True,
    )

    datasets_root = ROOT / "data/datasets"
    staging = Path(
        tempfile.mkdtemp(
            prefix=".rwkv_lh_action_state_tuning_10k_v1.staging-",
            dir=datasets_root,
        )
    )
    try:
        paths = {
            "candidates": staging / "semantic_candidates.jsonl",
            "oracles": staging / "private/oracle_trajectories.jsonl",
            "validation": staging / "validation.jsonl",
            "rejected": staging / "rejected_attempts.jsonl",
            "train_stage": staging / "stage_sft.train.jsonl",
            "dev_stage": staging / "stage_sft.dev.jsonl",
            "train_rwkv": staging / "rwkv_state_tuning.train.jsonl",
            "dev_rwkv": staging / "rwkv_state_tuning.dev.jsonl",
        }
        paths["oracles"].parent.mkdir(parents=True, exist_ok=True)
        _write_jsonl(paths["candidates"], [_public_candidate(item) for item in candidates])
        _write_jsonl(paths["oracles"], [_private_oracle(item) for item in candidates])

        handles = {
            key: path.open("w", encoding="utf-8", newline="\n")
            for key, path in paths.items()
            if key not in {"candidates", "oracles"}
        }
        validations: list[dict[str, Any]] = []
        stage_counts = Counter()
        operation_counts = Counter()
        stage_kind_counts = Counter()
        text_digests: set[str] = set()
        token_counts: list[int] = []
        rejected_count = 0
        try:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                replayed = executor.map(_replay, candidates)
                for index, (candidate, replay) in enumerate(
                    zip(candidates, replayed),
                    start=1,
                ):
                    positive, validation, rejected = replay
                    validations.append(validation)
                    split = str(candidate["split"])
                    stage_handle = handles[f"{split}_stage"]
                    rwkv_handle = handles[f"{split}_rwkv"]
                    for stage in positive:
                        if stage["schema_version"] != STAGE_SCHEMA:
                            raise AssertionError("stage schema changed")
                        stage_handle.write(_jsonl_line(stage))
                        rwkv_handle.write(_jsonl_line({"text": stage["text"]}))
                        digest = hashlib.sha256(stage["text"].encode("utf-8")).hexdigest()
                        if digest in text_digests:
                            raise AssertionError("official SFT contains an exact text duplicate")
                        text_digests.add(digest)
                        stage_counts[split] += 1
                        operation_counts[str(stage["target_operation"])] += 1
                        stage_kind_counts[str(stage["stage"])] += 1
                        token_counts.append(get_token_count(str(stage["text"])))
                    for row in rejected:
                        handles["rejected"].write(_jsonl_line(row))
                        rejected_count += 1
                    if index % 100 == 0 or index == len(candidates):
                        print(
                            f"verified {index}/{len(candidates)} trajectories; "
                            f"stages={sum(stage_counts.values())}",
                            flush=True,
                        )
            for row in validations:
                handles["validation"].write(_jsonl_line(row))
        finally:
            for handle in handles.values():
                handle.close()

        if stage_counts != {"train": TRAIN_STAGE_COUNT, "dev": DEV_STAGE_COUNT}:
            raise AssertionError(f"official stage split count changed: {stage_counts}")
        if len(text_digests) != OFFICIAL_TOTAL:
            raise AssertionError("official unique-text count is not 10,000")
        if len(validations) != TRAJECTORY_COUNT or any(
            not row["accepted"] for row in validations
        ):
            raise AssertionError("not every 10K trajectory passed replay")
        privacy_backend = sum(
            int(row["backend_execution_count"])
            for row in validations
            if row["source_seed_id"] in {"ST-ACT-013", "ST-ACT-014"}
        )
        if privacy_backend:
            raise AssertionError("privacy trajectories reached the retrieval backend")

        token_counts.sort()
        token_stats = {
            "min": token_counts[0],
            "p50": token_counts[len(token_counts) // 2],
            "p95": token_counts[int(len(token_counts) * 0.95)],
            "max": token_counts[-1],
            "mean": round(sum(token_counts) / len(token_counts), 2),
        }
        train_candidates = [item for item in candidates if item["split"] == "train"]
        dev_candidates = [item for item in candidates if item["split"] == "dev"]
        family_count = len({item["semantic_family_id"] for item in candidates})
        counts = {
            "official_sft": OFFICIAL_TOTAL,
            "train_stage_sft": stage_counts["train"],
            "dev_stage_sft": stage_counts["dev"],
            "trajectories": len(candidates),
            "train_trajectories": len(train_candidates),
            "dev_trajectories": len(dev_candidates),
            "seeds": len({item["source_seed_id"] for item in candidates}),
            "semantic_families": family_count,
            "rejected_attempts": rejected_count,
        }
        readme_path = staging / "README.md"
        manifest_path = staging / "manifest.json"
        _write_text(readme_path, _readme(counts, token_stats))
        artifact_paths = [
            readme_path,
            *paths.values(),
            Path(__file__).resolve(),
            ROOT / "scripts/generate_rwkv_action_state_tuning_v1.py",
            SCANNER_SOURCE,
        ]
        manifest: dict[str, Any] = {
            "schema_version": "rwkv-lh.dataset-manifest.v1",
            "dataset_version": VERSION,
            "artifact_kind": "controller_verified_action_state_tuning_10k",
            "training_ready": True,
            "count_unit": "actual_model_generation_stage",
            "source": "Expanded current 20 action-state seeds with independent family/entity variants and fresh Controller/Harness replay.",
            "purpose": "Formal first 10,000-record RWKV-7 action state-tuning corpus.",
            "generation": "uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_rwkv_action_state_tuning_10k_v1.py",
            "factory_method_source": "/home/chase/GitHub/RWKV-state-factory",
            "factory_boundary": "method_shared; schema/verifier/renderer/similarity_not_shared",
            "candidate_generation": "deterministic_private_oracle_bootstrap",
            "strong_model_as_label_source": False,
            "controller_replay": True,
            "tool_disclosure_mode": "progressive",
            "live_network_used": False,
            "counts": counts,
            "stage_kind_counts": dict(sorted(stage_kind_counts.items())),
            "operation_counts": dict(sorted(operation_counts.items())),
            "token_stats": token_stats,
            "split": {
                "unit": "semantic_family_id",
                "train_dev_overlap_count": 0,
                "train_stage_count": TRAIN_STAGE_COUNT,
                "dev_stage_count": DEV_STAGE_COUNT,
            },
            "validation": {
                "accepted_trajectories": len(validations),
                "rejected_trajectories": 0,
                "positive_stage_parse_rate": 1.0,
                "literal_binding_rate": 1.0,
                "controller_replay_rate": 1.0,
                "official_text_exact_duplicate_count": OFFICIAL_TOTAL - len(text_digests),
                "privacy_backend_execution_count": privacy_backend,
                "contamination": contamination,
            },
            "source_files": {
                str((SEED_ROOT / name).relative_to(ROOT)): {"sha256": _sha256(SEED_ROOT / name)}
                for name in (
                    "seed_templates.jsonl",
                    "SYNTHESIS_PROMPT.md",
                    "tool_contracts.json",
                    "manifest.json",
                )
            },
            "files": {},
        }
        manifest["files"] = {
            (
                str(path.relative_to(staging))
                if path.is_relative_to(staging)
                else str(path.relative_to(ROOT))
            ): {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in artifact_paths
        }
        _write_json(manifest_path, manifest)
        staging.rename(OUTPUT)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _count_jsonl(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.strip())


def validate_existing() -> dict[str, Any]:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("dataset_version") != VERSION or manifest.get("training_ready") is not True:
        raise AssertionError("10K manifest is not training-ready v1")
    for relative, metadata in manifest["files"].items():
        path = ROOT / relative if relative.startswith("scripts/") else OUTPUT / relative
        if _sha256(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
            raise AssertionError(f"10K artifact digest/size mismatch: {relative}")
    counts = manifest["counts"]
    checks = {
        "semantic_candidates.jsonl": counts["trajectories"],
        "private/oracle_trajectories.jsonl": counts["trajectories"],
        "validation.jsonl": counts["trajectories"],
        "rejected_attempts.jsonl": counts["rejected_attempts"],
        "stage_sft.train.jsonl": TRAIN_STAGE_COUNT,
        "stage_sft.dev.jsonl": DEV_STAGE_COUNT,
        "rwkv_state_tuning.train.jsonl": TRAIN_STAGE_COUNT,
        "rwkv_state_tuning.dev.jsonl": DEV_STAGE_COUNT,
    }
    for relative, expected in checks.items():
        observed = _count_jsonl(OUTPUT / relative)
        if observed != expected:
            raise AssertionError(f"{relative} rows {observed} != {expected}")
    unique: set[str] = set()
    for relative in ("stage_sft.train.jsonl", "stage_sft.dev.jsonl"):
        for row in _read_jsonl(OUTPUT / relative):
            if row["text"] != row["prompt"] + row["target"]:
                raise AssertionError("10K stage text is not prompt + target")
            if row["stage"] == "selector":
                if parse_tool_selection(row["target"]) != row["target_operation"]:
                    raise AssertionError("10K selector target mismatch")
            elif parse_model_command(row["target"]).name != row["target_operation"]:
                raise AssertionError("10K direct target mismatch")
            unique.add(hashlib.sha256(row["text"].encode("utf-8")).hexdigest())
    if len(unique) != OFFICIAL_TOTAL:
        raise AssertionError("10K official text uniqueness failed")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-existing", action="store_true")
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, max(1, os.cpu_count() or 1)),
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        raise ValueError("--workers must be between 1 and 16")
    manifest = validate_existing() if args.validate_existing else generate(workers=args.workers)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "dataset_version": manifest["dataset_version"],
                "training_ready": manifest["training_ready"],
                "counts": manifest["counts"],
                "validation": manifest["validation"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
