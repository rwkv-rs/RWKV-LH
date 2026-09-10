#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/source:/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export CUDA_VISIBLE_DEVICES=GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863
exec timeout 1800 /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B /home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/source/scripts/validate_statetune_native.py --runtime /home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/validation/NATIVE_RUNTIME.json --runtime-sha256 0af2b6eef9d84b170d29fb3a1d9559197a83338e6fb2750c93eb1c1cc07d463c --registration /home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/validation/COMPAT_REGISTRATION.json --registration-sha256 6d9eb94a36d96ec24bbd775aeeffcb18bdbb832e3d51f5943ee66d6abf00507c --output /home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/validation/compat
