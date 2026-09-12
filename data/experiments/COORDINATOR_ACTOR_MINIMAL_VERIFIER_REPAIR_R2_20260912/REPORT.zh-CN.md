# COORDINATOR_ACTOR_MINIMAL_VERIFIER_REPAIR_R2_20260912

## Agent 级结果

固定 `realprojectdevv1` 12 题、固定参数、单次真实模型运行结果为：**Strict 0/12、completed 0/12、external passed 0/12、mutation 5、动作 55**。49 个动作成功、6 个动作失败；5 次写入分布在 RP-API-01（3 次）和 RP-WEB-02（2 次）。没有错误宣称完成，也没有外部通过但系统拒绝完成的样本。

全部 12 题状态均为 `interrupted`。终止原因为：`identical_success_budget_exhausted` 5 题、`protocol_rejection_budget_exhausted` 4 题、`identical_failure_budget_exhausted` 1 题、`supervisor_review_unavailable` 2 题。候选可行性门要求至少 1/12 Strict 且 completed，并保持零错误完成；本轮未达到，不能切换生产架构。

| 任务 | 动作（成功/失败） | mutation | Runner 协议拒绝 | 终止原因 |
|---|---:|---:|---:|---|
| RP-API-01 | 7（7/0） | 3 | 12 | protocol_rejection_budget_exhausted |
| RP-API-02 | 4（4/0） | 0 | 12 | protocol_rejection_budget_exhausted |
| RP-MAINT-01 | 1（1/0） | 0 | 12 | protocol_rejection_budget_exhausted |
| RP-MAINT-02 | 13（8/5） | 0 | 0 | identical_failure_budget_exhausted |
| RP-CLI-01 | 2（2/0） | 0 | 2 | supervisor_review_unavailable |
| RP-CLI-02 | 3（3/0） | 0 | 1 | identical_success_budget_exhausted |
| RP-DATA-01 | 4（4/0） | 0 | 0 | identical_success_budget_exhausted |
| RP-DATA-02 | 5（5/0） | 0 | 1 | identical_success_budget_exhausted |
| RP-FULL-01 | 3（2/1） | 0 | 12 | protocol_rejection_budget_exhausted |
| RP-FULL-02 | 4（4/0） | 0 | 4 | identical_success_budget_exhausted |
| RP-WEB-01 | 4（4/0） | 0 | 2 | identical_success_budget_exhausted |
| RP-WEB-02 | 5（5/0） | 2 | 3 | supervisor_review_unavailable |

## 两项修复的验证

新增的两个回归测试先在 `aa5f4b51` 上分别复现 R1 原始失败：Coordinator 计划直接抛出 `ValueError: steps must be non-empty`；失败的 `list_directory` 被结构化分页投影器执行 `json.loads("")` 后抛出 `ObservationProjectionError`。修复后两个测试通过，相关四个测试文件共 **143 passed**，完整回归为 **1504 passed、0 failed、0 skipped，252.77 秒**。

Coordinator 修复没有猜测、映射或补写模型字段。它把 `SupervisorPlan.create` 的确切本地校验错误交回同一个 Coordinator，在已有 `semantic_repair_attempts` 内要求重新生成完整规范对象。真实运行中 11/12 题至少需要一次修复，共 25 次 plan 请求、13 次语义拒绝，最终 12/12 都取得合法计划并进入 Actor。R1 的 `supervisor_plan_unavailable` 从 10 题降到 0，证明该修复在真实链路生效。

Observation 修复让失败的 `list_directory/search_text` 不再进入成功结果的 JSON 分页解析器，而是通过既有有界通用投影返回 `success=false`、`outcome_type` 和 Harness 错误。确定性测试使用真实 Harness 在文件路径上调用 `list_directory`，验证错误可被投影为 Actor observation。R2 没有出现 Runner observation 投影崩溃；但随机真实轨迹没有再次执行 R1 那个完全相同的错误调用，因此真实运行只能证明“没有再崩溃”，不能算同一触发的第二次现场复现。

R1 到 R2 的可见变化是：进入 Actor 的题数从 2 增至 12，动作从 14 增至 55，mutation 从 0 增至 5；Strict、completed 和 external passed 仍全部为 0。两轮包含随机模型生成且没有成对重复运行，这些数字用于工程故障定位，不作为候选优于产品架构的因果结论。

## 每次模型调用的真实输入规模

RWKV 共 129 次生成，全部是唯一 `LANE:ACTION`，没有独立 Selector、Step Auditor、Stage Checker、Finalizer 或 Final Auditor 调用。下表的 Actor 输入来自每条 `raw_generation.prompt_token_ids` 的实际长度，记录标记为 `full_context`；输出来自实际 `raw_token_ids`。Native State 每次只 append 新 event，`static_replay_tokens=0`，但表中仍能看到该 State 对应的累计完整上下文大小。

