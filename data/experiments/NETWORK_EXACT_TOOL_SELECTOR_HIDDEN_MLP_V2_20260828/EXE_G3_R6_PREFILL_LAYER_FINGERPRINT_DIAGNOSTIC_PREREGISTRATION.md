# EXE-G3 R6 packed-prefill layer 指纹诊断预登记

登记日期：2026-08-30（Asia/Shanghai）。登记时远端 18070 健康、18075 空闲，本轮未启动推理。

## 冻结前提

终态指纹结果 `run_exe_g3_r6_prefill_terminal_fingerprint_diagnostic/DIAGNOSTIC_RESULT.json`
SHA-256 为 `8104480d4207a535e4c752340668b13003aae7548d8b17ca3e6cb34460ef9d23`。
16 次目标请求的 prefill input、v_first、elapsed 各只有一个精确 SHA-256，而 output hidden、shift、WKV
各有 4 个，完整 raw 仍为 43/86 token 两种。因此 packed-varlen prefill 内部是已证实的问题范围。

## 固定执行

- base model、G3 state `EXE-G3-MULTISTAGE-STEP2000`（SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`）、物理 GPU0、
  原 state adapter、`fp32io16`、native sampler、`--enforce-eager` 保持不变。
- 固定 source index 455、sample `EXEG6-25d90fc447d18b7b1bc63d0356ab`、1328-token prompt；
  temperature=0.0、top_p=1.0、top_k=0、seed=1067、logprobs=5、concurrency=1、attempt=1；
  连续请求 8 次。
- 对 61 层逐层记录 `tmix_varlen` 的输入、TMix shift/WKV 前后、输出及 v_first 的精确字节
  SHA-256；记录 `cmix_varlen` 的输入、CMix shift 前后和输出 SHA-256；记录完整 prefill 输入/输出。
- 指纹只读取 tensor，不改写模型 tensor 或输出。每次读取会产生同步，因此本轮同时观察“逐 substage 同步是否
  令输出稳定”；若稳定，只能判为缺少同步/流顺序候选，不能直接判定某一数学算子正确。
- wrapper SHA-256 固定为
  `74a1dbc0b6548b62087fac04032401ac552d39a3ebdac38fa496c5b4bc75ecb6`；启动器 SHA-256 固定为
  `c2f6a8184cda164be5c3112eb8df390c6df0026489feb62afc66dcccb8bd9765`。

## 固定分析顺序

对 layer 0..60 按以下顺序找第一个 unique SHA-256 数大于 1 的字段：TMix input、TMix shift/WKV
before、TMix output、TMix shift/WKV after、CMix input、CMix shift before、CMix output、CMix shift after。

- 若在某层输入与 state-before 均唯一、但 TMix output/state-after 首次变化：进入该层 TMix 内部
  projection/WKV 子阶段诊断。
- 若 TMix 全部唯一、而 CMix output/state-after 首次变化：进入该层 CMix 内部诊断。
- 若 8 次所有 layer/substage 均唯一且 raw/token/logprobs 也唯一：逐 substage 同步是稳定化候选，下一轮
  做 TMix-only 与 CMix-only 最小同步消融。
- 若所有指纹唯一但 raw 仍变化：进入 prefill→decode 边界或 decode 诊断。
- 事件数不是 8×61 TMix、8×61 CMix、8 complete，或输入指纹变化，则本轮无效。

本轮只做根因定位，不调整已登记 R6/R7 门槛，不作为上线通过。response body、raw text、token、
logprobs 先 append-only fsync，再分析；不得重试、后处理、修改、删除、隐藏、重排或诱导 RWKV 输出。
