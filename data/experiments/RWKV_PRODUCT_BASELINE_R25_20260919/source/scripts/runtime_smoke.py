"""Check the configured OpenAI-compatible RWKV endpoint."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from rwkv_lh.runtime import (
    OpenAICompatibleRWKVClient,
    get_request_sampling,
    sampling_parameters,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the RWKV runtime connection")
    parser.add_argument(
        "--completion",
        action="store_true",
        help="Also issue one short text completion after the health check",
    )
    parser.add_argument("--temperature", type=float, default=0.03)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--presence-penalty", type=float, default=None)
    parser.add_argument("--frequency-penalty", type=float, default=None)
    parser.add_argument("--penalty-decay", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=64)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    client = OpenAICompatibleRWKVClient()
    health = client.health()
    result: dict[str, object] = {"health": health.to_dict()}
    if health.available and arguments.completion:
        prompt = (
            "### User\nReturn only a JSON object with key ok and boolean true.\n"
            "### Assistant\n```json\n{"
        )
        with sampling_parameters(
            arguments.temperature,
            top_p=arguments.top_p,
            top_k=arguments.top_k,
            presence_penalty=arguments.presence_penalty,
            frequency_penalty=arguments.frequency_penalty,
            penalty_decay=arguments.penalty_decay,
        ):
            sampling = get_request_sampling()
            response = client.text_completion(
                prompt,
                max_tokens=max(1, arguments.max_tokens),
                stop=["### User"],
            )
        result["completion"] = {
            "sampling": asdict(sampling),
            "content": response.content,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
            "latency_ms": response.latency_ms,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if health.available else 2


if __name__ == "__main__":
    raise SystemExit(main())
