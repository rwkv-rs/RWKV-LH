# V4 分层中立分析协议

日期：2026-08-30

## 目的

在不预设错因的前提下，对同一批冻结的真实 Harness 轨迹逐层还原事实，再决定是否以及修改哪一层。候选层包括 Strong Planner、能力投影、2.9B Selector、选择到执行的交接、13.3B Executor、Harness/事务控制和外部验收；允许多个层共同贡献，也允许证据不足而不归因。

## 冻结输入

- `REAL_HARNESS_V4_EXECUTION_FREEZE.json`：`ff747ba6089dcd8de92127f11b5e1960d4a877b5fd35da983337331da06092f9`
- `run_s66_g3_g6_post_semantic_handoff_v4/results.json`：`ca9fd84197a8a52f4be77cf7bf7a4be99b77fe400010815de78918ed15f03a5a`
- `run_s66_g3_g6_post_semantic_handoff_v4/BASELINE_RESULT.json`：`74cbc27a72f139c672c66f369bde82e7fe377a0845535ae9143455e77d0ff0da`
- `run_s66_g3_g6_post_semantic_handoff_v4/RUN_PROTOCOL.json`：`53ed4289b235388c77425f030fefbaeb09cec033fb69c201605711e094e9b5d1`
- 运行前协议：`POST_SEMANTIC_HANDOFF_V4_PRERUN_VALIDATION.md`，分析开始时摘要为 `8c3aae01e1eab29a392a4a52b1077d606a00f0c7026469fa1f94be220fce526e`

分析只读上述已冻结运行，不重新采样，不修改任务、阈值、外部验收或原始输出。

## 固定事实口径

1. Planner：HTTP 尝试、finish reason、结构/语义拒绝、恢复与终态失败逐项计数。
2. 能力投影：按审计中的 atom 契约记录 kind、effect、候选工具数、action budget、minimum actions、读写根数量及可行性；不把“候选多”本身判成错误。
3. Selector：读取 worker 数据库中的原始选择记录，验证 logits/label/selection_id 完整性，按 atom 对齐选择序列、ABSTAIN、final_answer 和工具类别。
4. 交接：selection_id、唯一 schema 披露、重试继承和 Executor 调用一一对应；无绑定调用单独计数。
5. Executor：原始生成逐字节校验；协议拒绝、参数/Schema 错误、Action 成败与 workspace_changed 分开计数。
6. Harness：事务完整性、InputBudget、停滞、重复纠正、状态切换和终止原因分开计数。
7. 外部验收：只使用冻结 benchmark 的原始检查结果，不改变判定标准。

## 归因规则

所有结论使用以下四种状态，禁止从最终失败反推单一错因：

- `confirmed_violation`：该层存在直接、可复核的契约或运行违规证据。
- `confirmed_contributor`：该层的可观察行为直接阻断了当前原子的必要进展，但不能据此声称是唯一根因。
- `not_observed`：本次测量未观察到该类违规；不等于该层已被证明完美。
- `undetermined`：现有轨迹不足以区分相邻层责任。

固定的结构判定如下：

- mutate 原子若 `action_budget < minimum_actions`，记为 Planner/契约不可行；若没有此事实，不因根数量多而直接归咎 Planner。
- mutate 原子在完整预算/终止前从未提交任何 mutation 类工具且没有成功 mutation，记为 Selector 轨迹的进展阻断贡献；允许前置读取，不把单次 read 选择单独判错。
- 已选择 mutation 工具但 Executor JSON/Schema 未通过，记为 Executor 协议违规；工具选择是否语义最优若无 oracle 则保持 `undetermined`。
- mutation Action 已执行但失败或未覆盖写根，记录动作层事实；只有在 selection、arguments、action result 和契约写根能够对齐时才进一步归因。
- final_answer 在未满足原子必要条件前结束，按直接证据分别记录 Selector 过早终止、Executor final 内容和 Harness 提交门，不能合并为一个错因。
- verify/check 失败首先是外部功能失败事实；没有产物变更链和命令证据时，不指定是 Planner、Selector 还是 Executor 内容质量。
- Harness 正确拒绝不完整事务属于保护机制生效，不把“拒绝发生”本身判为 Harness 缺陷；InputBudget、状态丢失或错误终止另行验证。

## 原始输出保护

- 不修改、删除、重排、隐藏、截断、修补或替换 RWKV 原始输出。
- 分析产物只保存计数、哈希、枚举标签和结构摘要；不复制 Planner 正文、Selector 提示词或 RWKV 原始生成。
- 任一后续修改必须在本协议分析完成后另立冻结与回归记录。

## 后续决策门

1. 先完成全部 10 个任务、全部 atom、全部同类事件的对齐。
2. 只有 `confirmed_violation` 或可重复的 `confirmed_contributor` 才进入代码/数据/state 修改候选。
3. state tuning 不被预设为修复手段；若证据指向 Selector/Executor 的稳定模型行为，再使用固定数据集先做 zero-state 对照与消融。
4. 修改后使用同一 benchmark、同一外部验收、同一指标复测；不得为改善结果改变口径。
