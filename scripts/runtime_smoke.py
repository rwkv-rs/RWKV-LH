"""Check the configured OpenAI-compatible RWKV endpoint."""

from __future__ import annotations

import argparse
import json

from rwkv_lh.runtime import OpenAICompatibleRWKVClient, sampling_parameters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the RWKV runtime connection")
    parser.add_argument(
        "--completion",
        action="store_true",
        help="Also issue one short text completion after the health check",
    )
    parser.add_argument("--temperature", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=1)
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
        with sampling_parameters(arguments.temperature, seed=arguments.seed):
            response = client.text_completion(
                prompt,
                max_tokens=max(1, arguments.max_tokens),
                stop=["### User"],
            )
        result["completion"] = {
            "temperature": arguments.temperature,
            "seed": arguments.seed,
            "content": response.content,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
            "latency_ms": response.latency_ms,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if health.available else 2


if __name__ == "__main__":
    raise SystemExit(main())
