# EXE-G3 R6 greedy logprob / eager 根因诊断执行冻结

冻结日期：2026-08-30（Asia/Shanghai）。本文件写入时尚未启动本轮服务或推理。

## 冻结身份

- 预登记 SHA-256：`a71e9003dd32c78ea6e19241eec4d13bc6d64d87d17dc4cc158f70ce613b260c`
- 执行程序 `temp/run_exe_g3_r6_greedy_logprob_eager_diagnostic_20260830.py`
  - SHA-256：`75171bbe1299611f2ebd4c119ce97cb0f761bede024090005ad58b3fa72ed6dd`
- graph launcher SHA-256：`4b9bc8493b44ee92f1d57e125103bacc5684fc8047a3ee1e3d95fbf0f207e38c`
- eager 诊断 launcher `temp/run_remote_exe_g3_eager_diagnostic_vllm_20260830.sh`
  - 本地与远端 SHA-256：`9459421388e5dd9346bd39a27b303e51b0a33a055aa04a2dc5faa9acc0e2235f`
- 固定数据集 SHA-256：`f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee`
- 既有 graph/raw 基线 SHA-256：`fbb2952dfc012be1d3535463b52dd0986dc6d5d6984ae7b601f79da1169d1d45`
- Stage-C helper SHA-256：`739df0e1f9743e79da73e9f8a147c3cbf0893a6253cceefae2a27f4d30c2ae96`

## 启动前检查

- 执行程序通过 Python 语法检查、冻结输入校验和 AST helper 属性校验。
- eager launcher 通过 `bash -n`，已复制至远端固定路径并验证内容摘要。
- 本地输出目录和两个远端新证据目录均不存在；程序拒绝覆盖。
- 远端物理 GPU0 UUID 为 `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`。
- 产品端口 18070 正常，实验端口 18075 空闲。

## 不可变约束

- 严格执行 graph/logprobs5 24 次与 eager/raw 32 次，共 56 请求。
- 除 graph arm 的 `logprobs=5` 与 eager arm 的 `--enforce-eager` 外，模型、state、输入和 sampling
  均与预登记一致。
- concurrency=1、attempt=1；不重试、不修复、不后处理。
- 完整 response body、raw text 与 raw token IDs 必须先 append-only fsync，再进行 logprob 派生分析。
- 不修改、删除、隐藏、重排或诱导 RWKV 原始输出；不改变 R6 门槛；不从本轮直接产生上线结论。

