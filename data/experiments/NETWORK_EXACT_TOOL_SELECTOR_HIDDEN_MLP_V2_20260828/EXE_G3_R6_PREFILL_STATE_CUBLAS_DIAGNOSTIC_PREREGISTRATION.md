# EXE-G3 R6 prefill state / cuBLAS 根因诊断预登记

登记日期：2026-08-30（Asia/Shanghai）。登记时 18070 健康、18075 空闲，本轮尚未启动服务或推理。

## 已冻结结论

`run_exe_g3_r6_greedy_logprob_eager_diagnostic/DIAGNOSTIC_RESULT.json`（SHA-256
`10982f45ce6923204df1768314cd5d53a8ae015d06ef98fa999227a90fd106b4`）证明：

- graph/logprobs5 24 次仍有两个 raw variant（43 token 16 次、86 token 8 次）；
- token index 42 的 selected token 24/24 均为 top-1，排除 temperature=0 sampler 未按 argmax；
- eager/raw 32 次仍有两个 variant（43 token 25 次、86 token 7 次），排除 CUDA Graph 为必要条件；
- 第 0 个生成 token 的 selected logprob 已在重复请求间变化，范围约 `3.10e-6`，所以漂移在 prompt
  prefill 完成时已经存在，而不是第 42 个 decode 才首次产生。

目标仍固定为 source index 455、sample `EXEG6-25d90fc447d18b7b1bc63d0356ab`、prompt
SHA-256 `006194134f225089cbad9242065c1e3f4f05ca8387c9cd2bff54027b27eae1a2`。

## 固定三臂

三臂全部使用同一 base model、G3 state `EXE-G3-MULTISTAGE-STEP2000`（SHA-256
`13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`）、物理 GPU0、
`--enforce-eager`、logprobs=5、concurrency=1、attempt=1、temperature=0.0、top_p=1.0、
top_k=0、seed=1067、max_tokens=256。每臂连续请求目标 24 次；总计 72 个新请求。

1. `sync`：在原 state adapter 完成每次 tuned row 初始化后执行全设备同步；逐元素验证 WKV row 与
   冻结 initial state 完全相等，并验证 shift/elapsed 为零。cuBLAS 环境保持原状。
2. `cublas`：使用原 state adapter，不增加同步；在进程创建前固定
   `CUBLAS_WORKSPACE_CONFIG=:4096:8`。
3. `sync-cublas`：同时启用上述 state 同步/逐元素验证和 cuBLAS workspace 配置。

远端原 state adapter SHA-256 固定为
`be0523b8abb557b8cdbbc22c4cc8dd927b2d07d675afba25b8702897a485bec2`；诊断 wrapper SHA-256
固定为 `1033d61a8ab6d5c0ffd4cb33b7b513cd072fc86b663d9e88d01b538ecaa01fa1`。远端原 RWKV
state/model/sampler 与关键 CUDA 源分别固定为：

- model state `24dc28626ee34b2e93231b67a72dce9c20ac765ede5194c053b39d743ac47c3a`；
- model `e7980ffba01a303fd939e6d042007bbc924e62fc5297bae786edb64f8632e87e`；
- sampler `20b10fa9390bed3041908fab8317e18ec1653d56e90106b64efb26bac2b00751`；
- v3a ops CUDA `08c288b1790434022a9007d24ffc419fc2b0d135d13fae0d4b16d74884e09389`；
- FP32 WKV CUDA `dfa2f2c3b30f248b869ced64337f9d3e6578ebf927d389fb2626781107c02954`。

## 固定分析与解释

每臂比较 raw text/token variant 数、完整 `token_logprobs` 序列数、第 0/42 token logprob 范围和
state attestation。程序还必须从运行进程环境验证实际 PYTHONPATH 与 CUBLAS 配置。

- 仅 `sync`（以及 `sync-cublas`）变为单一 raw/token/logprob variant：state row 初始化同步为根因。
- 仅 `cublas`（以及 `sync-cublas`）变为单一 variant：prefill GEMM 确定性为根因。
- 两个单独臂仍漂移但组合臂稳定：两项缺陷叠加。
- 三臂都漂移且同步臂的 state 逐元素验证全部通过：排除 state 初始化与该 cuBLAS workspace 配置，
  后续进入 packed-varlen prefill 自定义算子的逐层重复性定位。

本轮只定位根因，不产生上线通过结论，不改变 R6 72/72 门槛。完整 response body、raw text、raw
token 与 logprobs 必须先 append-only fsync，再分析；不得重试、修复、后处理、修改、删除、隐藏、
重排或诱导 RWKV 原始输出。

