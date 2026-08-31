"""Run the advisory State Router entirely inside the local RWKV-LH process."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rwkv_lh.state_router.local_backend import (
    DEFAULT_ROUTER_MODEL,
    DEFAULT_VLLM_RWKV_PYTHON,
    DEFAULT_VLLM_RWKV_REVISION,
    DEFAULT_VLLM_RWKV_ROOT,
    LocalVLLMRWKVExtractor,
    LocalVLLMRWKVSettings,
)
from rwkv_lh.state_router.model import MultiHeadMLPArtifact, StateRouter
from rwkv_lh.state_router.protocol import RouterInput
from rwkv_lh.state_router.wkv_projection import ProjectedWKVExtractor


def read_inputs(path: str) -> list[RouterInput]:
    stream = sys.stdin if path == "-" else Path(path).open("r", encoding="utf-8")
    try:
        values = [
            json.loads(line)
            for line in stream
            if line.strip()
        ]
    finally:
        if stream is not sys.stdin:
            stream.close()
    inputs: list[RouterInput] = []
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("each Router input line must be a JSON object")
        nested = value.get("input")
        inputs.append(
            RouterInput.from_dict(nested if isinstance(nested, dict) else value)
        )
    return inputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument(
        "--projection",
        type=Path,
        help="train-only WKV PCA artifact required by a scheme-B head",
    )
    parser.add_argument("--input-jsonl", default="-")
    parser.add_argument("--model", type=Path, default=DEFAULT_ROUTER_MODEL)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_VLLM_RWKV_ROOT)
    parser.add_argument("--engine-revision", default=DEFAULT_VLLM_RWKV_REVISION)
    parser.add_argument("--engine-python", type=Path, default=DEFAULT_VLLM_RWKV_PYTHON)
    parser.add_argument("--wkv-mode", choices=("fp16", "fp32io16"), default="fp16")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args()

    artifact = MultiHeadMLPArtifact.load(args.head)
    base_extractor = LocalVLLMRWKVExtractor(
        LocalVLLMRWKVSettings(
            model=args.model,
            engine_root=args.engine_root,
            engine_revision=args.engine_revision,
            engine_python=args.engine_python,
            batch_size=args.batch_size,
            max_tokens=args.max_tokens,
            wkv_mode=args.wkv_mode,
        )
    )
    scheme = str(artifact.metadata.get("scheme") or "")
    if scheme == "B" and args.projection is None:
        parser.error("--projection is required by the selected scheme-B Router head")
    if args.projection is not None:
        if scheme != "B":
            parser.error("--projection can only be used with a scheme-B Router head")
        extractor = ProjectedWKVExtractor(
            base_extractor,
            args.projection,
            expected_model_hash=artifact.model_hash,
            expected_projection_digest=str(
                artifact.metadata.get("projection_digest") or ""
            ),
            expected_projection_sha256=str(
                artifact.metadata.get("projection_sha256") or ""
            ),
        )
    else:
        extractor = base_extractor
    router = StateRouter(extractor, artifact)
    for output in router.route_many(read_inputs(args.input_jsonl)):
        print(json.dumps(output.to_dict(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
