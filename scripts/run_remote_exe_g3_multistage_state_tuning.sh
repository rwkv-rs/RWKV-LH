#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/chase/chase/RWKV-PEFT
base_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
data_dir=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_executor_multistage_g3_2k
data_file="$data_dir/rwkv_state_tuning.train.requires_target_suffix.jsonl"
manifest_file="$data_dir/manifest.json"
validation_file="$data_dir/remote_training_contract_validation.json"
proj_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g3-multistage-request-last-2k-zero-lr2e-5-seed1055

[[ "$(sha256sum "$base_model" | cut -d' ' -f1)" == "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562" ]]
[[ "$(sha256sum "$data_file" | cut -d' ' -f1)" == "8ce1181020dfc5c65e2e75ae1dc1ee465b2d4b5d77cb4ea6fd21752933f21ad6" ]]
[[ "$(sha256sum "$manifest_file" | cut -d' ' -f1)" == "c510b434be71cf1304aeb75de6ba4156756aaebcae2566f56d528dcce844f5e1" ]]
[[ "$(jq -r '.overall.failure_count' "$validation_file")" == "0" ]]
[[ "$(wc -l < "$data_file")" -eq 2000 ]]
[[ ! -e "$proj_dir" ]]

export CUDA_VISIBLE_DEVICES=0
cd "$project_dir"

exec .venv/bin/python train.py \
  --load_model "$base_model" \
  --proj_dir "$proj_dir" \
  --data_file "$data_file" \
  --data_type jsonl \
  --loss_mask target_suffix \
  --jsonl_bos_token_id 0 \
  --data_shuffle 1 \
  --vocab_size 65536 \
  --n_layer 61 \
  --n_embd 4096 \
  --ctx_len 2496 \
  --micro_bsz 1 \
  --accumulate_grad_batches 1 \
  --epoch_steps 2000 \
  --epoch_count 1 \
  --epoch_save 1 \
  --step_save 250 \
  --lr_init 2e-5 \
  --lr_final 2e-6 \
  --lr_schedule cos \
  --warmup_steps 50 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed 1055 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
