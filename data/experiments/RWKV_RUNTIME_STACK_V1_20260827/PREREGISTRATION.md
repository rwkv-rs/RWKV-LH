# RWKV Runtime Stack v1 验证预注册

本验证只判定部署、数值兼容和端到端连接，不重新评价 State Router 的真实路由准确率，也不改变
阶段 1 未毕业结论。

## 固定输入

- vllm-rwkv commit：`67f0c5996c50dca0ad779da545cb491527de988f`；
- build profile：`rwkv`，`unrestricted=false`；
- Torch：`2.11.0+cu128`；
- 固定 Router test：`rwkv_lh_state_router_2k_v1/test.jsonl`，300 条；
- 固定参考：阶段 0 入选 B 方案的 `predictions.test.jsonl`；
- 固定 head/PCA：`STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827`；
- 置信度漂移上限：`0.05`。该值高于阶段 0 已记录的最大批次漂移 `0.048895`，本轮不得调整。

## 通过条件

1. 300/300 条的 context、phase、route、network、state profile、abstain 和原因完全一致；
2. model hash/head hash 完全一致；
3. 最大 head confidence 绝对差不超过 0.05；
4. 健康证明明确报告 reduced `rwkv` profile 和 Torch `2.11.0+cu128`；
5. Runtime Manager 不停止未拥有的远端服务或既有 SSH 隧道；
6. 一条真实 Controller Shadow 链完成 Router HTTP、13.3B、Harness 和 final；
7. 新增定向测试和完整工程测试通过。

吞吐和延迟只报告，不作为本轮选择阈值。真实分类毕业仍使用
`STATE_ROUTER_STAGE1_SHADOW_V1_20260827` 的独立协议。

