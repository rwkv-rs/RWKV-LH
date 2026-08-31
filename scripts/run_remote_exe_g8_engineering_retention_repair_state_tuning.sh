#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/chase/chase/RWKV-PEFT
base_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
parent_state=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g6-network-recovery-2k-g4-parent-lr2e-6-seed1067/rwkv-step-1500.pth
data_dir=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_executor_engineering_retention_repair_g8_2k
data_file="$data_dir/rwkv_state_tuning.train.requires_target_suffix.jsonl"
manifest_file="$data_dir/manifest.json"
validation_file="$data_dir/remote_training_contract_validation.json"
alignment_file="$data_dir/training_serving_tokenizer_alignment.json"
proj_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g8-engineering-retention-repair-2k-g6-step1500-parent-lr2e-6-seed1079

[[ "$(sha256sum "$base_model" | cut -d' ' -f1)" == "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562" ]]
[[ "$(sha256sum "$parent_state" | cut -d' ' -f1)" == "648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78" ]]
[[ "$(sha256sum "$data_file" | cut -d' ' -f1)" == "3b9d24a3fff5832b298a3ce45cfb36892f094addaccde60190d502999ae5879f" ]]
[[ "$(sha256sum "$manifest_file" | cut -d' ' -f1)" == "d9e863dba7dd46ae135bb18e125eb3dac96c41ff7f4219e73754e78ccee83013" ]]
[[ "$(sha256sum "$validation_file" | cut -d' ' -f1)" == "48a6be742223c4e5b341b2aac5dce94d8f3cd6e459add4c7ca5a1e5f0c4b4a83" ]]
[[ "$(sha256sum "$alignment_file" | cut -d' ' -f1)" == "60af639143abf5adb37f12a7716e6face3ea1c0c5d3e92efb90cc35ac0501f96" ]]
[[ "$(jq -r '.overall.failure_count' "$validation_file")" == "0" ]]
[[ "$(jq -r '.overall.maximum_tokens' "$validation_file")" -le 2497 ]]
jq -e '.target_suffix_audit.exact_label_match_rate == 1.0' "$validation_file" >/dev/null
[[ "$(jq -r '.failure_count' "$alignment_file")" == "0" ]]
[[ "$(wc -l < "$data_file")" -eq 2000 ]]
[[ "$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader,nounits -i 0 | tr -d ' ')" == "0,GPU-1faf7f09-25f4-2515-b707-6e0766aa841d" ]]
curl -fsS --max-time 10 http://127.0.0.1:18070/health >/dev/null
[[ ! -e "$proj_dir" ]]

export CUDA_VISIBLE_DEVICES=0
cd "$project_dir"

exec .venv/bin/python train.py \
  --load_model "$base_model" \
  --state_init "$parent_state" \
  --state_init_sha256 648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78 \
  --require_state_init 1 \
  --state_init_expected_tensors 61 \
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
  --lr_init 2e-6 \
  --lr_final 2e-7 \
  --lr_schedule cos \
  --warmup_steps 40 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed 1079 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
