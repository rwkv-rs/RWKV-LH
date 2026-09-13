#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/source:/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export CUDA_VISIBLE_DEVICES=GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863
exec timeout 3600 /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B /home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/source/scripts/validate_statetune_native.py --runtime /home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/validation/NATIVE_RUNTIME.json --runtime-sha256 ca5449f1ad9e1698d750909d9b648a9d0aa7ea78aedefbf34492f06087301b9a --registration /home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/validation/COMPAT_REGISTRATION.json --registration-sha256 3f444db754ad73ffeb8d1469b941b3811dca5363f3f369a81a4546c551e4e8ee --output /home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/validation/compat
