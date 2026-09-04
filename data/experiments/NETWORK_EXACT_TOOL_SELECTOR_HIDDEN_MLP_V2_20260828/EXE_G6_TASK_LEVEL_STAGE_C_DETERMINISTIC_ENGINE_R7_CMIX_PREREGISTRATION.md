# EXE-G6 task-level multi-profile deterministic engine R7/CMix 预注册

登记时间：2026-08-30（Asia/Shanghai）。本文件在 R7 任一模型请求前冻结。

## 问题与唯一变量

R6 在固定 Recovery72 上，G6 专用/多 profile 两种顺序为 72/72 exact；G3 为 71/72，唯一失败
样本在相同输入和 state 下随机生成 43-token JSON 或其 86-token 重复。逐层诊断和独立 operator
诊断已证明根因为 B1/T1 CMix 对跨 feature tile 使用无序 FP16 atomicAdd。

R7 相对 R6 的唯一数值变量是 extension SHA-256 从
`29631c7d14151129f965c666a5884b10c75b5469688382267f049de3b5df91a8` 切换为经过隔离验证的
deterministic CMix candidate
`31b64460dca6bc9d6b73a17120137822ae8b740eb5f3a3ee1fffbb1ea4a00fb1`。模型、G3/G6 state、
profile manifest、evaluator、Recovery72、采样参数、服务参数和阈值保持不变；不启用任何 prefill
或 decode 同步。

## 冻结输入

- R6 结果 SHA-256：
  `22f6f1f642ffb8c8667e09cd40379aa58f47b614ce2edec7c22f6d3a90b1d495`。
- CMix candidate 结果 SHA-256：
  `261a2766e28dd4170a4b2f42c6245b0960d42be31bcc47c1bbecabc6d0ace781`。
- prefill sync 消融结果 SHA-256：
  `862036dac9f0eac6b9804768841f81586bf1b05e111acdc3d5af1973680f30d7`；固定选择 `none`。
- evaluator SHA-256：
  `4b2ed1bfa6c4e693241ea36e1a48e06a39948cc76d77405af4d8f3dd2b281006`。
- G3：`EXE-G3-MULTISTAGE-STEP2000`，SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`。
- G6：`EXE-G6-NETWORK-RECOVERY-STEP1500`，SHA-256
  `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- 物理 GPU0 UUID：`GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`。
- dedicated launchers SHA-256：G3
  `556f9a131fdb4fc373fee2ce0b3b55eefd0ebeddfbf13c7746541bf25cf3d551`，G6
  `93df9d735d6b7d92882a2600e72fe4d380c2e4418d2eb881e5eb44192009a238`。
- multi launcher SHA-256：
  `cde2daffdc4e71c9aa490eaecd8cf035475147fb94c718f80262ab9d5bb1b8be`。

## 固定运行

1. 同一固定 Recovery72，temperature0、seed1067、attempt1、concurrency1、max_tokens256。
2. G3 dedicated 72、G6 dedicated 72。
3. 同一 multi-profile 服务先 G3→G6：144；再 G6→G3：144。合计 432 个正式生成，另有一个
   explicit-zero fail-closed probe。
4. 所有 response body、raw text、token IDs、finish reason 在解析前进入 append-only hash chain；
   derived canonical 只作派生指标。
5. dedicated 与 multi 均使用原 R6 CUDA Graph 配置，不加 `--enforce-eager`；服务运行时必须能从
   `/proc/*/maps` 证明加载的正是 candidate extension。
6. multi engine 使用 R6 task-level overlay 的相同 `envs.py`、`rwkv.py`、test 文件与同一 manifest，
   只在隔离副本替换 candidate source/extension；正式 `/home/chase/vllm-rwkv` 保持原 SHA。

## 固定门槛

- 四个 run 的 transport/envelope/profile pairs 全部成功，hash-chain valid，task 内 profile switch=0。
- 对每个 profile，dedicated、G3→G6、G6→G3 三份证据的共同 72 行必须满足：raw text 72、raw
  token IDs 72、finish reason 72、canonical pass/fail 72 全相等。
- dedicated 质量不得低于 R6：G3 canonical/operation/schema 均至少 41；G6 均为 72。
- multi 相对同轮 dedicated：warm p50 ≤1.25×、p95 ≤1.35×。
- candidate dedicated 相对 R6 dedicated：warm p50 ≤1.10×、p95 ≤1.15×。
- candidate extension 必须在 G3、G6、multi 三种服务中实际映射；正式原 extension/source、state、
  manifest 和产品 `18070` 前后身份不变。
- 所有门槛预先固定；运行后不得改指标、阈值或样本。任一失败都保留 raw 并阻止 canonical engine
  发布。

R7 全门槛通过才允许将该 kernel 作为可回滚的 canonical `vllm-rwkv` 修复；仍不等于联网质量、
Full90 或第一正式版本全门槛通过。
