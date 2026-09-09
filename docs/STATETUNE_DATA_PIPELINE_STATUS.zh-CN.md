# StateTune 管线现状

更新日期：2026-09-09，整改轮 `STATETUNE_ENTRY_REPAIR_R1_20260909`。Agent 最近完整实测仍为历史 R7 双臂各 Strict 0/12、completed 0/12、mutation 0；本轮未新增模型成绩或训练 run。完整状态见 [HANDOFF](HANDOFF.zh-CN.md)，代码证据见 [整改报告](../data/experiments/STATETUNE_ENTRY_REPAIR_R1_20260909/REPORT.zh-CN.md)。

## 当前具备的能力

| 环节 | 当前状态与唯一入口 |
|---|---|
| 生产架构与 State 注入 | 当前 Controller v7、五角色独立 State/会话；生产与数据使用同一输入 builder |
| trace 采集与来源核验 | durable 请求边界、原始生成、SQLite/导出因果一致性、完整源码与模型/State 身份 |
| 角色候选抽取 | `role_trace_dataset_v1 register/extract`，支持 all-zero 与冻结前序 State 的 role-stage |
| 失败与语义复核 | 保留真实失败上下文；待复核队列；双人绑定原始输入/输出/可见证据的纠正目标，原始 token 不修改 |
| 数据审计 | 固定 family 切分、byte 5-gram cosine、当前角色预注册覆盖；上游 State 与回归身份固定 |
| 完整输入 token | 可保存并证明服务器返回的 full input/BOS；未返回或仅有 delta 的来源仍标未证明 |
| 正式角色数据 | 本轮未创建 `data/datasets/` 版本，没有合格生产样本量或冻结回归的新增结论 |
| 优化器训练入口 | 本地 `rwkv_lh/`、`scripts/` 尚无已验证的当前训练驱动；需接通并登记匹配实际 backend 的训练器，抽取器本身不训练 |
| 当前角色 State 改善 | 未训练、未得到新 State，也没有修复后 Agent 提升证据 |

当前数据接口与文件字段详见 [生产 trace 使用说明](ROLE_TRACE_DATASET.zh-CN.md)。测试 mock、作者参考实现和私有验收不能填充正式角色数据数量。

## 按角色推进，不以 Agent 达标作为训练前提

Selector 先学习正确工具选择；足够数据和本阶段验证条件满足后训练。固定合格 Selector 后继续真实参数填写与执行，收集 Executor 的失败恢复与正确执行，再依次推进 Step Auditor、Finalizer、Final Auditor。每一步只要求当前角色的预注册覆盖；未到达后序角色会减少那些角色的数据，不会使前序角色自动无效。

R7 停在首次目录观察后的错误控制分支，第二个动作还没有发生。修复该控制流使后续动作可以发生，但不能据此预报后序模型已经正确。训练所需的“合格 trace”指输入、原始输出、State、因果与标签可信，并不要求任务已经成功；语义错误可以在同一真实边界复核纠正。只有缺失关键原始事实或矛盾的来源不能靠补造恢复。

Agent Strict、完成率、mutation 和终止原因持续观察；最终组合仍按既有 Agent 验收和消融决定是否保留。只换目标 State 的阶段比较与整个 Agent 是否达标分别登记。

## 历史 StateTune 与当前政策

项目过去确实存在 StateTune 数据入口、角色训练及 State 记录。旧合成数据生成器、旧协议和旧 State 已清理，历史事实不会因删除文件而消失，也不应恢复成当前的第二套架构。按具体冻结提交在 Git / GitHub 查询即可；不在工作树重建 retired/archive 或兼容入口。

历史盘点涉及旧 G1i 的 27 个 WKV 训练族和当前 G1J 不完整的逐 run 证据；这不能直接相加，也不能推导当前次数为零。[历史对账报告](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/TRAINING_ROUND_ACCOUNTING_REVIEW.zh-CN.md) 的 SHA 为 `19111348578a9380617e8cd9d825f385050c761143493a97d11d9946a81599a8`，其中旧额度政策已被 2026-09-09 owner 决定替代，历史报告保持原样。

**固定三轮上限已取消。** 后续依据预注册指标、最大 steps/时间/资源预算和真实训练 run 管理，不再使用“剩余轮次”。每个 run 绑定模型/词表/协议/数据/训练器 SHA、初始化 State、实际更新 steps、日志和输出 State，失败与中止同样记账。具体字段见 [训练管理记录](../data/experiments/STATETUNE_ENTRY_REPAIR_R1_20260909/TRAINING_POLICY.json)。

## 架构判断与模型升级

当前拆分把操作选择、参数执行和语义判断分开，适合定位并分阶段训练。已经发现的根因主要是 Controller 错误中断、自动标签权威过强和证据记录不足；尚不能从未调用的后序角色断言角色划分失败。多次菜单求值及每动作审计的成本可以在固定条件下消融评估，不因一次低分新增 Head、替代模型或平行状态机。

通用性来自稳定的角色合同与 State/模型适配边界。新 RWKV 首先核验模型、tokenizer、State 形状/精度、上下文、生成/停止与服务能力，复用当前 builder 和数据消费接口；需要调整的训练器适配也须有 SHA 与验证记录。只有语义合同确实改变才替换协议，旧实现从工作树删除、历史留 Git。数据管线已经共享这些边界，但没有当前 backend 的真实训练/回归记录之前，不能宣称跨版本训练兼容性已验证。
