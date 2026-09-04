# V4 中立分层分析报告

## 结论

本轮没有先框定 Planner、Selector、Executor 或 state 为错因。对冻结的 10 个任务、165 个 atom、482 次选择、453 次 Executor 原始生成逐项对齐后，证据显示首要系统缺口是 **Harness 执行结果没有形成供独立 Selector 使用的结构化契约进度闭环**。

当前 `runtime_projection.v1` 只把上一工具名、成功状态和 outcome type 交给 Selector；atom kind/effect、write-root 覆盖数、剩余义务、依赖证据是否已满足均只对 Executor 可见。独立 state 已存在，但 Selector 的 state 没有得到足够的闭环事实。

## 固定事实

- Strong Planner：80 次调用全部一次 HTTP 完成；2 次语义拒绝均恢复；不存在 action budget 小于 minimum actions 的契约。
- 66 个 mutate atom 中，23 个从未提交 mutation 工具，且这 23 个没有一个完成；其中 19 个直接形成“只读/计算后 final”的事务失败。
- 22 个 atom 在必要 mutation 前选择 final；3 个在覆盖全部 write roots 前选择 final。
- 工具与目标类型存在 18 个 atom 级不匹配：14 次 `write_json` 作用于非 JSON 路径，4 次 `patch_json` 作用于非 JSON 路径；另有 3 次 `read_json` 读取非 JSON 路径。
- Selector 原始记录完整：417 次提交、65 次 ABSTAIN 拒绝；全局 raw argmax 有 219 次为 final_answer。所有 raw logits 和选择身份均原样保留。
- Selector→Executor 交接没有观察到断链：0 次无绑定模型调用。
- Executor：407 次接受、46 次协议拒绝；拒绝包含 29 次非单一 JSON、12 次参数/Schema、5 次其他错误。
- Harness 的 25 次事务拒绝是保护机制生效，不是把错误结果提交成功；另有 6 次 InputBudget 终止需要单独整改。
- 外部验收仍为 10/10 command failure、5/10 文件集合失败、2/2 网络 grounding 失败。

## 分层判断

1. `confirmed_violation`：Harness→Selector 的契约进度投影缺失；真实轨迹不能从“Action 成功”判断“atom 完成”。
2. `confirmed_contributor`：Selector 在当前输入上有稳定的提前 final、ABSTAIN 和 JSON/非 JSON 工具混淆；静态 99.2% 不能代表真实闭环轨迹。
3. `confirmed_contributor`：13.3B Executor 仍有 46/453 协议拒绝和功能内容错误。
4. `not_observed`：选择身份、唯一 Schema 披露和重试继承未再出现断链。
5. `not_observed_as_terminal_root`：本轮未观察到 Strong Planner transport/格式成为终态根因，但 2 次可恢复语义错误仍保留记录。

## 下一步固定消融

- A：现有 `CurrentDirectStageV1`，S66 zero-state。
- B：只增加 Harness→Selector 的最小结构化闭环胶囊，模型/head/state 不变。
- C：B + 2.9B 约 2K state tuning；S66 head 固定。
- D：仅在 B/C 仍出现工具类型混淆时，评估 kind/effect 对候选集的机械投影；不先用候选过滤替代模型能力。

比较使用同一数据集、同一 raw-logit 记录、同一 exact/effect-class 指标和同一外部 Harness 验收。任何 arm 都不修改、删除、重排、隐藏、截断、修补或替换 RWKV 原始输出。
