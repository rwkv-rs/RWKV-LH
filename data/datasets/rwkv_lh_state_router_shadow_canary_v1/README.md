# RWKV-LH State Router Shadow Canary v1

- 来源：State Router 设计稿中的 final/local/deterministic/web/connector/mixed/OOD 边界。
- 版本：`rwkv-lh.state-router-shadow-canary.v1`。
- 用途：阶段 1 Shadow 基础设施的真实 Controller canary；不是训练数据，也不能作为有机流量结论。
- 规模：8 个固定请求；每个请求通过主 RWKV、真实 Harness 和旁路 State Router 完整执行。
- 生成：人工登记固定边界；运行前冻结，不根据 canary 输出改标签或样本。
- 权威说明：`expected_*` 只评价 Router 的固定 canary 分类；主模型的实际 Action Ledger 仅作行为对照，不是真值。
