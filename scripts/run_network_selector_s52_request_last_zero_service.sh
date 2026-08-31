#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_ROOT="$PROJECT_ROOT/data/runtime/engines/vllm-rwkv-67f0c5996c50"
ENGINE_PYTHON="$ENGINE_ROOT/.venv/bin/python"
MODEL_ARTIFACT="$PROJECT_ROOT/data/models/rwkv7-g1i-2.9b-vllm-v1"
HEAD="$PROJECT_ROOT/data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_s52_request_last_head_dev_selection/candidates/concat-h64/selector_head.json"
PROFILE_MANIFEST="$PROJECT_ROOT/data/models/state_profiles/network-selector-true-trajectory-s31-step2000-v1/profiles.json"
STATE_DIR="$PROJECT_ROOT/data/runtime/network-selector-s52-request-last-zero/dynamic-state"
RUNTIME_TEMP="$PROJECT_ROOT/temp/vllm-rwkv-selector-s52-request-last-zero-service-gpu0"

ENGINE_REVISION="67f0c5996c50dca0ad779da545cb491527de988f"
MODEL_SHA256="01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044"
HEAD_SHA256="a1015319ade76d757013c9db41438f2cc7d1cdd7d13f4bac683896f4428d445c"
HEAD_HASH="84f89789d8d31c54ce03551fa217cd38ab37d32c7b8d2f5d0fcf1136024c4b1a"
INPUT_PROTOCOL="rwkv-lh.exact-tool-selector-input.v4-request-last"
PROFILE_MANIFEST_SHA256="706ff62cc8ae5851f9c918509911d4ee701f9db5d00bef16f24d2a568e3a0b47"
ZERO_SHA256="0000000000000000000000000000000000000000000000000000000000000000"

SERVICE_HOST="${RWKV_SELECTOR_SERVICE_HOST:-127.0.0.1}"
SERVICE_PORT="${RWKV_SELECTOR_SERVICE_PORT:-29621}"
REQUESTED_GPU="${CUDA_VISIBLE_DEVICES:-0}"

if [[ "$SERVICE_HOST" != "127.0.0.1" ]]; then
  echo "network Selector service is local-only; host must be 127.0.0.1" >&2
  exit 2
fi
if [[ ! "$SERVICE_PORT" =~ ^[0-9]+$ ]] || (( SERVICE_PORT < 1024 || SERVICE_PORT > 65535 )); then
  echo "RWKV_SELECTOR_SERVICE_PORT must be an unprivileged TCP port" >&2
  exit 2
fi
if [[ "$REQUESTED_GPU" != "0" ]]; then
  echo "network Selector service is pinned to physical GPU0" >&2
  exit 2
fi

for required in "$ENGINE_PYTHON" "$MODEL_ARTIFACT" "$HEAD" "$PROFILE_MANIFEST"; do
  if [[ ! -e "$required" ]]; then
    echo "required network Selector artifact is missing: $required" >&2
    exit 2
  fi
done

verify_sha256() {
  local path="$1"
  local expected="$2"
  local actual
  actual="$(sha256sum -- "$path")"
  actual="${actual%% *}"
  if [[ "$actual" != "$expected" ]]; then
    echo "network Selector artifact SHA-256 mismatch: $path" >&2
    exit 2
  fi
}

verify_sha256 "$HEAD" "$HEAD_SHA256"
verify_sha256 "$PROFILE_MANIFEST" "$PROFILE_MANIFEST_SHA256"

mkdir -p -- "$STATE_DIR" "$RUNTIME_TEMP"
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="$PROJECT_ROOT"

exec uv run --no-project --python "$ENGINE_PYTHON" python \
  -m rwkv_lh.exact_tool_selector.network_service \
  --host "$SERVICE_HOST" \
  --port "$SERVICE_PORT" \
  --engine-root "$ENGINE_ROOT" \
  --engine-revision "$ENGINE_REVISION" \
  --engine-python "$ENGINE_PYTHON" \
  --model-artifact "$MODEL_ARTIFACT" \
  --model-name rwkv7-g1i-2.9b-vllm-v1 \
  --model-sha256 "$MODEL_SHA256" \
  --head "$HEAD" \
  --head-sha256 "$HEAD_SHA256" \
  --head-hash "$HEAD_HASH" \
  --input-protocol "$INPUT_PROTOCOL" \
  --profile-manifest "$PROFILE_MANIFEST" \
  --profile-manifest-sha256 "$PROFILE_MANIFEST_SHA256" \
  --profile-id zero \
  --profile-sha256 "$ZERO_SHA256" \
  --state-dir "$STATE_DIR" \
  --runtime-temp "$RUNTIME_TEMP"
