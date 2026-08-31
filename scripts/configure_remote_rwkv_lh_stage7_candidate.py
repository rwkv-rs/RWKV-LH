"""Atomically configure and optionally start one Stage7 vLLM candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


RUN = Path(
    "/home/chase/chase/RWKV-PEFT/out/"
    "g1i-13.3b-rwkv-lh-stage7-factory-contrast2000-cont-stage4-lr3e-6-seed833"
)
ENV = Path("/home/chase/.config/rwkv-lh-stage7-candidate.env")
SERVICE = "helicopter-vllm-g1i-13p3b-rwkv-lh-stage7-candidate-gpu0.service"
TRAINING_SERVICE = "rwkv-lh-stage7-factory-contrast-state-tuning.service"
STEPS = (500, 1000, 1500, 2000)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def active(service: str) -> bool:
    return (
        subprocess.run(
            ["systemctl", "--user", "is-active", "--quiet", service], check=False
        ).returncode
        == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, choices=STEPS, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()
    checkpoint = RUN / f"rwkv-step-{args.step}.pth"
    if not checkpoint.is_file() or sha256(checkpoint) != args.sha256:
        raise SystemExit("candidate checkpoint digest mismatch")
    served_model = f"rwkv7-g1i-13.3b-rwkv-lh-stage7-step{args.step}-bos-ctx2496"
    candidate_dir = RUN / f"candidate-step{args.step}"
    candidate_dir.mkdir(exist_ok=True)
    values = {
        "VLLM_RWKV7_INITIAL_STATE_PATH": str(checkpoint),
        "VLLM_RWKV7_INITIAL_STATE_SHA256": args.sha256,
        "VLLM_RWKV7_ATTESTATION_PATH": str(
            candidate_dir / "vllm_state_attestation.jsonl"
        ),
        "RWKV_LH_VLLM_PREFLIGHT_REPORT": str(candidate_dir / "vllm_preflight.json"),
        "RWKV_LH_SERVED_MODEL": served_model,
    }
    temporary = ENV.with_suffix(".env.tmp")
    temporary.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(ENV)
    result = {
        "schema_version": "rwkv-lh.stage7-candidate-deployment.v1",
        "configured_at": datetime.now().astimezone().isoformat(),
        "step": args.step,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": args.sha256,
        "served_model": served_model,
        "service": SERVICE,
        "started": False,
    }
    if args.start:
        if active(TRAINING_SERVICE):
            raise SystemExit("refusing to interrupt active Stage7 training")
        subprocess.run(["systemctl", "--user", "restart", SERVICE], check=True)
        result["started"] = True
    (candidate_dir / "deployment.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
