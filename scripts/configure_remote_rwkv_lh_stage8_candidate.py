"""Fail-closed configuration for one Stage8 three-round vLLM state candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


PROJECT = Path("/home/chase/chase/RWKV-PEFT").resolve()
RUN_ROOT = (PROJECT / "out").resolve()
ENV = Path("/home/chase/.config/rwkv-lh-stage7-candidate.env")
SERVICE = "helicopter-vllm-g1i-13p3b-rwkv-lh-stage7-candidate-gpu0.service"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--served-model", required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    candidate_dir = args.candidate_dir.resolve()
    if RUN_ROOT not in checkpoint.parents or not checkpoint.is_file():
        raise SystemExit("checkpoint must be an existing RWKV-PEFT/out artifact")
    if RUN_ROOT not in candidate_dir.parents:
        raise SystemExit("candidate directory must remain under RWKV-PEFT/out")
    if sha256(checkpoint) != args.sha256:
        raise SystemExit("candidate checkpoint digest mismatch")
    if not checkpoint.name.endswith(".vllm.pth"):
        raise SystemExit("Stage8 deployment requires the explicit vLLM state export")
    sidecar = checkpoint.with_suffix(".json")
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    if not (
        metadata.get("format") == "rwkv7-state-tuning-v2"
        and metadata.get("num_layers") == 61
        and metadata.get("training_layout") == "[head,value,key]"
        and metadata.get("vllm_layout") == "[head,value,key]"
        and metadata.get("conversion") == "identity"
    ):
        raise SystemExit("vLLM state metadata contract failed")
    if not args.served_model.startswith("rwkv7-g1i-13.3b-rwkv-lh-stage8-"):
        raise SystemExit("unexpected served model name")

    candidate_dir.mkdir(parents=True, exist_ok=True)
    values = {
        "VLLM_RWKV7_INITIAL_STATE_PATH": str(checkpoint),
        "VLLM_RWKV7_INITIAL_STATE_SHA256": args.sha256,
        "VLLM_RWKV7_ATTESTATION_PATH": str(
            candidate_dir / "vllm_state_attestation.jsonl"
        ),
        "RWKV_LH_VLLM_PREFLIGHT_REPORT": str(
            candidate_dir / "vllm_preflight.json"
        ),
        "RWKV_LH_SERVED_MODEL": args.served_model,
    }
    temporary = ENV.with_name(ENV.name + ".tmp")
    temporary.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(ENV)
    result = {
        "schema_version": "rwkv-lh.stage8-candidate-deployment.v1",
        "configured_at": datetime.now().astimezone().isoformat(),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": args.sha256,
        "state_metadata": metadata,
        "served_model": args.served_model,
        "service": SERVICE,
        "started": False,
    }
    if args.start:
        subprocess.run(["systemctl", "--user", "restart", SERVICE], check=True)
        result["started"] = True
    (candidate_dir / "deployment.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
