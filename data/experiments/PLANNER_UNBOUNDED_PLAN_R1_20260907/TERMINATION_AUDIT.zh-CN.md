# GoalLoop 完成条件只读审查

2026-09-07；范围为移除 Planner 数量上限后的当前 `rwkv_lh/` 与普通单元测试。未修改生产或测试，未调用模型，未读取 Holdout / acceptance。源码版本见 `TERMINATION_AUDIT_SOURCES_SHA256SUMS.txt`。本报告仅报告代码审查与已有测试断言，不宣称另跑了验证。

**未发现当前新建 v4 GoalLoop 通过步骤数、阶段数、action 数或“计划暂时走完”直接提前标记成功的路径。** 数量上限已移除，真正完成仍需要 RWKV Final Auditor 明确接受 Finalizer 候选。有限资源预算仍可能让运行中断或阻塞，这些状态没有完成权限。

生产入口 `rwkv_lh/product_runtime.py:164` 创建 `StatefulGoalLoopController`，使用其覆盖的 `run()`。父类的其他模式不能直接当作本次 GoalLoop 的结束逻辑。

| 检查点 | 当前行为 | 源定位 |
| --- | --- | --- |
| `steps` 为空 | `batch_complete` 为 false；循环调用 Planner 获取工作，不生成 Final。即使丢弃全部未完成步骤，也不会利用空集合真值直接通过。 | `goal_loop_protocol.py:1146`；`stateful_goal_loop.py:2202` |
| 当前所有步骤已审计完成 | 仅表示 `batch_complete`。`complete` 还要求全部已登记 obligation 的 required_phases 有已接受的步骤证据覆盖。 | `goal_loop_protocol.py:1142`、`:1152` |
| 当前计划走完，但 obligation-phase 尚未覆盖 | 向 Planner 请求 continuation，随后继续执行；不是完成。 | `stateful_goal_loop.py:2428` |
| frontier 为空，但计划未完成且不属于上述 continuation | 抛出 `acyclic rolling plan has no executable frontier`，没有 Final 或 `run_completed` 分支。 | `stateful_goal_loop.py:2439` |
| 已完成一个或多个阶段 | 先处理已有 repair，再检查每个未检查的完成阶段；Stage Checker 返回 repair 时先补计划。阶段数不是完成阈值。 | `stateful_goal_loop.py:2387`、`:2400`；`:1939` |
| 准备 Final | 只有 `plan.complete` 才调用 Finalizer；Finalizer 自己再次要求 complete 和非空 completed_step_ids。Finalizer 只产生候选，事件明确 `completion_authority=False`。 | `stateful_goal_loop.py:2447`；`model.py:772`、`:783`、`:845` |
| 尝试打开 pre-final | 再次重建 plan 并要求 complete；因此即使其他 lane 提前输出 `final_answer`，也不能跳过义务覆盖门。 | `stateful_goal_loop.py:1056`、`:1070`、`:2548` |
| Final Auditor 检查 | 单独 RWKV Final Audit session，输入不可变 goal、全部 completed step 记录、已接受 evidence 与具体候选；允许 `repair/ready_for_final`。要求候选以证据完整回答原始 goal，并保留目标未证明、候选遗漏/无依据等 gap。 | `model.py:1043`；`goal_state_protocols/auditor_final.py:56`、`:176`、`:221` |
| 实际写入 completed | 读取已接受的 pre-final decision；只有 audit 为 `READY_FOR_FINAL` 才保存原候选文本并写 `RunStatus.COMPLETED` 和 `run_completed`。这是当前 GoalLoop 唯一的新完成写入点。 | `stateful_goal_loop.py:2254`、`:2264`、`:2288` |

这不是“步骤多于或等于某个数就结束”。`not open_step_ids` 是要求已承诺工作都完成；`bool(steps)` 和非空 completed 是阻止空计划终结。它们是必要条件，不能代替义务覆盖和最终审计。步骤完成也不是单看 action 调用成功：Step Auditor 接受后仍检查 evidence 的存在、动作成功、目标根、phase 和执行分配，参见 `goal_loop_protocol.py:1615`、`:1689`；Final 审计必须引用已被完成步骤接受的成功证据，见 `:1746`。

| 数量或资源边界 | 耗尽结果 | 源定位 |
| --- | --- | --- |
| 每次调用的 `max_transitions`（产品默认 200） | `_yield(..., controller_slice_exhausted)` → `run_interrupted`，空 Final、`resumable=True`。transition 包含规划、审计、动作等，不等同于 action 数。 | `product_runtime.py:86`；`stateful_goal_loop.py:2187`、`:2806`、`:2834` |
| 相同失败 / 相同无变化成功、协议拒绝、相同 Final repair、无效审计循环 | `_block` → `run_blocked`，空 Final、`termination_permitted=False`，只允许显式恢复。 | `stateful_goal_loop.py:2454`、`:2613`、`:2644`、`:2792`、`:2808` |
| 输入预算无法容纳必要材料 | `model_input_budget_unresolvable` → blocked，不产生简化版成功结论。 | `stateful_goal_loop.py:2690` |
| 模型传输或 Strong Planner / Stage Checker 不可用 | interrupted，可恢复，不是 completed。 | `stateful_goal_loop.py:1390`、`:1975`、`:2065`、`:2727` |

durable state 按不同事件恢复为 COMPLETED / INTERRUPTED / BLOCKED，见 `rwkv_lh/schema.py:1238` 起；没有把资源耗尽映射成 completed。`run()` 开头对已有 COMPLETED 结果的幂等返回（`:2091`）读取的是既存完成事件，不是新判断步数。

**仍需保留的边界说明。**

- `uncovered_obligation_phases` 的无 obligations 分支仍返回空集合，源码明确为旧于 v4 的计划保留历史 batch-completion 行为（`goal_loop_protocol.py:1155`）。这是实际存在的旧回放兼容边界，不能声称已完全清理；当前生产 Planner 首轮会额外拒绝无 obligations（`supervisor_openai.py:2978`），所以不能把它等同于当前新 v4 运行已发生提前完成。
- obligation-phase 覆盖是机械必要条件，不是对任意自然语言结果的充分证明。它只累计已审计步骤绑定的 obligation 与 phase；Planner 若遗漏义务，或 Step Auditor 误判，同类步骤的数量再多也不能自动发现语义遗漏。因此 Final Auditor 必须检查原始 goal；移除数量上限不改变此职责，也不能据此声称模型已能可靠完成任务。
- Final Auditor 返回 repair 时会记录 `goal_final_rejected`，关闭该候选边界并重新进入循环，不写 completed（`stateful_goal_loop.py:2264`）。当前 `_pending_action_repair_feedback` 只消费 action 边界的 Step Audit repair（`:1699`）；在没有其他待修复工作时，完整计划会再次进入 Finalizer。若 Final gap 实际需要新增工具工作，仅重写候选可能无效，重复相同 gap 最终 blocked。这是可见的恢复能力局限，**不是**数字条件绕过 Final Auditor 或隐式成功路径，本次未整改。

已有普通测试覆盖义务欠缺时继续规划（`tests/test_stateful_goal_loop.py:803`、`:1904`）、无效 Final 不可直接完成（`:2961`）、Finalizer/Final Auditor 顺序与完成权限（`:3347`）、预算耗尽状态（`:3753`、`:3800`、`:3890`）、Final repair 在完成前发生（`:4041`）、阶段 repair 遇上游中断后的恢复（`:4642`）。本轮新大计划测试另外覆盖 6/19/64 步、较大完成阶段，以及扩大计划后仍拒绝非法依赖和根冲突（`tests/test_goal_planner_plan_size.py`）。
