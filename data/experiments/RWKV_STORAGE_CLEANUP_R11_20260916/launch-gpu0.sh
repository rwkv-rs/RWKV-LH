#!/bin/bash
set -euo pipefail
export VLLM_RWKV7_NATIVE_STATE_CACHE_CAPACITY=8
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-live-runtime-r11-20260916/ENGINE_SOURCE.json
export VLLM_USE_V2_MODEL_RUNNER=1
export RWKV_NATIVE_REQUEST_JOURNAL=/home/chase/GitHub/RWKV-LH-live-runtime-r11-20260916/state-gpu0/journal.sqlite3
export VLLM_RWKV7_NATIVE_STATE_DIR=/home/chase/GitHub/RWKV-LH-live-runtime-r11-20260916/state-gpu0/blobs
export VLLM_RWKV7_WKV_MODE=fp32io16
export CUDA_VISIBLE_DEVICES=GPU-1faf7f09-25f4-2515-b707-6e0766aa841d
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-concurrency-r7-20260915/source:/home/chase/GitHub/RWKV-LH-live-runtime-r11-20260916/engine
export VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY=0
export VLLM_PLUGINS=rwkv_lh_native_state
export PYTHONDONTWRITEBYTECODE=1
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256=1f29962fde1f7592d43d39b89a471e80afb84b074e9ca08d1a8be4c5b642b11e
export OMP_NUM_THREADS=4
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-concurrency-r7-20260915/PROJECT_SOURCE.json
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256=3f6211b7e9e861ecc2644dce8d471f0f541f43b42c072dcee358b7860d3a12f4
export VLLM_RWKV7_NATIVE_STATE_ENABLED=1
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -c 'import vllm; from rwkv_lh.inference.native_source_identity import verify_native_source_identity; print(verify_native_source_identity(engine_file=vllm.__file__))'
exec /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -m vllm.entrypoints.cli.main serve /home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1 --host 127.0.0.1 --port 18234 --tokenizer-mode rwkv --trust-request-chat-template --enable-auto-tool-choice --tool-call-parser rwkv --max-model-len 16384 --served-model-name rwkv7-g1j-13.3b-zero-state-capability-ctx16384-gc-r7 --gpu-memory-utilization 0.35 --max-num-batched-tokens 32768 --max-num-seqs 16 --override-generation-config '{"temperature":0.1}'
