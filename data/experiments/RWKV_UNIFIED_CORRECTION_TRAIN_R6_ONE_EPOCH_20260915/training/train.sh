#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-unified-train-r5-300-20260915/source:/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=0
exec timeout 18300 /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B /home/chase/GitHub/RWKV-LH-unified-train-r5-300-20260915/source/scripts/run_state_tune.py train --registration /home/chase/GitHub/RWKV-LH-unified-train-r6-one-epoch-20260915/training_registration/REGISTRATION.json --registration-sha256 3d2cb117cb6d616073b91a0cd64b3d5c0d829c39ef151f24b72427ee5751dd65 --output /home/chase/GitHub/RWKV-LH-unified-train-r6-one-epoch-20260915/training_runs/direct-unified-r6-one-epoch-20260915
