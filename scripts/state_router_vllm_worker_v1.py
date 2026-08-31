"""Run State Router feature extraction inside the local vllm-rwkv runtime."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REQUEST_SCHEMA = "rwkv-lh.state-router-vllm-worker-request.v1"
RESPONSE_SCHEMA = "rwkv-lh.state-router-vllm-worker-response.v1"


def _extract_with_model(
    model: Any,
    operation: str,
    token_rows: list[list[int]],
    batch_size: int,
    layer_index: int,
    code_token_ids: list[int],
) -> dict[str, Any]:
    import torch

    required = ("zero_state", "forward_all_hidden", "project_logits_fp32")
    missing = [name for name in required if not callable(getattr(model, name, None))]
    if missing:
        raise RuntimeError(f"local vllm-rwkv model lacks direct APIs: {missing}")
    if not token_rows or any(not row for row in token_rows):
        raise ValueError("local vllm-rwkv token rows must be non-empty")

    layer_count = int(model.total_num_layers)
    resolved_layer = layer_index if layer_index >= 0 else layer_count + layer_index
    if not 0 <= resolved_layer < layer_count:
        raise ValueError("WKV layer index is outside the local vllm-rwkv model")
    buckets: dict[int, list[int]] = defaultdict(list)
    for index, row in enumerate(token_rows):
        buckets[len(row)].append(index)
    rows: list[Any | None] = [None] * len(token_rows)
    with torch.inference_mode():
        for token_count in sorted(buckets):
            indices = buckets[token_count]
            for start in range(0, len(indices), batch_size):
                batch_indices = indices[start : start + batch_size]
                tokens = torch.tensor(
                    [token_rows[index] for index in batch_indices],
                    dtype=torch.long,
                    device="cuda",
                )
                state = model.zero_state(len(batch_indices))
                hidden = model.forward_all_hidden(tokens, state)
                if operation == "hidden_mean":
                    values = hidden.float().mean(dim=1)
                elif operation == "wkv_statistics":
                    recurrent = state[1][resolved_layer].float()
                    values = torch.cat(
                        (
                            recurrent.mean(dim=-1).flatten(1),
                            recurrent.mean(dim=-2).flatten(1),
                            recurrent.diagonal(dim1=-2, dim2=-1).flatten(1),
                            recurrent.square().mean(dim=-1).sqrt().flatten(1),
                        ),
                        dim=1,
                    )
                elif operation == "code_logits":
                    logits = model.project_logits_fp32(hidden[:, -1, :])
                    code_index = torch.tensor(
                        code_token_ids, dtype=torch.long, device=logits.device
                    )
                    values = logits.index_select(1, code_index).float()
                else:
                    raise ValueError(f"unsupported vllm-rwkv operation: {operation}")
                values = values.detach().float().cpu()
                for local_index, source_index in enumerate(batch_indices):
                    rows[source_index] = values[local_index]
    if any(row is None for row in rows):
        raise RuntimeError("local vllm-rwkv extraction left unfilled rows")
    stacked = torch.stack(rows)
    profile = model.execution_profile
    return {
        "features": stacked.numpy(),
        "runtime": {
            "model_class": type(model).__name__,
            "hidden_size": int(model.hidden_size),
            "num_hidden_layers": layer_count,
            "head_size": int(model.head_size),
            "vocab_size": int(model.vocab_size),
            "wkv_mode": str(profile.wkv_mode),
            "wkv_state_dtype": str(profile.wkv_state_dtype),
            "gemm_accumulation_policy": str(profile.gemm_accumulation_policy),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "device": torch.cuda.get_device_name(),
            "cuda_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
            "cuda_peak_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        },
    }


def _load_direct_model(model_path: Path) -> Any:
    import torch
    from safetensors import safe_open
    from vllm.config.compilation import CompilationConfig, CompilationMode
    from vllm.config.vllm import set_current_vllm_config
    from vllm.model_executor.models import rwkv7
    from vllm.model_executor.models.rwkv7 import RWKV7ForCausalLM
    from vllm.transformers_utils.configs.rwkv7 import RWKV7Config

    config_values = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
    config = RWKV7Config(**config_values)
    rwkv7.get_tensor_model_parallel_world_size = lambda: 1
    rwkv7.get_tensor_model_parallel_rank = lambda: 0
    model_config = SimpleNamespace(
        hf_config=config,
        enforce_eager=True,
        dtype=torch.float16,
        head_dtype=None,
    )
    vllm_config = SimpleNamespace(
        compilation_config=CompilationConfig(mode=CompilationMode.NONE),
        model_config=model_config,
        quant_config=None,
        parallel_config=None,
    )
    with set_current_vllm_config(vllm_config):
        model = RWKV7ForCausalLM(vllm_config=vllm_config)
    weights_path = model_path / "model.safetensors"
    with safe_open(weights_path, framework="pt", device="cpu") as weights:
        loaded = model.load_weights(
            (name, weights.get_tensor(name)) for name in weights.keys()
        )
    if len(loaded) != 795:
        raise RuntimeError(f"local vllm-rwkv loaded {len(loaded)} weights, expected 795")
    model.eval()
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if request.get("schema_version") != REQUEST_SCHEMA:
        raise ValueError("unsupported local vllm-rwkv worker request")
    engine_root = Path(request["engine_root"]).resolve()
    model_path = Path(request["model_path"]).resolve()
    runtime_temp = Path(request["runtime_temp"]).resolve()
    if Path.cwd().resolve() != engine_root:
        raise RuntimeError("local vllm-rwkv worker must run from its source root")
    runtime_temp.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(runtime_temp)
    os.environ["TEMP"] = str(runtime_temp)
    os.environ["TMP"] = str(runtime_temp)
    os.environ.setdefault("VLLM_ALLOW_INSECURE_SERIALIZATION", "1")
    os.environ.setdefault("VLLM_USE_V2_MODEL_RUNNER", "1")
    os.environ["VLLM_RWKV7_WKV_MODE"] = str(request["wkv_mode"])

    import numpy as np
    import torch
    import transformers
    import vllm
    import vllm.rwkv7_ops  # noqa: F401
    from vllm.tokenizers.rwkv import RWKVTokenizer

    vllm_source = Path(vllm.__file__).resolve()
    if not vllm_source.is_relative_to(engine_root):
        raise RuntimeError(
            f"vllm resolved outside the required local source tree: {vllm_source}"
        )
    texts = [str(text) for text in request["texts"]]
    if not texts or any(not text.strip() for text in texts):
        raise ValueError("local vllm-rwkv extraction texts must be non-empty")
    max_tokens = int(request["max_tokens"])
    tokenizer = RWKVTokenizer.from_pretrained(model_path)
    token_rows = [
        tokenizer.encode(
            text,
            truncation=True,
            max_length=max_tokens,
            add_special_tokens=True,
        )
        for text in texts
    ]
    codes = [str(code) for code in request.get("codes") or []]
    code_token_ids: list[int] = []
    for code in codes:
        encoded = tokenizer.encode(f" {code}", add_special_tokens=False)
        if len(encoded) != 1:
            raise ValueError(f"constrained code is not one RWKV token: {code!r}")
        code_token_ids.append(int(encoded[0]))

    batch_size = int(request["batch_size"])
    torch.cuda.reset_peak_memory_stats()
    model = _load_direct_model(model_path)
    result = _extract_with_model(
        model,
        str(request["operation"]),
        token_rows,
        batch_size,
        int(request.get("layer_index", -1)),
        code_token_ids,
    )
    features = np.asarray(result["features"], dtype=np.float32)
    if features.ndim != 2 or features.shape[0] != len(texts):
        raise RuntimeError("local vllm-rwkv returned an invalid feature matrix")
    response = {
        "schema_version": RESPONSE_SCHEMA,
        "operation": request["operation"],
        "rows": len(texts),
        "feature_shape": list(features.shape),
        "token_counts": [len(row) for row in token_rows],
        "tokenizer": {
            "class": type(tokenizer).__name__,
            "vocab_size": tokenizer.vocab_size,
            "bos_token_id": tokenizer.bos_token_id,
            "eos_token_id": tokenizer.eos_token_id,
            "pad_token_id": tokenizer.pad_token_id,
            "truncation_side": tokenizer.truncation_side,
        },
        "runtime": {
            **result["runtime"],
            "runtime_temp": str(runtime_temp),
            "vllm_module": str(vllm_source),
            "vllm_version": vllm.__version__,
            "transformers_version": transformers.__version__,
        },
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pending_npz = output.with_suffix(output.suffix + ".pending")
    with pending_npz.open("wb") as stream:
        np.savez_compressed(stream, features=features)
    os.replace(pending_npz, output)
    response_path = output.with_suffix(output.suffix + ".json")
    pending_response = response_path.with_suffix(response_path.suffix + ".pending")
    pending_response.write_text(
        json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending_response, response_path)


if __name__ == "__main__":
    main()
