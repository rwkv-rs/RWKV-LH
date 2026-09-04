# AtomExecutionContract B 臂剩余失败归因协议 V1

## 目的

在不改变既有 A/B 指标、阈值或原始输出的前提下，对固定 B 臂的 10 个 Agent Ladder
任务、全部原子 worker 因果状态和外部验证结果做分层归因。诊断必须区分：

1. 工程投影、状态绑定或上下文预算造成的能力抑制；
2. 2.9B Selector 的工具选择/停止能力；
3. 13.3B Executor 的参数、格式、变更和验证能力；
4. Planner/Reviewer 的图闭环与证据闭环。

本协议只读取原实验目录。SQLite 必须以 `mode=ro&immutable=1` 打开，禁止调用可能追加
恢复事件的 `LongHorizonStore.load()`。

## 固定输入

- 实验：`ATOM_EXECUTION_CLOSED_LOOP_ABLATION_V1_20260830`；
- 臂：`run_b_contract_progress_v1`；
- 用例：固定 Agent Ladder 10，不增删；
- 执行冻结摘要：`9d107b1c8c2454d4aef0c49f3c8acf5a57a92ab4e904abc5f3626b7442bffc46`；
- B 臂 `results.json` 摘要：`2f2369153ee69bad7a1bfc1da5fa024cf523e6664ed38adb25ccc024171207f1`；
- 相似/比较口径：结构计数、精确身份 join、精确字符串类别和固定比例；不使用主观评分。

## 固定指标

### 工程层

- `input_budget_error_count`：原 outcome 中精确的 `InputBudgetError` 数量；
- `dependency_handoff_chars_legacy/current`：对所有依赖边按旧投影和当前统一投影重放后的
  canonical JSON 字符数；
- `dependency_projection_source_unchanged`：投影前后完整 outcome canonical JSON 是否一致；
- `external_results_over_18k`：完整网络结果 canonical JSON 大于 18,000 字符的动作数；
- `legacy_external_evidence_lost/current_external_evidence_kept`：固定旧 ResultCapsule 降级逻辑与
  当前统一投影是否保留至少一个 evidence record；
- `review_termination_reason`、patch/review/replan 数量和全原子完成但顶层中断数量。

### 2.9B Selector

- committed selection、ABSTAIN、operation 分布；
- selected label 在 eligible labels 内的重算 softmax 概率与 top-1/top-2 logit margin；
- 同一原子连续选择同一 operation 的次数；
- `deadline_nonmutation_selection`：mutation atom 在
  `remaining_action_budget <= remaining_required_count` 且尚未 completion-ready 时，仍选择非路径变更
  operation 的次数；这是由固定 ContractProgress 推出的必然事务失败，不使用理想答案标签；
- final selection 在选择时是否由固定 eligible labels 允许。

### 13.3B Executor

- accepted/rejected decision 数量及精确 error 类别；
- 非 final selection 产生 accepted Action 的比例；
- accepted path mutation 的成功、workspace changed、write-root coverage 数量；
- JSON/Schema/参数类拒绝数量；
- 外部 verifier 通过用例数。

### Planner/Reviewer

- graph patch/review/replan/stagnation/correction-repeat 计数；
- Reviewer 可见的外部 evidence 投影保留率；
- 所有原子 outcome completed 但顶层仍中断的用例数。

## 固定诊断触发条件

- 工程整改未完成：任一 InputBudgetError、任一完整外部 evidence 被 Reviewer 投影整体丢失、任一
  contract/selection/decision/action 身份 join 漂移；
- 2.9B 定向 state tuning：任一 `deadline_nonmutation_selection`，或 ABSTAIN 率大于 1%，或
  eligible top-1 margin 不高于 0.5 的比例大于 15%；
- 13.3B 定向 state tuning：Executor rejection rate 大于 5%，或 accepted mutation 的 write-root
  coverage 小于 90%，或固定外部 verifier 通过率小于 80%；
- Planner/Reviewer 闭环整改：任一“全部原子 completed 但顶层 evidence stagnant/correction repeated”
  用例，或统一投影后 Reviewer 仍不可见已提交外部 evidence。

这些触发条件只决定下一步归因与数据构建，不替代最终发布门槛。运行后不得修改。

## 不干预声明

- 不修改、删除、重排、隐藏、截断、修复或替换任一 RWKV raw output；
- 不改原 A/B 目录、audit、worker 数据库、模型身份或 state profile；
- 当前投影重放只生成新的诊断产物，并记录源码和产物 SHA-256；
- 凭据值不进入诊断产物。
