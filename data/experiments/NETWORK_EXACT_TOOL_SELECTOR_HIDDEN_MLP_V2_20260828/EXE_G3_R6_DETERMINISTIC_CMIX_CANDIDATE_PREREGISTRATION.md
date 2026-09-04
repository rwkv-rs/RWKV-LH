# EXE-G3 R6 deterministic CMix 候选预注册

登记时间：2026-08-30（Asia/Shanghai）。本文件在构建候选 extension 和查看候选指标前冻结。

## 已确认根因

固定输入诊断的当前原始 operator 在 `C=4096,F=16384`、32 次重复中产生 32 个 bitwise SHA，
最大相互差 `0.0078125`。CUDA 源中每个 128-feature tile 使用 FP16 `atomicAdd(__half2*)`
写入同一输出，tile 到达顺序不固定。端到端层级 trace 的首个 decode 分歧恰好位于 layer0
CMix 输出，输入仍逐 bit 相同。

## 候选算法与边界

- 只修改通用 B1/T1 `cmix_sparse_down_relu_one` 及其 `_out` 入口，不按样例、prompt、state、
  layer 或模型输出特判。
- 第一 kernel 保留现有 128-feature tile 内的 ReLU-square、稀疏压缩和双 FP16 累加链；每个
  tile 写入独占 `[f_block,C]` FP16 partial，不再 atomic 写共享输出。
- 第二 kernel 按 `f_block=0..F/128-1` 固定顺序使用 FP16 half2 加法归约到最终输出。
- 这选择原算法允许的一种固定 tile 加法顺序；不对 RWKV 文本做解析后修复、截断、删除、
  隐藏或重排，不改权重、state、采样器和协议。
- 原始源码保持不变；候选在隔离 source snapshot 构建，验证通过后才讨论发布替换。

## 冻结身份

- 原 CUDA source SHA-256：
  `23a16dfff498ea6123d1f0278e7a90766721e2a68cd7c804096d9218f24fe09d`。
- 原 extension SHA-256：
  `29631c7d14151129f965c666a5884b10c75b5469688382267f049de3b5df91a8`。
- 候选 CUDA source SHA-256：
  `a092c37533d67b1ddb1f0ca4e101629a26edf37f29ded8ca0d00902361758f95`。
- 候选 kernel test source SHA-256：
  `70efb1086a31c2b81fa855ca7d2d0edd35055a0387d5955f734f790688b65bee`。
- 远端物理 GPU0 UUID：
  `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`。

## 固定验证

1. 使用现有 RWKV venv、`VLLM_BUILD_PROFILE=rwkv`、`VLLM_TARGET_DEVICE=cuda` 在隔离副本构建，
   不覆盖 `/home/chase/vllm-rwkv/vllm/rwkv7_ops.abi3.so`。
2. 运行现有 allocating/out 等价、FP32 reference、prepare-zero graph replay、fake/schema、
   bad-output 测试，以及新增 `C=256,F=4096,16` 次 bitwise deterministic 测试。
3. 固定真实维度 `C=4096,F=16384`、seed `20260830`、同一输入，候选重复 64 次：
   `unique_output_sha256_count` 必须为 1，finite 64/64。
4. 同一进程随后加载原/候选 extension 会发生同名 operator 注册冲突，因此性能比较使用两个
   独立进程、同一输入生成规则、各 10 次 warmup + 100 次同步计时；报告 p50/p95。
5. 候选对 FP32 ordered reference 维持现有测试 `rtol=2e-2,atol=2e-2`；真实维度最大绝对误差
   不高于根因诊断原始 32 次中的最大值 `0.006854534149169922 + 0.001`。
6. 性能初门槛：候选 warm p50 不超过原 operator 的 5 倍且绝对值不超过 0.5 ms。未通过则
   保留候选结果并优化，不能降低确定性或精度门槛。
7. 正式产品 `18070` 构建和测试前后健康；`18075` 不用于 kernel test；不停止其他既存进程。

通过这些只代表 CUDA 候选可进入端到端验证，不代表 R7 或第一正式版本发布通过。
