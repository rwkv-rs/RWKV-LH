#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 ROUND_LABEL SERVED_MODEL" >&2
  exit 64
fi

round_label=$1
served_model=$2
case "$round_label" in
  round1|round2|round3) ;;
  *) echo "unexpected round label: $round_label" >&2; exit 64 ;;
esac

project_dir=/home/chase/GitHub/RWKV-LH
output_dir="$project_dir/data/experiments/RWKV_STATE_TUNING_STAGE8_THREE_ROUND_V1_20260828/$round_label"
[[ ! -e "$output_dir" ]] || {
  echo "refusing existing evaluation output: $output_dir" >&2
  exit 1
}
mkdir -p "$output_dir"
cd "$project_dir"
export RWKV_MODEL="$served_model"

uv run python scripts/evaluate_rwkv_state_boundary_dataset.py \
  --source data/datasets/rwkv_lh_state_tuning_stage8_mutation_stop_v1/stage_sft.dev.jsonl \
  --label "${round_label}_stage8_dev400" \
  --output "$output_dir/stage8_dev400.json" \
  --temperature 0 \
  --seed 834 \
  --concurrency 16

uv run python scripts/evaluate_rwkv_state_boundary_dataset.py \
  --source data/datasets/rwkv_lh_state_tuning_stage7_factory_contrast_v1/stage_sft.dev.jsonl \
  --label "${round_label}_stage7_dev400" \
  --output "$output_dir/stage7_dev400.json" \
  --temperature 0 \
  --seed 834 \
  --concurrency 16

uv run python scripts/evaluate_rwkv_state_boundary_dataset.py \
  --source data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1/stage_sft.dev.jsonl \
  --label "${round_label}_round1_dev200" \
  --output "$output_dir/round1_dev200.json" \
  --temperature 0 \
  --seed 834 \
  --concurrency 16

set +e
uv run python scripts/run_ecra_route_benchmark.py \
  --output "$output_dir/ecra_route120_B" \
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
