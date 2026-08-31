"""Freeze the exact RWKV-LH files used by the Stage-1 Shadow canary."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "data/experiments/STATE_ROUTER_STAGE1_SHADOW_V1_20260827"
    / "FROZEN_CODE_MANIFEST.json"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_files() -> list[Path]:
    paths = set((ROOT / "rwkv_lh").rglob("*.py"))
    paths.update((ROOT / "rwkv_lh/web_assets").glob("*"))
    paths.update(
        {
            ROOT / "pyproject.toml",
            ROOT / "uv.lock",
            ROOT / "scripts/freeze_state_router_shadow_v1.py",
            ROOT / "scripts/run_local_state_router.py",
            ROOT / "scripts/run_long_horizon.py",
            ROOT / "scripts/run_state_router_shadow_canary_v1.py",
            ROOT / "scripts/state_router_vllm_worker_v1.py",
            ROOT / "tests/test_long_horizon_cli.py",
            ROOT / "tests/test_retrieval_kernel.py",
            ROOT / "tests/test_state_router_shadow.py",
            ROOT / "tests/test_web_ui.py",
            ROOT / "data/datasets/rwkv_lh_state_router_shadow_canary_v1/README.md",
            ROOT / "data/datasets/rwkv_lh_state_router_shadow_canary_v1/cases.json",
            ROOT / "data/datasets/rwkv_lh_state_router_shadow_canary_v1/manifest.json",
            ROOT
            / "data/experiments/STATE_ROUTER_STAGE1_SHADOW_V1_20260827"
            / "PREREGISTRATION.md",
            ROOT
            / "data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827"
            / "state_router_head.json",
            ROOT
            / "data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827"
            / "projection.train_only.pt",
            ROOT / "data/models/rwkv7-0.4b-g1-vllm-v1/manifest.json",
            ROOT / "data/models/rwkv7-0.4b-g1-vllm-v1/config.json",
        }
    )
    missing = sorted(str(path) for path in paths if not path.is_file())
    if missing:
        raise RuntimeError(f"missing frozen implementation files: {missing}")
    return sorted(paths)


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite frozen manifest: {OUTPUT}")
    files = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in selected_files()
    ]
    payload = {
        "schema_version": "rwkv-lh.frozen-code-manifest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "purpose": "Exact Stage-1 Shadow implementation and real-Controller canary input freeze",
        "selection": (
            "all rwkv_lh Python/runtime web assets plus explicit Shadow entrypoints, tests, "
            "dataset, preregistration, selected Stage-0 head/PCA, and Router model metadata"
        ),
        "files": files,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT.with_name(f".{OUTPUT.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, OUTPUT)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "file_count": len(files),
                "sha256": file_sha256(OUTPUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
