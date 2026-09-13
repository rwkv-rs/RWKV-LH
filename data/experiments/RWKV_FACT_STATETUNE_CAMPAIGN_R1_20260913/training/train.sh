#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/source:/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export CUDA_VISIBLE_DEVICES=GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863
exec timeout 14700 /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B /home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/source/scripts/run_state_tune.py train --registration /home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/training_registration/REGISTRATION.json --registration-sha256 8e38993134773140af38fef36639509c975228469203270c604ee9aececc4e95 --output /home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/training_runs/direct-fact-r1-20260913
