#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-selector-r1-20260909/source:/home/chase/GitHub/RWKV-LH-native-r32-engine/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export CUDA_VISIBLE_DEVICES=GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863
export VLLM_RWKV7_WKV_MODE=fp32io16
exec timeout 1800 /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python /home/chase/GitHub/RWKV-LH-selector-r1-20260909/source/scripts/validate_statetune_native.py --runtime /home/chase/GitHub/RWKV-LH-selector-r1-20260909/validation/NATIVE_RUNTIME.json --runtime-sha256 aa6b8607ef91e2f26b6ad73bca47276720544cc76c6cb2250ef444b27fd6ebde --registration /home/chase/GitHub/RWKV-LH-selector-r1-20260909/validation/COMPAT_REGISTRATION.json --registration-sha256 2ab24eaa7bf7993c26d9e02916d2ac81f8aadbc2eff413161fb3d242ea0e5d79 --output /home/chase/GitHub/RWKV-LH-selector-r1-20260909/validation/compat_attempt2
