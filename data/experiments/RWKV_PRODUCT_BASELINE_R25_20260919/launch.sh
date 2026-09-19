#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-product-baseline-r25-20260919/source:/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/validation/ENGINE_SOURCE.json
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256=016d3ac4af9c5eca71fa27b82d3fe71d4e029314bee3f0c1a1513bc00b839693
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-product-baseline-r25-20260919/PROJECT_SOURCE.json
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256=939d2fbc100112e705c76d0adac3a9ba2f0f59f9a52126fdf47ed4b0ffac7416
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=0
export VLLM_PLUGINS=rwkv_lh_native_state
export VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_RWKV7_NATIVE_STATE_ENABLED=1
export VLLM_RWKV7_NATIVE_STATE_CACHE_CAPACITY=8
export VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY=0
export VLLM_RWKV7_NATIVE_STATE_DIR=/home/chase/GitHub/RWKV-LH-product-baseline-r25-20260919/state/blobs
export RWKV_NATIVE_REQUEST_JOURNAL=/home/chase/GitHub/RWKV-LH-product-baseline-r25-20260919/state/journal.sqlite3
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -c 'import vllm; from rwkv_lh.inference.native_source_identity import verify_native_source_identity; print(verify_native_source_identity(engine_file=vllm.__file__))'
exec /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -m vllm.entrypoints.cli.main serve /home/chase/GitHub/RWKV-LH-unified-corrections-r1-20260914/model_serving_ctx24576 --revision 67f0c5996c50dca0ad779da545cb491527de988f --host 127.0.0.1 --port 18265 --tokenizer-mode rwkv --trust-request-chat-template --enable-auto-tool-choice --tool-call-parser rwkv --max-model-len 24576 --served-model-name rwkv-direct-product-r25-ctx24576 --gpu-memory-utilization 0.60 --max-num-batched-tokens 32768 --max-num-seqs 16 --override-generation-config '{"temperature":0.1}'