| 任务 | Actor 调用 | Actor full-context tokens（最小–最大） | 输出打满上限 | Coordinator plan prompt tokens | Final review prompt tokens |
|---|---:|---:|---:|---|---|
| RP-API-01 | 21 | 4,173–21,629 | 12 | 556, 630 | — |
| RP-API-02 | 17 | 3,682–21,702 | 0 | 568, 642 | — |
| RP-MAINT-01 | 14 | 4,552–10,114 | 0 | 904, 978 | — |
| RP-MAINT-02 | 14 | 4,265–22,104 | 0 | 998, 1,072 | — |
| RP-CLI-01 | 5 | 3,829–6,808 | 1 | 426 | 3,238 × 2 |
| RP-CLI-02 | 5 | 3,365–9,989 | 0 | 429, 503 | — |
| RP-DATA-01 | 5 | 3,648–11,222 | 0 | 444, 518 | — |
| RP-DATA-02 | 7 | 3,476–10,722 | 0 | 428, 502 | — |
| RP-FULL-01 | 16 | 4,792–9,709 | 9 | 856, 930 | — |
| RP-FULL-02 | 9 | 5,330–14,341 | 0 | 972, 1,046, 972, 1,046 | — |
| RP-WEB-01 | 7 | 4,157–11,785 | 0 | 740, 814 | — |
| RP-WEB-02 | 9 | 4,294–13,715 | 1 | 762, 836 | 6,676 × 2 |

Actor 的累计输入最小 3,365、最大 22,104、均值 10,442、中位数 8,990、P90 20,605 tokens；26/129 次达到或超过 runtime doctor 登记的 `max_model_len=16384`。Native 路径当前明确跳过确定性 rollover，因此这个现象需要单独消融；它与长轨迹退化相关，但本轮不能仅凭相关性断言为唯一因果。

Actor 实际输出最小 17、最大 1,800、均值 474 tokens；23 次命中长度上限，23 次全部被协议拒绝。每次追加的新 event 为 82–2,600 tokens，均值 918，总计 118,379。Coordinator 的 25 次 plan 输入为 426–1,072 tokens，均值 743；4 次 final review 输入为 3,238–6,676，均值 4,957。Coordinator 总请求 29 次。

## 新暴露的系统性缺陷

第一，Actor 直接选择工具和参数的边界已经真实运行，但协议能力不足。官方 runner 统计 61 次协议拒绝；原始事件为 62 次，额外 1 次是终止候选边界的拒绝事件。23 次是输出长度耗尽。其余高频错误是模型使用了当前 schema 不存在的参数：`write_file.target` 11 次，`read_file.end_byte` 9 次，`read_file.max_bytes/max_lines` 等组合 15 次。Controller 没有替模型改名或补参数，这是正确的证据边界，也意味着该问题必须在 Actor 的协议能力、State 或可验证的输入设计上解决，不能通过参数别名掩盖。

第二，执行循环仍会重复。55 个实际动作只覆盖 `list_directory` 9 次、`read_file` 41 次、`write_file` 5 次；5 题重复成功动作耗尽，RP-MAINT-02 对失败的读取重复到失败预算耗尽。简化架构证明循环不是由三次 Selector 投票单独造成的。静态一次性计划没有给未充分训练 agent 场景的 RWKV 提供短期当前目标；失败 observation 虽然进入同一 State，模型仍无法稳定转向。

第三，Minimal Verifier 没有完成一次合法 review。RP-CLI-01 和 RP-WEB-02 产生 final candidate 后各调用 review 两次，但 `review_final` 直接把非规范结构交给 `ReviewDisposition`，得到 `ValueError: '' is not a valid ReviewDisposition`；Controller 的 pending retry只是重复完整请求，没有把本地校验错误交回 reviewer。两题都以 `supervisor_review_unavailable` 中断。该缺陷与 R1 的 create-plan 缺陷同类，应在下一轮按相同方式修复并单独保留先失败再通过的回归。

## 架构判断和下一步方法

`Coordinator + RWKV Actor + Harness + Minimal Verifier` 仍是更合理的职责边界，但当前实现的“Coordinator 一次性给整项计划，随后长期静态 Actor 循环”不适合这个尚未训练大量 agent 场景的 RWKV。下一候选应让强 Coordinator 管理**粗粒度里程碑**：初始时给一个当前里程碑；仅在里程碑被 Actor 明确报告完成、Verifier 拒绝或通用循环断路器触发时，根据不可变需求和 durable Harness ledger 给出下一个里程碑。Coordinator 不输出工具名、参数或业务文件内容。

每个里程碑内仍只有一个 RWKV Actor，直接生成 operation 和完整 arguments；Harness 执行并返回真实 observation。到里程碑边界建立新的 Actor State，输入当前小目标、必要约束和由 Harness 绑定的精确证据，避免一个 State 无界累积；不得用自由文本摘要替代 durable ledger。Minimal Verifier 只判断当前里程碑或 final candidate 是否有足够公开证据，返回 pass/revise 和具体缺口，不改写答案、不选择工具。

工程顺序应是：先给 `review_final` 增加与 plan 相同的有界语义修复；再预注册“静态整项 plan”与“Coordinator 粗粒度里程碑”两臂，固定这 12 题、参数、评分和两遍噪声测量。Actor 的未知参数和长 JSON 截断必须作为独立指标；在没有训练授权的前提下只做输入/State 生命周期消融，不启动 StateTune。正式保留仍要求 Agent 级 Strict/completed 达门，不能用角色 schema 100% 或零错误完成替代。

本轮没有修改生产入口、评分或验收；没有训练、新建 dataset 版本、部署、读取 Holdout 或 push。R1 结果保持原样，没有重评分。
