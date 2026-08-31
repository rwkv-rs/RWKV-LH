#!/usr/bin/env python3
"""Generate S39 by enabling every variant inside each S38 source split."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path("/home/chase/GitHub/RWKV-LH")
BASE = ROOT / "scripts/generate_network_selector_matched_prefix_s38_v1.py"
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S39_FULL_VARIANT_MATCHED_PREFIX_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_full_variant_matched_prefix_s39_v1"

BASE_SHA256 = "dc7629016694a61a0be7c16827b872d178dbe0882269474f8b9d86b995c82752"
PREREGISTRATION_SHA256 = "79240a388a70e5a90e06568f3e187665f5cf2c8e0a29ea16aadbde58e11b50ea"
VERSION = "rwkv-lh.network-selector.full-variant-matched-prefix-s39.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-full-variant-matched-prefix-row.s39.v1"
OPAQUE_ID = re.compile(r"^S39-[PT]-[0-9a-f]{24}$")
ALL_VARIANTS = (0, 1, 2, 3, 4, 5)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_base() -> ModuleType:
    if sha256_file(BASE) != BASE_SHA256:
        raise RuntimeError("S39 frozen S38 generator dependency changed")
    spec = importlib.util.spec_from_file_location(
        "rwkv_lh_s39_frozen_s38_generator", BASE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load frozen S38 generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def opaque_id(kind: str, *parts: object) -> str:
    digest = hashlib.sha256(
        "|".join(["S39", kind, *(str(part) for part in parts)]).encode("utf-8")
    ).hexdigest()[:24]
    return f"S39-{kind}-{digest}"


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S39 dataset")
    module = load_base()
    original_load_s30 = module.load_base

    def full_variant_s30() -> ModuleType:
        s30 = original_load_s30()
        s30.VARIANTS = {
            "train": ALL_VARIANTS,
            "dev": ALL_VARIANTS,
            "test": ALL_VARIANTS,
        }
        return s30

    module.load_base = full_variant_s30
    module.PREREGISTRATION = PREREGISTRATION
    module.PREREGISTRATION_SHA256 = PREREGISTRATION_SHA256
    module.OUTPUT = OUTPUT
    module.VERSION = VERSION
    module.ROW_SCHEMA = ROW_SCHEMA
    module.OPAQUE_ID = OPAQUE_ID
    module.opaque_id = opaque_id
    module.main()

    manifest_path = OUTPUT / "manifest.json"
    cases_path = OUTPUT / "cases.jsonl"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("dataset_version") != VERSION
        or manifest.get("files", {}).get("cases.jsonl", {}).get("rows") != 5142
        or manifest.get("validation", {}).get("prefix_counts")
        != {"train": 3428, "dev": 857, "test": 857}
        or manifest.get("validation", {}).get("trajectory_counts")
        != {"train": 2000, "dev": 500, "test": 500}
        or sha256_file(cases_path)
        != manifest["files"]["cases.jsonl"]["sha256"]
    ):
        raise RuntimeError("S39 generated dataset identity changed")
    manifest.update(
        {
            "schema_version": "rwkv-lh.dataset-manifest.s39.v1",
            "purpose": (
                "full-variant, source-split-separated, depth-matched prefix "
                "supervision for the current direct Selector architecture"
            ),
            "generation_method": (
                "reuse the frozen S38 matched-depth/source-split generator "
                "while making all six contract variants eligible inside each "
                "already isolated source pool"
            ),
            "eligible_contract_variants_by_split": {
                "train": list(ALL_VARIANTS),
                "dev": list(ALL_VARIANTS),
                "test": list(ALL_VARIANTS),
            },
            "generator": {
                "path": str(Path(__file__).resolve().relative_to(ROOT)),
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "frozen_s38_generator_dependency": {
                "path": str(BASE.relative_to(ROOT)),
                "sha256": BASE_SHA256,
            },
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "README.md").write_text(
        "# S39 full-variant matched-prefix Selector dataset\n\n"
        "This dataset keeps S38's split-separated sources and exactly matched "
        "depth distributions while making all six operation-contract variants "
        "eligible inside each source split. It contains 2,000/500/500 base "
        "trajectories and every callable prefix. Full provenance and hashes are "
        "recorded in `manifest.json`.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "event": "s39_full_variant_matched_prefix_dataset_finalized",
                "prefix_rows": 5142,
                "cases_sha256": sha256_file(cases_path),
                "manifest_sha256": sha256_file(manifest_path),
                "eligible_variants": list(ALL_VARIANTS),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
