#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/chase/chase/RWKV-PEFT
base_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
parent_state=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g3-multistage-request-last-2k-zero-lr2e-5-seed1055/rwkv-step-2000.pth
data_dir=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_executor_true_workflow_g4_2k
data_file="$data_dir/rwkv_state_tuning.train.requires_target_suffix.jsonl"
manifest_file="$data_dir/manifest.json"
validation_file="$data_dir/remote_training_contract_validation.json"
proj_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g5-g3-continued-true-workflow-2k-lr5e-6-seed1063

[[ "$(sha256sum "$base_model" | cut -d' ' -f1)" == "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562" ]]
[[ "$(sha256sum "$parent_state" | cut -d' ' -f1)" == "9f22ce1ef1b71a157f966e4abeb1ef0ef67014bc9fd26f86106857f23b01e016" ]]
[[ "$(sha256sum "$data_file" | cut -d' ' -f1)" == "5bb2e09f4e9f109438acadc703c3ccb1d49051fee5db0b548e9584e26910e593" ]]
[[ "$(sha256sum "$manifest_file" | cut -d' ' -f1)" == "ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f" ]]
[[ "$(jq -r '.overall.failure_count' "$validation_file")" == "0" ]]
[[ "$(wc -l < "$data_file")" -eq 2000 ]]
[[ ! -e "$proj_dir" ]]

export CUDA_VISIBLE_DEVICES=0
cd "$project_dir"

exec .venv/bin/python train.py \
  --load_model "$base_model" \
  --state_init "$parent_state" \
  --state_init_sha256 9f22ce1ef1b71a157f966e4abeb1ef0ef67014bc9fd26f86106857f23b01e016 \
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
  --lr_init 5e-6 \
  --lr_final 5e-7 \
  --lr_schedule cos \
  --warmup_steps 40 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed 1063 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
