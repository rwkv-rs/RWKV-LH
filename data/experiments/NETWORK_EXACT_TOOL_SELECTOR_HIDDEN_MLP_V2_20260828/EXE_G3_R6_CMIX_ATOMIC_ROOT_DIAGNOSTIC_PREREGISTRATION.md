# EXE-G3 R6 CMix 原子归约根因诊断预注册

登记时间：2026-08-30（Asia/Shanghai）。本文件在运行诊断、查看本诊断输出之前冻结。

## 目的

直接检查当前 `vllm-rwkv` 已编译的
`rwkv7_fast_ops_fp16::cmix_sparse_down_relu_one`：在输入、权重、GPU、流和调用参数完全相同的
情况下，B1/T1 13.3B 实际维度输出是否逐 bit 稳定。该诊断只调用原始 CUDA operator，不启动
模型服务，不解析、替换、删除或重排任何 RWKV 文本输出。

## 固定输入与环境

- 远端：`rwkv-8222`；物理 GPU0，UUID
  `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`。
- Python：`/home/chase/.venv-vllm-rwkv-8e90d04ecb/bin/python`。
- 已编译 extension：`/home/chase/vllm-rwkv/vllm/rwkv7_ops.abi3.so`，运行前记录 SHA-256。
- CUDA 源：`csrc/libtorch_stable/rwkv7/rwkv7_fast_ops_fp16.cu`，运行前记录 SHA-256。
- 固定 `C=4096`、`F=16384`、dtype FP16、seed `20260830`、重复 `32` 次。
- `preact = randn(F) * 0.25`，`value_fc = randn(F,C) * 0.05`；张量只生成一次。
- 每次调用原始 allocating operator 后立即同步并复制原始 FP16 bit pattern 到 CPU，计算 SHA-256。
- 正式产品 `18070` 在诊断前后必须健康；实验端口 `18075` 必须为空闲；不停止其他既存进程。

## 固定指标与解释

- `unique_output_sha256_count`：32 次原始 FP16 输出的不同 bitwise SHA 数。
- `max_abs_diff_vs_first`：其余输出相对首个输出的最大绝对差，仅作量级记录，不替代 exact 指标。
- 若 `unique_output_sha256_count > 1`，则直接确认该 operator 在固定输入下非 bitwise deterministic，
  与端到端首个 decode 的 layer0 CMix 首分歧证据构成因果闭环。
- 若等于 1，只能说明本次独立调用未复现，不能推翻端到端层级证据。
- 指标、维度、重复次数和解释在运行后不得修改。

## 完整性门槛

必须同时满足 GPU UUID 正确、32/32 调用完成、所有张量 finite、extension/source 身份已记录、
产品 `18070` 前后健康、`18075` 未被占用。失败时保留原始诊断结果并标记 invalid，不补跑后改口径。
