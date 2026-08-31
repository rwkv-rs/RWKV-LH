#!/usr/bin/env python3
"""Fail-closed validation for all EXE-G2-V3-RL checkpoints."""

from pathlib import Path

import validate_remote_exe_g1_v2_checkpoints as validation


validation.RUN = (
    validation.PROJECT
    / "out/g1i-13.3b-rwkv-lh-exe-g2-v3-request-last-2k-zero-lr2e-5-seed829"
)
validation.PREFLIGHT = (
    validation.PROJECT
    / "temp/exe_g2_v3_request_last_training/RUN_MANIFEST.pretrain.json"
)
validation.OUTPUT = validation.RUN / "CHECKPOINT_VALIDATION.json"
validation.PROFILE = "EXE-G2-V3-RL"
validation.REPORT_SCHEMA_VERSION = (
    "rwkv-lh.exe-g2-v3-request-last-checkpoint-validation.v1"
)


if __name__ == "__main__":
    validation.main()
