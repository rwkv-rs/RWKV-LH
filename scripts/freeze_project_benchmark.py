"""Compile authored project contracts into a fixed development evaluation suite.

This packages existing task briefs and private graders; it does not generate
scenarios or role training examples. Authoring a dataset requires owner approval.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path

from rwkv_lh.goal_state_protocols import (
    auditor_final,
    auditor_step_v5,
    executor_args_v5,
    finalizer_answer,
    selector_intent_v5,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shingles(value: str) -> Counter[bytes]:
    data = value.encode("utf-8")
    return Counter(data[index:index + 5] for index in range(max(0, len(data) - 4)))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def freeze(dataset: Path, package: Path, *, source_run: str) -> dict:
    tasks = []
    cases = {}
    sources = []
    families = []
    similarity_inputs = {}
    for path in sorted(dataset.glob("*/RP-*/task.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        task_id = task["task_id"]
        if task_id in cases or path.parent.name != task_id:
            raise ValueError(f"duplicate or mismatched task identity: {task_id}")
        verifier = path.with_name("private_verify.py")
        program = verifier.read_bytes().decode("utf-8")
        compile(program, str(verifier), "exec")
        tasks.append(task)
        cases[task_id] = {
            "runner_control": {"network_policy": "offline"},
            "checks": [{
                "kind": "project_behavior",
                "program": program,
                "program_sha256": digest(verifier),
                "timeout": 120,
                "browser": task_id.startswith(("RP-WEB-", "RP-FULL-")),
            }],
        }
        families.append({"task_id": task_id, "family_id": task_id, "group": path.parent.parent.name,
                         "capabilities": task["capabilities"]})
        similarity_inputs[task_id] = shingles(task["user_request"] + "\n" + "\n".join(
            item["content"] for item in task["workspace_files"] if item["path"].endswith(".md")
        ))
        for source in sorted(path.parent.rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts and source.suffix != ".pyc":
                sources.append({"path": source.relative_to(dataset).as_posix(),
                                "bytes": source.stat().st_size, "sha256": digest(source)})
    if len(tasks) != 12:
        raise ValueError(f"expected twelve authored task contracts, found {len(tasks)}")
    pairs = []
    for first, second in combinations(sorted(similarity_inputs), 2):
        a, b = similarity_inputs[first], similarity_inputs[second]
        denominator = math.sqrt(sum(value * value for value in a.values()) * sum(value * value for value in b.values()))
        score = sum(value * b.get(key, 0) for key, value in a.items()) / denominator if denominator else 1.0
        pairs.append({"first": first, "second": second, "cosine": score})
    flagged = [pair for pair in pairs if pair["cosine"] >= 0.95]
    if flagged:
        raise ValueError(f"near-duplicate public briefs require review before freezing: {flagged}")
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text('"""Owner-authorized real project development benchmark."""\n', encoding="utf-8")
    write_json(package / "tasks.json", {"schema_version": "rwkv-real-project-dev-v1.tasks.v1", "tasks": tasks})
    write_json(package / "acceptance.json", {"schema_version": "rwkv-real-project-dev-v1.acceptance.v1", "cases": cases})
    manifest = {
        "schema_version": "rwkv-lh.project-development-dataset-manifest.v1",
        "source": "owner-authorized authored development benchmark; not collected real-user production tasks",
        "owner_authorization": "先补齐真实项目任务和验收，再全面测试（推荐）",
        "source_run": source_run,
        "generator": {"path": "scripts/freeze_project_benchmark.py", "sha256": digest(Path(__file__))},
        "role_protocol_modules": [{"module": module.__name__, "sha256": digest(Path(module.__file__))}
                                  for module in (executor_args_v5, selector_intent_v5, auditor_step_v5,
                                                 finalizer_answer, auditor_final)],
        "split_algorithm": "all twelve distinct task families fixed as development evaluation; no training, confirmation or holdout split created",
        "similarity": {"algorithm": "UTF-8 byte 5-gram cosine of public request + Markdown contract",
                       "normalization": "none; exact UTF-8 bytes and occurrence counts",
                       "near_duplicate_threshold": 0.95, "pairs": pairs, "flagged_pairs": flagged},
        "coverage_audit": {"count": len(tasks), "task_families": families,
                           "categories": {name: 2 for name in ("CLI", "DATA", "API", "MAINT", "WEB", "FULL")},
                           "grading": "black-box execution, real browser for Web/fullstack, persistence/restart and failure boundaries",
                           "limitations": "development sample, twelve families; no external network or large repository tasks; not exhaustive Agent capability coverage"},
        "agent_visibility": "task.json public fields only; private programs, references and mutations excluded from workspace seeds",
        "role_training_samples": 0,
        "files": sources,
        "compiled_resources": [{"path": path.name, "sha256": digest(path)}
                               for path in (package / "tasks.json", package / "acceptance.json")],
    }
    write_json(dataset / "MANIFEST.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--source-run", required=True)
    args = parser.parse_args()
    manifest = freeze(args.dataset.resolve(strict=True), args.package.resolve(), source_run=args.source_run)
    print(json.dumps({"tasks": manifest["coverage_audit"]["count"], "manifest_sha256": digest(args.dataset / "MANIFEST.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
