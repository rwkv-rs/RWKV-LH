# EXE-G3 R6 首轮 decode 指纹诊断预登记

登记日期：2026-08-30（Asia/Shanghai）。登记时 18070 健康、18075 空闲，尚未启动本轮推理。

冻结前序有效结果 `run_exe_g3_r6_prefill_addln_fingerprint_r2_diagnostic/DIAGNOSTIC_RESULT.json`
SHA-256 为 `649573ce1e1c5bf9782acef52869626a21584b97b2b606edeaf90c977e642db4`：8 次
prefill 的 61×TMix、61×CMix、121×Add+LayerNorm 和 complete 指纹全部精确一致，但 raw 仍为
43/86 token 两种、完整 logprob 序列 8 种。因此以该逐 substage 同步作为“已稳定 prefill”的固定前置，
定位每个请求的第一轮 B1/T1 decode。

本轮固定相同 G3 state、物理 GPU0、1328-token 目标、temperature=0、logprobs=5、concurrency=1、
attempt=1，连续 8 次。每次要求：61 个 first-decode TMix、61 个 CMix-from-mixed、1 个 decode
complete、1 个 decode logits 指纹；同时保留前序全部 prefill 事件。

逐层记录 TMix input、fused pre_mix、shift/WKV before/after、output、v_first；记录 CMix mixed input
和 output；记录首轮 decode 总输入/输出与全部 state 前后；最后记录 `project_logits_fp32` 输入与 FP32
logits。分析按 layer 0..60 的 TMix→CMix 顺序找第一个变化字段；若层级全部精确而 logits 首次变化，
定位到 head projection；若 logits 也精确而 API logprob 变化，定位到后续 logits/logprob 管线。

wrapper SHA-256 固定为
`41cf706e191dbc6c4c44ddac082289c7ed1f2ef9463aca4bebd2c3f60bef1790`；启动器 SHA-256 为
`731dbfee2e00278e0cb81bde04d931ee53d9e5bfbb99f0068938d0d446876769`；其稳定 prefill adapter
依赖 SHA-256 为 `4bdf9bde009a3121498366873f93a17c66397793f1f6b689664a9389af3d62ed`。

本轮只定位，不改变 R6/R7 门槛；指纹只读取 tensor。完整 response/text/token/logprobs 先
append-only fsync，不得修改、删除、隐藏、重排或诱导 RWKV 输出。
