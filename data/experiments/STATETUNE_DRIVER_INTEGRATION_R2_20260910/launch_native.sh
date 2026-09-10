#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/source:/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/validation/ENGINE_SOURCE.json
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256=4327197e8305f2a79ed750128df4ec689df16e2bd234b438d634bbd9d7fa395d
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/validation/PROJECT_SOURCE.json
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256=d8952c5dab4248a93db339720f37dd4e7657fa175882e8fc23b5a1613b8241e6
export CUDA_VISIBLE_DEVICES=GPU-1faf7f09-25f4-2515-b707-6e0766aa841d
export VLLM_PLUGINS=rwkv_lh_native_state
export VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_RWKV7_NATIVE_STATE_ENABLED=1
export VLLM_RWKV7_NATIVE_STATE_CACHE_CAPACITY=8
export VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY=0
export VLLM_RWKV7_NATIVE_STATE_DIR=/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/state/blobs
export RWKV_NATIVE_REQUEST_JOURNAL=/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910/state/journal.sqlite3
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -c 'import vllm; from rwkv_lh.inference.native_source_identity import verify_native_source_identity; print(verify_native_source_identity(engine_file=vllm.__file__))'
exec /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -m vllm.entrypoints.cli.main serve /home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1 --host 127.0.0.1 --port 18234 --tokenizer-mode rwkv --trust-request-chat-template --enable-auto-tool-choice --tool-call-parser rwkv --max-model-len 16384 --served-model-name rwkv7-g1j-13.3b-zero-state-capability-ctx16384 --gpu-memory-utilization 0.35 --max-num-batched-tokens 32768 --max-num-seqs 16 --override-generation-config '{"temperature":0.1}'
