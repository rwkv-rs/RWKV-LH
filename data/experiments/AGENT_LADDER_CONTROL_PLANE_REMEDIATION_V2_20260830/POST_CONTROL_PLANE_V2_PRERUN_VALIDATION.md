# Post-Control-Plane V2 真实 Harness 运行前验证

## 固定整改证据

- Planner correction namespace：API 5/5 HTTP、strict schema、namespace、append-only compile 全部通过；结果 SHA256 `ccc4b5e7484e56a6fd532b4cbc12d743b865f7e41ae3206af4ec6c83e2ea8f05`。
- Selector eligibility 反事实：同一 283 条 S66 原始 logits，结构不可执行选择由 A 的 122 降为 C 的 0；结果 SHA256 `3a078c8261d0f9592c558d2d66c907980a9f89ac46a2c80a652c167778cb9201`。
- 相关测试：83/83 通过；完整回归第一次为 652 passed / 1 failed，唯一失败是测试用 `atom=None` 的构造兼容问题，已修复；失败项及相关回归随后 21/21 通过。完整回归将在本轮真实 Harness 后再次执行，不把局部复跑冒充完整通过。

## 本轮只改变

1. contract-plan strict schema v7 为 correction/finalizer 分配 revision 新鲜 ID namespace。
2. Selector service request/response v3 保留 25 维原始 logits，只在 Controller 已授权且当前阶段可执行的标签内取 argmax；ABSTAIN 保留。
3. atom 的 `minimum_actions` 在达到前机械排除 `final_answer`。

没有改变 2.9B 模型、S66 Head、13.3B 模型、G3/G6 state、任务、接受器、并发、采样、阈值或相似度口径。

## 固定比较

- 数据与顺序：原 Agent Ladder 10 题，完全相同顺序。
- 比较源：post-lean V1 `results.json` SHA256 `196cf691f1c6babe213dd05f7ed8e9c7aa4e149b5e26903f49327d13b3921778`。
- 主要度量：strict/external/completed；进入 Executor；Planner failure；Selector 总尝试、越权选择、premature final、ABSTAIN；RWKV generation、协议拒绝、动作、成功写入、上下文预算失败；G3/G6 绑定与 run 内 state switch。
- RWKV 原始输出仍逐事件校验文本、SHA256、UTF-8 bytes 与 `postprocessed=false`；绝不修改、删除、重排、隐藏、截断、修复或替换。

## 服务约束

- 远端 Executor 与本地 Selector 均只使用物理 GPU0。
- 实验端口 18075/29613/29621；产品 18070/29610 必须全程健康，不停止产品。
- 实验结束必须清理实验进程并再次验证产品服务。
