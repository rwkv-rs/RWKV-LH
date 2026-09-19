#!/usr/bin/env python3
"""Apply the audited state-profile overlay to the server's exact vLLM tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


EXPECTED_ENVS_SHA256 = "5b951d7bcea4ff5c0c4e4c0c7a83d8e21d12a99e194fee2007202f53e388c86c"
EXPECTED_RWKV_STATE_SHA256 = (
    "24dc28626ee34b2e93231b67a72dce9c20ac765ede5194c053b39d743ac47c3a"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source marker, found {count}")
    return text.replace(old, new, 1)


def _patch_envs(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '    VLLM_RWKV7_WKV_MODE: str = "fp16"\n',
        '    VLLM_RWKV7_WKV_MODE: str = "fp16"\n'
        "    VLLM_RWKV7_STATE_PROFILE_MANIFEST: str | None = None\n"
        "    VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256: str | None = None\n",
        label="env type declarations",
    )
    text = _replace_once(
        text,
        '    "VLLM_RWKV7_WKV_MODE": lambda: os.getenv("VLLM_RWKV7_WKV_MODE", "fp16"),\n',
        '    "VLLM_RWKV7_WKV_MODE": lambda: os.getenv("VLLM_RWKV7_WKV_MODE", "fp16"),\n'
        '    "VLLM_RWKV7_STATE_PROFILE_MANIFEST": lambda: os.getenv(\n'
        '        "VLLM_RWKV7_STATE_PROFILE_MANIFEST"\n'
        "    ),\n"
        '    "VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256": lambda: os.getenv(\n'
        '        "VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256"\n'
        "    ),\n",
        label="env runtime registrations",
    )
    path.write_text(text, encoding="utf-8")


def _patch_rwkv_state(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "import torch\nimport torch.nn as nn\n\nfrom vllm.config import VllmConfig\n",
        "import torch\nimport torch.nn as nn\n\n"
        "from vllm import envs\n"
        "from vllm.config import VllmConfig\n",
        label="vllm env import",
    )
    text = _replace_once(
        text,
        "from vllm.v1.worker.gpu.model_states.interface import ModelState\n",
        "from vllm.v1.worker.gpu.model_states.interface import ModelState\n"
        "from vllm.v1.worker.gpu.model_states.vllm_rwkv_state_profiles_v1 import (\n"
        "    RWKV7InitialStateProfile,\n"
        "    RWKV7InitialStateProfiles,\n"
        "    resolve_request_profile,\n"
        ")\n",
        label="state-profile import",
    )
    text = _replace_once(
        text,
        "        self._prefill_req_slots: list[int] = []\n"
        "        self._prefill_becomes_decode: list[bool] = []\n",
        "        self._prefill_req_slots: list[int] = []\n"
        "        self._prefill_becomes_decode: list[bool] = []\n"
        "        self.req_state_profile_ids: dict[str, str] = {}\n\n"
        "        manifest_path = envs.VLLM_RWKV7_STATE_PROFILE_MANIFEST\n"
        "        manifest_sha256 = envs.VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256\n"
        "        if manifest_path is None:\n"
        "            if manifest_sha256 is not None:\n"
        "                raise ValueError(\n"
        '                    "RWKV7 state-profile manifest SHA-256 requires a manifest"\n'
        "                )\n"
        "            self.initial_state_profiles = RWKV7InitialStateProfiles.zero_only()\n"
        "        else:\n"
        "            model_artifact = str(\n"
        '                getattr(self.model_config, "model", None)\n'
        '                or getattr(cfg, "name_or_path", None)\n'
        '                or getattr(cfg, "_name_or_path", None)\n'
        '                or type(self.model).__qualname__\n'
        "            )\n"
        "            model_revision = str(\n"
        '                getattr(self.model_config, "revision", None)\n'
        '                or getattr(cfg, "_commit_hash", None)\n'
        '                or getattr(cfg, "rwkv_model_revision", None)\n'
        '                or "runtime"\n'
        "            )\n"
        '            tp_size = int(getattr(self.model, "tp_size", 1))\n'
        '            tp_rank = int(getattr(self.model, "tp_rank", 0))\n'
        "            self.initial_state_profiles = RWKV7InitialStateProfiles.load(\n"
        "                manifest_path,\n"
        "                manifest_sha256,\n"
        "                model_artifact=model_artifact,\n"
        "                model_revision=model_revision,\n"
        "                total_num_layers=total_num_layers,\n"
        "                total_num_heads=total_num_heads,\n"
        "                layer_offset=self.layer_offset,\n"
        "                num_layers=self.num_layers,\n"
        "                tp_size=tp_size,\n"
        "                tp_rank=tp_rank,\n"
        "                num_heads=self.num_heads,\n"
        "                head_size=self.head_size,\n"
        "                device=self.device,\n"
        "                dtype=self.wkv_state.dtype,\n"
        "            )\n"
        "            logger.info(\n"
        '                "RWKV7 state profiles loaded: manifest_sha256=%s profiles=%s",\n'
        "                self.initial_state_profiles.manifest_sha256,\n"
        "                self.initial_state_profiles.identities(),\n"
        "            )\n",
        label="profile initialization",
    )
    text = _replace_once(
        text,
        "        self._prefill_becomes_decode = []\n\n"
        "    def _state_slot_for_batch_entry(\n",
        "        self._prefill_becomes_decode = []\n"
        "        self.req_state_profile_ids.clear()\n\n"
        "    def _state_slot_for_batch_entry(\n",
        label="profile mapping reset",
    )
    old_add = '''    def add_request(self, req_index: int, new_req_data: NewRequestData) -> None:\n        self.req_id_to_index[new_req_data.req_id] = req_index\n        if not self.free_rows:\n            raise RuntimeError("RWKV7 state pool is full")\n        row = min(self.free_rows)\n        self.free_rows.remove(row)\n        self.req_slot_to_row[req_index] = row\n        self.row_to_req_slot[row] = req_index\n        self._zero_row(row)\n'''
    new_add = '''    def add_request(self, req_index: int, new_req_data: NewRequestData) -> None:\n        if req_index < 0 or req_index >= self.max_num_reqs:\n            raise RuntimeError(f"RWKV7 request slot {req_index} is out of range")\n        req_id = new_req_data.req_id\n        if req_id in self.req_id_to_index:\n            raise RuntimeError(f"RWKV7 request id {req_id!r} already owns state")\n        if self.req_slot_to_row[req_index] != -1:\n            raise RuntimeError(f"RWKV7 request slot {req_index} already owns state")\n        if not self.free_rows:\n            raise RuntimeError("RWKV7 state pool is full")\n\n        # Resolve and verify the requested profile before allocating any row.\n        profile = resolve_request_profile(\n            self.initial_state_profiles, new_req_data.sampling_params\n        )\n        row = min(self.free_rows)\n        self.free_rows.remove(row)\n        self.req_id_to_index[req_id] = req_index\n        self.req_slot_to_row[req_index] = row\n        self.row_to_req_slot[row] = req_index\n        self.req_state_profile_ids[req_id] = profile.profile_id\n        try:\n            self._initialize_row(row, profile)\n        except Exception:\n            self.req_id_to_index.pop(req_id, None)\n            self.req_slot_to_row[req_index] = -1\n            self.row_to_req_slot[row] = -1\n            self.req_state_profile_ids.pop(req_id, None)\n            self.free_rows.add(row)\n            self._zero_row(row)\n            raise\n'''
    text = _replace_once(text, old_add, new_add, label="request initialization")
    text = _replace_once(
        text,
        "        req_index = self.req_id_to_index.pop(req_id, None)\n"
        "        if req_index is None:\n"
        "            return\n",
        "        req_index = self.req_id_to_index.pop(req_id, None)\n"
        "        if req_index is None:\n"
        "            return\n"
        "        self.req_state_profile_ids.pop(req_id, None)\n",
        label="profile removal",
    )
    text = _replace_once(
        text,
        "    def _zero_row(self, row: int) -> None:\n"
        "        self.shift_state[:, :, row].zero_()\n"
        "        self.wkv_state[:, row].zero_()\n"
        "        self.elapsed[row].zero_()\n\n",
        "    def _zero_row(self, row: int) -> None:\n"
        "        self.shift_state[:, :, row].zero_()\n"
        "        self.wkv_state[:, row].zero_()\n"
        "        self.elapsed[row].zero_()\n\n"
        "    def _initialize_row(\n"
        "        self, row: int, profile: RWKV7InitialStateProfile\n"
        "    ) -> None:\n"
        "        self._zero_row(row)\n"
        "        if profile.wkv_state is not None:\n"
        "            self.wkv_state[:, row].copy_(profile.wkv_state)\n\n",
        label="profile row copy",
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--profile-module", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    envs_path = source_root / "vllm/envs.py"
    rwkv_path = source_root / "vllm/v1/worker/gpu/model_states/rwkv.py"
    profile_target = (
        source_root
        / "vllm/v1/worker/gpu/model_states/vllm_rwkv_state_profiles_v1.py"
    )
    inputs = {
        "envs.py": _sha256(envs_path),
        "rwkv.py": _sha256(rwkv_path),
    }
    expected = {
        "envs.py": EXPECTED_ENVS_SHA256,
        "rwkv.py": EXPECTED_RWKV_STATE_SHA256,
    }
    if inputs != expected:
        raise RuntimeError(f"source identity mismatch: {inputs!r}")
    if profile_target.exists():
        raise FileExistsError(f"overlay profile module already exists: {profile_target}")

    shutil.copyfile(args.profile_module.resolve(), profile_target)
    _patch_envs(envs_path)
    _patch_rwkv_state(rwkv_path)
    outputs = {
        "envs.py": _sha256(envs_path),
        "rwkv.py": _sha256(rwkv_path),
        "vllm_rwkv_state_profiles_v1.py": _sha256(profile_target),
    }
    report = {
        "schema_version": "rwkv-lh.vllm-rwkv-0p23-state-profile-overlay.v1",
        "source_root": str(source_root),
        "inputs": inputs,
        "outputs": outputs,
    }
    args.report.resolve().write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
