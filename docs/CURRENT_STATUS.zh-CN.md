# RWKV-LH 当前状态

更新时间：2026-09-04（Asia/Shanghai）

## 结论

最新有效 baseline 是 2026-09-03 的 Agent Capability Ladder：B01-B14、P01-P06 共 20 个 case，成功 `0/20`；P07 在 222/240 calls 时人工停止。1124 次 Selector 决策只有 `list_directory=1044`、`move_file=80`，其余 23 个标签均为 0；有效 trace 合计 2813 次协议拒绝。

根因不是 13.3B 权重整体退化。旧 Selector Head 的 400 条 feature 都从同一个 bootstrap State 独立计算，却宣称 `persistent_history_replayed=true`；在线服务当时持续传递整条 run 的 parent WKV。同时训练输入是显式指出单个工具的孤立模板，在线输入却是完整 `GoalFrontierStateV1`。13.3B 只能填写上游已经锁定的工具参数，无法纠正错误选择；整改前的持久 Executor WKV 又累积旧工具与格式锚点，最终产生大量围栏和重复 Tool Call 输出。

## 当前固定架构

```text
Strong Planner
  └─ nested add_stages / replace_stages / discard_step_ids
       └─ current stage peer steps
            └─ step-revision-local 2.9B Selector: one tool
                 └─ clean-per-action 13.3B Executor: parameters/action/report
                      └─ Harness facts
                           └─ Controller read/write evidence gate
                                └─ clean-State RWKV semantic Audit
                                     └─ Evidence Kernel
                                          └─ Strong Stage Checker: advance/repair
```

阶段协议和阶段检查已经实现；阶段内真实并发尚未实现。当前顺序推进，但每个已选 action 使用干净 Executor State，避免跨工具 WKV 污染。

## 已完成整改

- 产品入口只保留 `stateful_goal`。
- Strong Planner 使用原生嵌套 `GoalPlanPatch`，未完成步骤可真正 replace/discard。
- 阶段内同级、跨阶段依赖、阶段屏障和读写冲突均由内核校验。
- Stage Checker 是同一强模型部署上的独立只读调用，模型只返回 `verdict/gaps/reason`。
- 2.9B 是工具选择唯一权威；13.3B 不再 Top-K 二次选择。
- Selector 使用 G1J `selector-intent.v1` 输入；Head 还必须具备同分布持久因果轨迹身份。
- Selector WKV 只在同一个 `(step_id, step_revision)` 内持续；切换步骤/revision 或 Final 意图时从角色初始 State 重启。
- Executor 一次只接收一个当前步骤、该步骤及直接依赖的有界事实和一个工具 schema。
- Executor 每个新 action 干净启动；同一 handoff 最多修复一次，连续 12 次 action 协议失败后进入 `BLOCKED`，worker 不再自动空转。
- Planner 声明的 read/write roots 不是完成事实；Controller 先用成功 Action 的真实参数做覆盖检查，缺失时直接反馈 Selector，不调用 Auditor。
- Auditor 使用独立 clean State，只判断机械覆盖后的自然语言成功条件；retry 不污染 Executor，WKV 不 merge。
- repair feedback 与 Planner patch 有 durable source link，恢复后不会遗漏未完成修订。
- Planner、Selector、Executor、Auditor 都可通过 `.env` 替换模型配置。

## 当前 G1J 状态

五个 v1 正式角色数据集已生成，State 训练、选中 checkpoint、选中 State 和发布 profile 均仍为 `0`。旧 Selector Head 已因训练/运行轨迹身份错误而淘汰，不能再作为 runtime Head。

## 当前验证

工程整改以 2026-09-03 的完整 trace 为输入；原始 trace 不改写。模型能力必须在新 Selector 轨迹数据和新 Head 冻结后，使用同一 Ladder、参数、阈值和指标重新运行。

## 尚未完成

- 从真实 Goal 链路构造 Selector 的 train/dev/sealed 持久因果轨迹，覆盖多 action、失败、repair、跨 step 和 final；
- 为五个角色补齐固定 evaluator，并重新训练 Selector Head v2；
- 在 v3 架构上重跑固定 Ladder，之后才判断剩余缺口是否需要具体角色的 State Tuning；
- 同阶段安全并发与确定性事实合并仍未实现，不阻塞顺序能力基线。

新的实施与证据登记入口见 [G1J 分环节 State Tuning 冻结实施协议](G1J_STATE_TUNING_AUDIT_HANDOFF_20260902.zh-CN.md)。
