#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 9 ]]; then
  echo "usage: $0 DATA_FILE PARENT PARENT_SHA RUN_DIR STEPS STEP_SAVE LR_INIT LR_FINAL SEED" >&2
  exit 64
fi
data_file=$1
parent_state=$2
parent_sha=$3
proj_dir=$4
steps=$5
step_save=$6
lr_init=$7
lr_final=$8
seed=$9
project_dir=/home/chase/chase/RWKV-PEFT
base_model=/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth

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
  --epoch_steps "$steps" \
  --epoch_count 1 \
  --epoch_save 1 \
  --step_save "$step_save" \
  --lr_init "$lr_init" \
  --lr_final "$lr_final" \
  --lr_schedule cos \
  --warmup_steps 40 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed "$seed" \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla
