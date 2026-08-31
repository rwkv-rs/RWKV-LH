#!/usr/bin/env bash
set -euo pipefail

project_dir=/home/chase/chase/RWKV-PEFT
base_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth
parent_state=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-stage1-selector500-cont-r1-lr5e-5-seed827/rwkv-step-500.pth
parent_sha=180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8
data_file=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_state_tuning_stage4_balanced_boundary_v1/rwkv_state_tuning.train.requires_target_suffix.jsonl
proj_dir=/home/chase/chase/RWKV-PEFT/out/g1i-13.3b-rwkv-lh-stage4-balanced1140-cont-stage1-lr1e-5-seed830

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
  --data_shuffle 1 \
  --vocab_size 65536 \
  --n_layer 61 \
  --n_embd 4096 \
  --ctx_len 2496 \
  --micro_bsz 1 \
  --accumulate_grad_batches 1 \
  --epoch_steps 1140 \
  --epoch_count 1 \
  --epoch_save 1 \
  --step_save 285 \
  --lr_init 1e-5 \
  --lr_final 2e-6 \
  --lr_schedule cos \
  --warmup_steps 40 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed 830 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
