# S1 step1000 state 注入预检

- 冻结时间：2026-08-28（执行前）。
- checkpoint step1000 只验证本地 vllm-rwkv state 注入路径，不参与最终 checkpoint 或指标选择。
- 固定输入使用 v2.4 第一条 rendered input；模型、引擎、FP16 WKV、batch=1 与正式 hidden 提取相同。
- A：zero profile；B1/B2：同一 step1000 profile 独立重放。
- B1/B2 hidden 必须逐元素相同；A/B1 最大绝对差必须大于 `1e-6`；A/B1 cosine 必须小于 `0.999999`。
- 两轮均不得调用 sampling 或生成 RWKV text；输入 token 数必须相同。
- profile checkpoint 固定 SHA-256 `71e78a06e1116c9d77b7d46057631b05b29054a73c873b1d92c0e732f790df53`；32 个 BF16 state tensors，shape `(40,64,64)` 的完整数值验证由训练完成后的 final validator 执行。

