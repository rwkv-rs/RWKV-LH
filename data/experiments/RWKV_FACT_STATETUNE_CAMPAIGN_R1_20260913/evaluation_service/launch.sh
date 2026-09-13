#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/source:/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/validation/ENGINE_SOURCE.json
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256=016d3ac4af9c5eca71fa27b82d3fe71d4e029314bee3f0c1a1513bc00b839693
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/validation/PROJECT_SOURCE.json
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256=292df51dfbcb10023ef5718c14d1b2fa92991bb1f30466f15ebba02b43ccaf9a
export CUDA_VISIBLE_DEVICES=GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863
export VLLM_PLUGINS=rwkv_lh_native_state
export VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_RWKV7_NATIVE_STATE_ENABLED=1
export VLLM_RWKV7_NATIVE_STATE_CACHE_CAPACITY=8
export VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY=0
export VLLM_RWKV7_NATIVE_STATE_DIR=/home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/evaluation_state/blobs
export RWKV_NATIVE_REQUEST_JOURNAL=/home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/evaluation_state/journal.sqlite3
export VLLM_RWKV7_STATE_PROFILE_MANIFEST=/home/chase/GitHub/RWKV-LH-fact-statetune-r1-20260913/evaluation_service/STATE_PROFILES_SERVING.json
export VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256=bf838e9896eb135c8ff64b6eb762b32da01dfc36dcf13ac910a0e97db263cb22
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -c 'import vllm; from rwkv_lh.inference.native_source_identity import verify_native_source_identity; print(verify_native_source_identity(engine_file=vllm.__file__))'
exec /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -m vllm.entrypoints.cli.main serve /home/chase/GitHub/RWKV-LH-direct-statetune-r1-20260913/model_serving_r2 --revision 67f0c5996c50dca0ad779da545cb491527de988f --host 127.0.0.1 --port 18236 --tokenizer-mode rwkv --trust-request-chat-template --enable-auto-tool-choice --tool-call-parser rwkv --max-model-len 16384 --served-model-name rwkv-direct-fact-r1-ctx16384 --gpu-memory-utilization 0.35 --max-num-batched-tokens 32768 --max-num-seqs 16 --override-generation-config '{"temperature":0.1}'
