#!/bin/bash
set -euo pipefail
export PYTHONPATH=/home/chase/GitHub/RWKV-LH-selector-r1-20260909/source:/home/chase/GitHub/RWKV-LH-native-r32-engine/engine
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
export CUDA_VISIBLE_DEVICES=GPU-5d61943c-0955-e221-92a8-318915f5a3a0
export VLLM_RWKV7_WKV_MODE=fp32io16
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python /home/chase/GitHub/RWKV-LH-selector-r1-20260909/validation/verify_uploaded_project_source_20260909.py --manifest /home/chase/GitHub/RWKV-LH-selector-r1-20260909/SOURCE_MANIFEST.json --sha256 63f481fc95bb953a385f5fc9729ced38c50f15512e02fc7e057c3e54694a4575
exec /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python -m rwkv_lh.exact_tool_selector.native_network_service --engine-root /home/chase/GitHub/RWKV-LH-native-r32-engine/engine --engine-revision 67f0c5996c50dca0ad779da545cb491527de988f --engine-python /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python --engine-source-manifest /home/chase/GitHub/RWKV-LH-native-r32-engine/ENGINE_SOURCE.json --engine-source-manifest-sha256 841ac0d6bdd1b0a45660583fc12e385f3cfcd1d3300601a276bc4f60a1471522 --model-artifact /home/chase/GitHub/RWKV-LH-selector-r1-20260909/model --model-name rwkv7-g1j-2.9b-20260831-ctx16384 --model-sha256 1f920b94c4684e8463f36d8b71df23a8b50551f7776d39eec9ec6970471d460b --decoder-manifest /home/chase/GitHub/RWKV-LH-selector-r1-20260909/validation/DECODER_MANIFEST.json --decoder-sha256 c4c250b36c52b0891b20e96b82ec3b056d3606313c139962241a308334be807a --context-tokens 16384 --runtime-temp /home/chase/GitHub/RWKV-LH-selector-r1-20260909/runtime --port 29621
