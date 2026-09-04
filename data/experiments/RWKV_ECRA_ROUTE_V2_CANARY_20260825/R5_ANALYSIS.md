# r5 canary analysis

`variant_b_contract_graph_r5` 是第一轮自然结束并生成完整 `results.json` 的
Contract Graph v2 route canary。它未通过预注册门槛，不能作为采纳结果。

## 固定指标

- first-tool exact：3/7 = 0.4286。
- network decision macro-F1：0.2222（门槛 0.90）。
- web/connector macro-F1：0（门槛 0.85）。
- required-online false-negative：1.0（上限 0.10）。
- local-only network false-positive：0（通过）。
- privacy backend execution：0（通过，无泄漏）。
- privacy policy rejection coverage：0（失败）。
- Strong Planner concrete operation count：0（通过）。

## 根因与范围

1. `EffectCeiling.LOCAL_READ_ONLY` 同时限制副作用与信息来源。Strong Planner
   虽未输出工具名，仍可通过 ceiling 移除网络工具，间接决定是否联网。
2. 即使 `ECRA-ROUTE-056` 得到 public 菜单，v2 benchmark wrapper 把 objective
   写成“exercise applicable branch”，使任意本地观察都可能被 RWKV 当成一条
   可完成分支；它选择了 `list_directory`，随后明确报告任务其实未完成。
3. Planner 为 Controller 自动提供的 network audit 创建了额外 work node，导致
   本地/计算/隐私任务多执行一次无关 local action。
4. finalizer 的 projected minimum_actions=1，迫使终局 RWKV 在回答前额外调用
   一个读取工具。
5. `ECRA-ROUTE-091` 与 `118` 是 Strong Planner HTTP 500，适配器已做两次重试，
   仍 fail-closed 中断；这两例不应被解释为模型路由结果。

## r6 整改

- capability projection v2：只读 ceiling 只约束副作用；信息来源由 RWKV 在
  Controller/系统策略投影后的完整只读菜单中选择。offline 仍从注册表移除网络。
- v1 projection trace 继续可读；新 patch 只提交 v2 source。
- benchmark wrapper v3 要求 work objective 保留原任务语义，禁止 generic route
  objective 和 unrelated local completion，同时禁止 Planner 预选来源分支。
- Strong Planner prompt 明确 network audit 是 Controller evidence，不得创建专用
  work node。
- finalizer minimum_actions=0。

数据集、case、expected sequence、模型、并发、预算和所有门槛不变。
