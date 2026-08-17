"""Create or read-only verify the frozen Round126 v19-P1 source manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/chase/GitHub/RWKV-LH")
OUTPUT = ROOT / "data/experiments/Round126_v19p1_source_manifest.json"
PROTOCOL = ROOT / "data/experiments/Round126_V19P1_BOOTSTRAP_REQUEST_LAST_ADJACENCY_PROTOCOL.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(*args: str) -> str:
    return subprocess.run(
        list(args), cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def source_paths() -> list[Path]:
    paths = [
        *(ROOT / "rwkv_lh").rglob("*.py"),
        *(ROOT / "scripts").glob("*.py"),
        *(ROOT / "tests").glob("*.py"),
        ROOT / "README.md",
        ROOT / "docs/G1I_TOOL_PROTOCOL.zh-CN.md",
        ROOT / "docs/LOCAL_WEB_UI.zh-CN.md",
        ROOT / "docs/LONG_HORIZON_AGENT_DESIGN.zh-CN.md",
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
    ]
    return sorted({path.resolve() for path in paths if path.is_file()})


def records(paths: list[Path]) -> list[dict[str, object]]:
    return [
        {
            "path": str(path.relative_to(ROOT)),
            "size_bytes": path.stat().st_size,
            "sha256": sha(path),
        }
        for path in paths
    ]


def verify(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mismatches = []
    for item in payload["source_files"] + payload["dataset_files"] + [payload["protocol"]]:
        source = ROOT / str(item["path"])
        actual = sha(source) if source.is_file() else "missing"
        if actual != item["sha256"]:
            mismatches.append(
                {"path": item["path"], "expected": item["sha256"], "actual": actual}
            )
    print(
        json.dumps(
            {
                "manifest": str(path),
                "checked": len(payload["source_files"]) + len(payload["dataset_files"]) + 1,
                "mismatches": mismatches,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if mismatches:
        raise SystemExit(1)


parser = argparse.ArgumentParser()
parser.add_argument("--check", type=Path)
arguments = parser.parse_args()
if arguments.check is not None:
    verify(arguments.check.resolve())
    raise SystemExit(0)
if OUTPUT.exists():
    raise SystemExit(f"refusing to overwrite frozen manifest: {OUTPUT}")

dataset_paths = [
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_30/acceptance.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_lh12/acceptance.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_extension48/acceptance.json",
    ROOT / "data/datasets/rwkv_e2e_90_v1/codex_reference_answers.json",
]
request = urllib.request.Request(
    "http://127.0.0.1:29610/v1/models",
    headers={"Authorization": "Bearer rwkv-skills"},
)
with urllib.request.urlopen(request, timeout=10) as response:
    endpoint = json.loads(response.read())["data"][0]

diff = subprocess.run(
    ["git", "diff", "--binary"], cwd=ROOT, check=True, capture_output=True
).stdout
status = command("git", "status", "--short", "--untracked-files=all").encode("utf-8")
source_records = records(source_paths())
ordered = "\n".join(
    f"{item['sha256']}  {item['path']}" for item in source_records
).encode("utf-8")
payload = {
    "schema_version": "rwkv-lh.experiment-source-manifest.v2",
    "experiment": "Round126 v19-P1 Bootstrap Request-Last Adjacency (immutable_request rendered as the LAST bootstrap-payload field, nearest the continuation point; sort_keys dropped; content byte-identical to R119, only key ordering changed; no per-turn re-injection)",
    "baseline": "Round119 v18-P0 (Strict 30 / FP 36 / FN 0); only rwkv_lh/model.py changes vs baseline (model_session.py restored byte-exact to R119 after R125 REVERT)",
    "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "environment": {
        "distribution": "WSL UbuntuRecovered",
        "kernel": platform.release(),
        "uv": command("/home/chase/.local/bin/uv", "--version"),
        "python": command("/home/chase/.local/bin/uv", "run", "python", "--version"),
    },
    "git": {
        "branch": command("git", "branch", "--show-current"),
        "head": command("git", "rev-parse", "HEAD"),
        "working_tree": "dirty historical tree; per-file hashes are authoritative",
        "tracked_binary_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "porcelain_status_with_untracked_sha256": hashlib.sha256(status).hexdigest(),
    },
    "protocol": {
        "path": str(PROTOCOL.relative_to(ROOT)),
        "size_bytes": PROTOCOL.stat().st_size,
        "sha256": sha(PROTOCOL),
    },
    "architecture": {
        "run_schema": "long-horizon.run.v18",
        "causal_event_schema": "rwkv-lh.causal-event.v2",
        "online_semantic_lanes": ["LANE:ACTION"],
        "direct_registered_operations": 17,
        "terminal_operation": "final_answer",
        "online_task_graph": False,
        "reviewer": False,
        "sampling_policy": {
            "version": "r119-byte-exact (unchanged this round)",
            "default": {"temperature": 0.05, "top_p": 1.0, "top_k": 0},
            "seed_supported": False,
        },
        "bootstrap_request_last": {
            "version": "request-last-adjacency.v1",
            "change": "_assignment payload key order = protocol, constraints, workspace_manifest, recent_exact_action_records, instruction, immutable_request (LAST); json.dumps without sort_keys",
            "persisted": True,
            "per_turn_reinjection": False,
            "token_delta_vs_R119": 0,
            "second_decision_added": False,
            "task_text_parsed": False,
            "hidden_acceptance_read": False,
        },
        "prompt_render_changed_vs_baseline": "bootstrap/rollover payload key ordering only (same content bytes); append chain unchanged",
        "transport": "prompt_replay",
    },
    "offline_verification": {
        "pytest": "107 passed",
        "e2e_catalog": {"selected": 90, "total": 90, "catalog_valid": True},
        "compileall": "passed",
        "changed_files_vs_R119": ["rwkv_lh/model.py"],
        "render_smoke": "immutable_request confirmed as last content before the Assistant continuation marker; sort_keys removed (protocol precedes constraints)",
    },
    "source_bundle_sha256": hashlib.sha256(ordered).hexdigest(),
    "source_files": source_records,
    "dataset_files": records(dataset_paths),
    "endpoint": {
        "url": "http://127.0.0.1:29610/v1/models",
        "model": endpoint["id"],
        "owner": endpoint["owned_by"],
        "max_model_len": endpoint["max_model_len"],
    },
    "outputs": {
        "official": "data/experiments/Round126_v19p1_full90",
    },
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
