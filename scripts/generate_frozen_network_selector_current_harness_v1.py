#!/usr/bin/env python3
"""Reproduce frozen S23/S24 v1 payloads after eligibility metadata was added.

The online Selector input now binds ``eligible_labels`` into its authoritative
input digest.  Frozen S23/S24 v1 predate that metadata field; it was never part
of their rendered model input.  This versioned generator delegates every
source, split, similarity and row rule to the original generators while
removing only that post-v1 serialization field.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any


ROOT = Path("/home/chase/GitHub/RWKV-LH")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FrozenV1Input:
    """Proxy current rendering while preserving the frozen v1 object shape."""

    def __init__(self, value: Any) -> None:
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        projected = dict(self.value.to_dict())
        projected.pop("eligible_labels", None)
        return projected

    def render_bootstrap(self) -> str:
        return self.value.render_bootstrap()

    def render_step(self) -> str:
        return self.value.render_step()

    def render(self) -> str:
        return self.value.render()


def _rewrite_generator_record(output: Path, dataset: str) -> None:
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    script = Path(__file__).resolve()
    record = {
        "path": str(script.relative_to(ROOT)),
        "sha256": sha256(script),
    }
    if dataset == "s23":
        record["command"] = f"uv run python {script} --dataset s23 --output {output}"
    else:
        manifest["generation"] = (
            f"uv run python {script} --dataset s24 --output {output}"
        )
    manifest["generator"] = record
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def generate(dataset: str, output: Path) -> None:
    destination = output.expanduser().resolve()
    if dataset == "s23":
        module = importlib.import_module(
            "scripts.generate_network_selector_current_harness_ecra_s23_v1"
        )
        current_builder = module.build_network_selector_input

        def frozen_builder(*args: Any, **kwargs: Any) -> FrozenV1Input:
            return FrozenV1Input(current_builder(*args, **kwargs))

        module.build_network_selector_input = frozen_builder
        module.OUTPUT = destination
        module.ROWS = destination / "decision_points.jsonl"
        module.MANIFEST = destination / "manifest.json"
        module.README = destination / "README.md"
    elif dataset == "s24":
        module = importlib.import_module(
            "scripts.generate_network_selector_current_harness_training_s24_v1"
        )
        current_input_type = module.NetworkSelectorInput

        class FrozenV1InputFactory:
            @staticmethod
            def create(*args: Any, **kwargs: Any) -> FrozenV1Input:
                return FrozenV1Input(current_input_type.create(*args, **kwargs))

        module.NetworkSelectorInput = FrozenV1InputFactory
        module.OUTPUT = destination
    else:
        raise ValueError("dataset must be s23 or s24")
    module.main()
    _rewrite_generator_record(destination, dataset)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, choices=("s23", "s24"))
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate(args.dataset, args.output)


if __name__ == "__main__":
    main()
