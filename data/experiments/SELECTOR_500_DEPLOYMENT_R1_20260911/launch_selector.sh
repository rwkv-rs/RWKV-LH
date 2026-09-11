#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/source:/home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export VLLM_RWKV7_WKV_MODE=fp32io16
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/validation/ENGINE_SOURCE.json
export RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256=9fdfd8e8b11f6c6de3df30ae9e36088765cf9780831595b49150d4e95375b32a
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST=/home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/validation/PROJECT_SOURCE.json
export RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256=524a195270d8d10062e87a17a7c0c5dba36ceae3c83e3413ca34c85a01def0c5
export CUDA_VISIBLE_DEVICES=GPU-5d61943c-0955-e221-92a8-318915f5a3a0
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -c 'import vllm; from rwkv_lh.inference.native_source_identity import verify_native_source_identity; print(verify_native_source_identity(engine_file=vllm.__file__))'
exec /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -B -m rwkv_lh.exact_tool_selector.native_network_service --engine-root /home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/engine --engine-revision 67f0c5996c50dca0ad779da545cb491527de988f --engine-python /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python --engine-source-manifest /home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/validation/ENGINE_SOURCE.json --engine-source-manifest-sha256 9fdfd8e8b11f6c6de3df30ae9e36088765cf9780831595b49150d4e95375b32a --model-artifact /home/chase/GitHub/RWKV-LH-selector-r1-20260909/model --model-name rwkv7-g1j-2.9b-20260831-ctx16384 --model-sha256 1f920b94c4684e8463f36d8b71df23a8b50551f7776d39eec9ec6970471d460b --decoder-manifest /home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/validation/DECODER_MANIFEST.json --decoder-sha256 bd5d3720498f56ca9291d3f3033ea99cf73dabdd5d1c65a84e50e99ae484c610 --context-tokens 16384 --runtime-temp /home/chase/GitHub/RWKV-LH-selector-500-runtime-r1-20260911/selector_runtime --port 29621
