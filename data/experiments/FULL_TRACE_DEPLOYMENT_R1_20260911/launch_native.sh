#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-full-trace-runtime-r1-20260911/source:/home/chase/GitHub/RWKV-LH-full-trace-runtime-r1-20260911/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-full-trace-runtime-r1-20260911/validation/ENGINE_SOURCE.json
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256=a01d49ffd93c539bdc37abdb08e5de488230c47c15b61074a83afa377cece27a
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-full-trace-runtime-r1-20260911/validation/PROJECT_SOURCE.json
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256=36f054ffa38b9ade0504163ee0baa0f3b65cd321c5283a7ba399bb8aaf163aab
export CUDA_VISIBLE_DEVICES=GPU-1faf7f09-25f4-2515-b707-6e0766aa841d
export VLLM_PLUGINS=rwkv_lh_native_state
export VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_RWKV7_NATIVE_STATE_ENABLED=1
export VLLM_RWKV7_NATIVE_STATE_CACHE_CAPACITY=8
export VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY=0
export VLLM_RWKV7_NATIVE_STATE_DIR=/home/chase/GitHub/RWKV-LH-full-trace-runtime-r1-20260911/state/blobs
export RWKV_NATIVE_REQUEST_JOURNAL=/home/chase/GitHub/RWKV-LH-full-trace-runtime-r1-20260911/state/journal.sqlite3
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -c 'import vllm; from rwkv_lh.inference.native_source_identity import verify_native_source_identity; print(verify_native_source_identity(engine_file=vllm.__file__))'
exec /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -m vllm.entrypoints.cli.main serve /home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1 --host 127.0.0.1 --port 18234 --tokenizer-mode rwkv --trust-request-chat-template --enable-auto-tool-choice --tool-call-parser rwkv --max-model-len 16384 --served-model-name rwkv7-g1j-13.3b-zero-state-capability-ctx16384 --gpu-memory-utilization 0.35 --max-num-batched-tokens 32768 --max-num-seqs 16 --override-generation-config '{"temperature":0.1}'
