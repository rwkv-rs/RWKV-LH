#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/chase/chase/RWKV-PEFT
base_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
parent_state=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g4-true-workflow-full-request-last-2k-zero-lr2e-5-seed1059/rwkv-step-2000.pth
data_dir=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_executor_network_recovery_g6_2k
data_file="$data_dir/rwkv_state_tuning.train.requires_target_suffix.jsonl"
manifest_file="$data_dir/manifest.json"
validation_file="$data_dir/remote_training_contract_validation.json"
proj_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g6-network-recovery-2k-g4-parent-lr2e-6-seed1067

[[ "$(sha256sum "$base_model" | cut -d' ' -f1)" == "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562" ]]
[[ "$(sha256sum "$parent_state" | cut -d' ' -f1)" == "85f06763e776513acca86d5f8b23ea46bfe985a23b4d151c73ede01f833bdaaa" ]]
[[ "$(sha256sum "$data_file" | cut -d' ' -f1)" == "ecbdf7ac67270ba15609f9582b56a1cd4403bd44ab56ac70fc430108c8ad172f" ]]
[[ "$(sha256sum "$manifest_file" | cut -d' ' -f1)" == "b5f960a51a418d45b246bf454a3df8b9c326c0ded66af0e05cb05700a04f3c17" ]]
[[ "$(jq -r '.overall.failure_count' "$validation_file")" == "0" ]]
[[ "$(jq -r '.overall.maximum_tokens' "$validation_file")" -le 2497 ]]
[[ "$(wc -l < "$data_file")" -eq 2000 ]]
[[ ! -e "$proj_dir" ]]

export CUDA_VISIBLE_DEVICES=0
cd "$project_dir"

exec .venv/bin/python train.py \
  --load_model "$base_model" \
  --state_init "$parent_state" \
  --state_init_sha256 85f06763e776513acca86d5f8b23ea46bfe985a23b4d151c73ede01f833bdaaa \
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
  --random_seed 1067 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
