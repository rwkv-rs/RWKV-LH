#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 STEP SERVED_MODEL" >&2
  exit 2
fi

step=$1
served_model=$2
case "$step" in
  500|1000|1500|2000) ;;
  *) echo "unexpected Stage7 checkpoint step: $step" >&2; exit 2 ;;
esac

project_dir=/home/chase/GitHub/RWKV-LH
experiment_dir="$project_dir/data/experiments/RWKV_STATE_TUNING_STAGE7_FACTORY_CONTRAST_V1_20260827"
output_dir="$experiment_dir/candidates/step$step"
own_dev="$output_dir/own_dev400_greedy.json"
round1_dev="$output_dir/round1_dev200_greedy.json"
ecra_dir="$output_dir/ecra_route120_B"

[[ ! -e "$output_dir" ]] || { echo "refusing existing evaluation output: $output_dir" >&2; exit 1; }
mkdir -p "$output_dir"
cd "$project_dir"
export RWKV_MODEL="$served_model"

uv run python scripts/evaluate_rwkv_state_boundary_dataset.py \
  --source data/datasets/rwkv_lh_state_tuning_stage7_factory_contrast_v1/stage_sft.dev.jsonl \
  --label "stage7_step${step}_own_dev400" \
  --output "$own_dev" \
  --temperature 0 \
  --seed 826 \
  --concurrency 16

uv run python scripts/evaluate_rwkv_state_boundary_dataset.py \
  --source data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1/stage_sft.dev.jsonl \
  --label "stage7_step${step}_round1_dev200" \
  --output "$round1_dev" \
  --temperature 0 \
  --seed 826 \
  --concurrency 16

set +e
uv run python scripts/run_ecra_route_benchmark.py \
  --output "$ecra_dir" \
  --variant B \
  --architecture direct \
  --case-concurrency 8 \
  --max-transitions 40 \
  --max-actions 5
ecra_status=$?
set -e
if [[ "$ecra_status" -ne 0 && "$ecra_status" -ne 2 ]]; then
  exit "$ecra_status"
fi

# Stage1 Shadow is observational and is explicitly outside the Stage7 deployment
# score. Exit 2 means its own preregistered classifier gate did not pass; retain
# that raw result without turning it into a state-checkpoint infrastructure error.
set +e
uv run python scripts/run_state_router_shadow_canary_v1.py \
  --output "$output_dir/state_router_shadow_canary" \
  --max-transitions 200
shadow_status=$?
set -e
if [[ "$shadow_status" -ne 0 && "$shadow_status" -ne 2 ]]; then
  exit "$shadow_status"
fi
