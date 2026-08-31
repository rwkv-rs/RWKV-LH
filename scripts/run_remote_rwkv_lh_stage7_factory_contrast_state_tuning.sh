#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/chase/chase/RWKV-PEFT
base_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
parent_state=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-stage4-balanced1140-cont-stage1-lr1e-5-seed830/rwkv-step-1140.pth
parent_sha=8af6f29bb8cd68ed2f5e7ca6bcee56f7df7c53bccb083a80d1fa51e680d81960
base_sha=5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562
data_file=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_state_tuning_stage7_factory_contrast_v1/rwkv_state_tuning.train.requires_target_suffix.jsonl
manifest_file=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_state_tuning_stage7_factory_contrast_v1/manifest.json
validation_file=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_state_tuning_stage7_factory_contrast_v1/remote_training_contract_validation.json
alignment_file=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_state_tuning_stage7_factory_contrast_v1/training_serving_tokenizer_alignment.json
proj_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-stage7-factory-contrast2000-cont-stage4-lr3e-6-seed833
preflight_manifest="$proj_dir/run_manifest.pretrain.json"

check_sha256() {
  local path=$1
  local expected=$2
  local actual
  [[ -f "$path" ]] || { echo "missing required artifact: $path" >&2; exit 1; }
  actual=$(sha256sum -- "$path")
  actual=${actual%% *}
  [[ "$actual" == "$expected" ]] || { echo "required artifact changed: $path" >&2; exit 1; }
}

check_sha256 "$base_model" "$base_sha"
check_sha256 "$parent_state" "$parent_sha"
check_sha256 "$data_file" b9bcb35b9f9dcc715725fadd093a7f7933a154749f9d7fb733357bd74c57bd55
check_sha256 "$manifest_file" 4033a1c92d68e028b206f1c2acd37369ae3ea29492513658e999dd74f26d2b70
check_sha256 "$validation_file" 6abe19907588405963e0ca571944c2a737282b1c543e004eef34d6f986b16fcd
check_sha256 "$alignment_file" da78e978641dd2be8dd3166647a1ee59c4d6ac07f058179ed76fc57ba2033d36
[[ -s "$preflight_manifest" ]] || { echo "committed preflight manifest is missing" >&2; exit 1; }

export CUDA_VISIBLE_DEVICES=0
cd "$project_dir"

exec .venv/bin/python train.py \
  --load_model "$base_model" \
  --state_init "$parent_state" \
  --state_init_sha256 "$parent_sha" \
  --require_state_init 1 \
  --state_init_expected_tensors 61 \
  --proj_dir "$proj_dir" \
  --data_file "$data_file" \
  --data_type jsonl \
  --loss_mask target_suffix \
  --jsonl_bos_token_id 0 \
  --data_shuffle 0 \
  --vocab_size 65536 \
  --n_layer 61 \
  --n_embd 4096 \
  --ctx_len 2496 \
  --micro_bsz 1 \
  --accumulate_grad_batches 1 \
  --epoch_steps 2000 \
  --epoch_count 1 \
  --epoch_save 1 \
  --step_save 500 \
  --lr_init 3e-6 \
  --lr_final 6e-7 \
  --lr_schedule cos \
  --warmup_steps 20 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed 833 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
