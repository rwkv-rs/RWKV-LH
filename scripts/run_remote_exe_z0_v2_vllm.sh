#!/usr/bin/env bash
set -euo pipefail

model_path=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
vllm_bin=/home/chase/.venv-vllm-rwkv-8e90d04ecb/bin/vllm
served_model=rwkv7-g1i-13.3b-exe-z0-v2-base-zero-ctx2496

export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=/home/chase/vllm-rwkv
export VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_RWKV7_WKV_MODE=fp32io16
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_USE_RAPID_SAMPLER=0

# The state adapter is opt-in.  Clearing every adapter variable is the
# fail-closed identity for EXE-Z0-V2; vLLM then creates its native zero state.
unset VLLM_RWKV7_INITIAL_STATE_PATH
unset VLLM_RWKV7_INITIAL_STATE_SHA256
unset VLLM_RWKV7_ATTESTATION_PATH

exec "$vllm_bin" serve "$model_path" \
  --host 127.0.0.1 \
  --port 18075 \
  --tokenizer-mode rwkv \
  --trust-request-chat-template \
  --enable-auto-tool-choice \
  --tool-call-parser rwkv \
  --max-model-len 16384 \
  --served-model-name "$served_model" \
  --gpu-memory-utilization 0.38 \
  --max-num-batched-tokens 32768 \
  --max-num-seqs 16 \
  --override-generation-config='{"temperature":0.1}'
