#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/chase/chase/RWKV-PEFT
load_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
data_file=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_executor_state_tuning_v2_2k/rwkv_state_tuning.train.requires_target_suffix.jsonl
proj_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-exe-g1-v2-2k-zero-lr2e-5-seed829
expected_model_sha=5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562
expected_data_sha=c081d47641d475719d495a0bf3b941f497877eeee2ed85c619a5645a5f7359f7

[[ "$(sha256sum "$load_model" | cut -d' ' -f1)" == "$expected_model_sha" ]]
[[ "$(sha256sum "$data_file" | cut -d' ' -f1)" == "$expected_data_sha" ]]
[[ "$(wc -l < "$data_file")" -eq 2000 ]]
[[ ! -e "$proj_dir" ]]

export CUDA_VISIBLE_DEVICES=0
cd "$project_dir"

# EXE-G1-V2 is deliberately initialized from native zero.  There is no
# --state_init or continuation checkpoint in this command.
exec .venv/bin/python train.py \
  --load_model "$load_model" \
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
  --random_seed 829 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
