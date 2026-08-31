#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 5 ]]; then
  echo "usage: $0 MANIFEST_SHA256 ENVS_SHA256 RWKV_SHA256 TEST_SHA256 EVAL_TAG" >&2
  exit 2
fi

manifest_sha=$1
envs_sha=$2
rwkv_sha=$3
test_sha=$4
eval_tag=$5
for digest in "$manifest_sha" "$envs_sha" "$rwkv_sha" "$test_sha"; do
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || {
    echo "all artifact identities must be lowercase SHA-256" >&2
    exit 3
  }
done
[[ "$eval_tag" =~ ^eval-[a-z0-9][a-z0-9-]{0,63}$ ]] || {
  echo "invalid evaluation tag" >&2
  exit 4
}

engine_root=/home/chase/chase/vllm-rwkv-g8-stage-c-20260829
profile_root=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g8-engineering-retention-repair-2k-g6-step1500-parent-lr2e-6-seed1079/stage-c-profiles
manifest_path="$profile_root/profiles.json"
envs_path="$engine_root/vllm/envs.py"
rwkv_path="$engine_root/vllm/v1/worker/gpu/model_states/rwkv.py"
test_path="$engine_root/tests/model_executor/models/test_rwkv7.py"
model_path=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
vllm_bin=/home/chase/.venv-vllm-rwkv-8e90d04ecb/bin/vllm
evidence_dir="$profile_root/$eval_tag"
served_model=rwkv7-g1i-13.3b-exe-g8-stage-c-multiprofile-ctx2496

[[ -d "$engine_root" && -s "$manifest_path" ]]
[[ "$(sha256sum "$manifest_path" | cut -d' ' -f1)" == "$manifest_sha" ]]
[[ "$(sha256sum "$envs_path" | cut -d' ' -f1)" == "$envs_sha" ]]
[[ "$(sha256sum "$rwkv_path" | cut -d' ' -f1)" == "$rwkv_sha" ]]
[[ "$(sha256sum "$test_path" | cut -d' ' -f1)" == "$test_sha" ]]
[[ ! -e "$evidence_dir" ]] || {
  echo "refusing to reuse multi-profile service evidence" >&2
  exit 5
}
if ss -ltn | grep -q ':18075 '; then
  echo "port 18075 is already in use" >&2
  exit 6
fi
mkdir -p "$evidence_dir"

export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="$engine_root"
export VLLM_USE_V2_MODEL_RUNNER=1
export VLLM_RWKV7_WKV_MODE=fp32io16
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_USE_RAPID_SAMPLER=0
export VLLM_RWKV7_STATE_PROFILE_MANIFEST="$manifest_path"
export VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256="$manifest_sha"
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
