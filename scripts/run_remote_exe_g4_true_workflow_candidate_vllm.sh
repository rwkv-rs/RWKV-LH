#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 2 || "$#" -gt 3 ]]; then
  echo "usage: $0 STEP EXPECTED_VLLM_SHA256 [EVAL_TAG]" >&2
  exit 2
fi

step=$1
expected_sha=$2
eval_tag=${3:-eval-step-$step}
case "$step" in
  250|500|750|1000|1250|1500|1750|2000) ;;
  *) echo "unregistered checkpoint step: $step" >&2; exit 3 ;;
esac
[[ "$expected_sha" =~ ^[0-9a-f]{64}$ ]]
[[ "$eval_tag" =~ ^eval-[a-z0-9][a-z0-9-]{0,63}$ ]]

run_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g4-true-workflow-full-request-last-2k-zero-lr2e-5-seed1059
state_path="$run_dir/rwkv-step-$step.vllm.pth"
sidecar_path="$run_dir/rwkv-step-$step.vllm.json"
attestation_path="$run_dir/$eval_tag/vllm_state_attestation.jsonl"
model_path=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
vllm_bin=/home/chase/.venv-vllm-rwkv-8e90d04ecb/bin/vllm
served_model="rwkv7-g1i-13.3b-exe-g4-true-workflow-step${step}-ctx2496"

[[ -s "$state_path" && -s "$sidecar_path" ]]
[[ "$(sha256sum "$state_path" | cut -d' ' -f1)" == "$expected_sha" ]]
if ss -ltn | grep -q ':18075 '; then
  echo "port 18075 is already in use" >&2
  exit 4
fi
mkdir -p "$(dirname "$attestation_path")"

export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=/home/chase/.local/share/rwkv-state-tuning-adapter:/home/chase/vllm-rwkv
export VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_RWKV7_WKV_MODE=fp32io16
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_USE_RAPID_SAMPLER=0
export VLLM_RWKV7_INITIAL_STATE_PATH="$state_path"
export VLLM_RWKV7_INITIAL_STATE_SHA256="$expected_sha"
export VLLM_RWKV7_ATTESTATION_PATH="$attestation_path"

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
