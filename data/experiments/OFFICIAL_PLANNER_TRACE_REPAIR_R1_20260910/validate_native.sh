#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-official-planner-repair-r1-20260910/source:/home/chase/GitHub/RWKV-LH-official-planner-repair-r1-20260910/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export CUDA_VISIBLE_DEVICES=GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863
exec timeout 1800 /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-20260910/source/scripts/validate_statetune_native.py --runtime /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-20260910/validation/NATIVE_RUNTIME.json --runtime-sha256 9f46703cc42804a88f61e8ae5db0272821e783e491bf324a89d147d79cac9498 --registration /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-20260910/validation/COMPAT_REGISTRATION.json --registration-sha256 098c23de4c1b7056deb746d849ffe33bdceb9344e85ca1486d3dd03367f5625b --output /home/chase/GitHub/RWKV-LH-official-planner-repair-r1-20260910/validation/compat
