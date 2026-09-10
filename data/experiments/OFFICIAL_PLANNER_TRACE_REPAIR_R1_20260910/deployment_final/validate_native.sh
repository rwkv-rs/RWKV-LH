#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910/source:/home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export CUDA_VISIBLE_DEVICES=GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863
exec timeout 1800 /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910/source/scripts/validate_statetune_native.py --runtime /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910/validation/NATIVE_RUNTIME.json --runtime-sha256 2012b5eefe9e579e757e52e8ac471f9a10ecafc1edd4fb4ae88170fcea31f55d --registration /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910/validation/COMPAT_REGISTRATION.json --registration-sha256 f2778165a35187afc47cf37c6aaedf5d5e0ef49ca72c107323bed6cf054b0d44 --output /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-final-20260910/validation/compat
