# RWKV Goal Loop v2 角色隔离整改预注册

日期：2026-09-01

## 目标

在不做 State Tuning 的前提下，先修复已证实的架构职责错位：

1. Strong Model 只作为 Planner；
2. 未完成步骤允许 replace/discard，不再 append-only；
3. 2.9B Selector 只接收当前 frontier，不接收完整多步骤 Goal；
4. 13.3B Executor 每次只执行当前步骤和一个已选工具；
5. Auditor 使用独立干净 State，不继承或合并 Executor WKV；
6. 产品入口只保留 `stateful_goal`，移除旧模式和 State Router shadow 选择。

## 冻结验证口径

- 结构回归：完整 `pytest -q`；通过阈值为零失败。
- 角色输入 gate：Planner schema 不含工具选择字段；Selector wire 不含完整 Goal；Executor 使用当前 frontier 作为 `current_requirement`；Auditor 的 `current_question` 为最后语义字段。
- 因果 gate：旧 step revision 的 action 不能完成替换后的新 revision；Auditor checkpoint 可持久化恢复；Audit retry 不写入 Executor State。
- 产品 gate：CLI、Web API 和 `build_product_controller` 只接受 `stateful_goal`，显式拒绝旧 `contract_graph`、`none` 和 State Router shadow。
- 格式 gate：`GoalPlanPatch` 使用严格 JSON schema；step schema 的 `required` 等于全部公开 properties。

本轮是确定性结构整改，不生成模型文本，因此不伪造相似度指标。模型质量沿用已登记的固定数据、标签、accuracy 和 macro-F1；运行后不得修改阈值。

## G1J 模型复测边界

- 固定权重：G1J 2.9B、7.2B、13.3B，位于 `rwkv-8222:/mnt/nas-model/g1j/`。
- Selector 旧对照：S60/v7 数据与既有 S28、S39、S52、S53、S55 gate。
- v8 改变了输入身份，必须重新抽取同一固定样本的 G1J zero-State 特征并训练匹配 Head；禁止复用或改写 v7 Head 的 portable identity。
- 13.3B/Auditor 实测必须先通过模型身份和 runtime capability 检查。
- 本地 WSL 权重缺失或远端服务未加载目标权重时，结论记为基础设施未就绪，不得记为模型质量失败。

## State Tuning 禁止条件

只要角色正确的 v8 数据尚未完成固定 gate，或错误仍能由输入职责、Head identity、服务配置、协议/持久化 bug 解释，就不启动 State Tuning。
