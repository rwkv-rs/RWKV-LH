# EXE-G3 R6 packed-prefill Add+LayerNorm 指纹诊断预登记

登记日期：2026-08-30（Asia/Shanghai）。登记时 18070 健康、18075 空闲，尚未启动本轮推理。

冻结前序结果 `run_exe_g3_r6_prefill_layer_fingerprint_diagnostic/DIAGNOSTIC_RESULT.json`
SHA-256 为 `ac08a4588382c125ceb376996d830f999c5cf8671a9eac01e2122ce0669d01b3`：8×61
TMix、8×61 CMix 与 8 个 complete 事件全部有效；layer 0–47 已观测 TMix/CMix 字段均只有一个
SHA-256，首个变化字段是 layer 48 TMix input（2 个 SHA-256）。layer 47 CMix output 仍唯一，故需要
检查其间的 residual `x` 与 `add_layer_norm_f16` 两个输出，不能直接把根因记到 TMix 48。

本轮固定沿用上一轮的逐 TMix/CMix 指纹同步，并额外包装所有 121 次 `add_ln`：对每次调用的 input x、
input residual、output x、output normalized 记录精确字节 SHA-256。偶数 ordinal `2L` 是 layer L
TMix 后的 LN2，奇数 ordinal `2L+1` 是 layer L CMix 后通往 layer L+1 的 LN1。固定相同 G3 state、
物理 GPU0、1328-token 目标、temperature=0、logprobs=5、concurrency=1、attempt=1，连续 8 次。

wrapper SHA-256 固定为
`8e8173afc4519d4243783fd0e7fb5981d1043bef16f3a07c036c16026adf0eaf`，其冻结 layer-wrapper
依赖 SHA-256 为 `74a1dbc0b6548b62087fac04032401ac552d39a3ebdac38fa496c5b4bc75ecb6`；启动器
SHA-256 为 `7ffe62d12a745360ec9f611bbf6293c25c2076d2501988569368ac74ac6d73bd`。

分析按 ordinal 0..120 查第一个 unique SHA-256 数大于 1 的字段：input x、input residual、output x、
output normalized。若两个输入唯一而输出首次变化，确认该 Add+LayerNorm 调用为根因边界，并对
`rows=1328,C=4096,dim=2` 实现做独立复现/修复；若输入先变化，则沿第一个变化的 residual owner
继续回溯。若所有 Add+LayerNorm 唯一且输出稳定，只能判同步稳定化候选。

本轮只定位，不改变质量门槛。所有原始 response/text/token/logprobs 先 append-only fsync；wrapper
只读取 tensor，不修改、删除、隐藏、重排或诱导 RWKV 原始输出。
