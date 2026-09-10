# StateTune 管线现状

更新日期：2026-09-10，当前工程轮 `OFFICIAL_PLANNER_TRACE_REPAIR_R1_20260910`。官方 DeepSeek 完整 UltraData R5 为 Strict 0/3、completed 0/3、mutation 0、动作 1：2 题高思考耗尽输出，1 题角色协议拒绝。后续工程修复已完成扩展工具重建及标签校验、显式思考配置和失败证据记录；完整回归 **1414 passed、0 skipped**。真实 optimizer steps 仍为 0，固定 3+12 题将重新采集。完整状态见 [HANDOFF](HANDOFF.zh-CN.md)。

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
| Native 数值训练后端 | 当前唯一 `statetune_native_model` / `statetune_native_recurrence`；共享 `RWKV7Layout`，2.9B zero/非零 State 全词表对齐、16384 token 反向及冻结底模核验通过 |
| 正式数据消费 | `scripts/run_state_tune.py freeze` 重新从生产 trace 抽取并核对完整候选清单，原子发布 train 与固定 regression；训练入口仅解析 train |
| 优化器训练入口 | `scripts/run_state_tune.py train`：完整源码/模型/数值兼容登记、State-only AdamW、真实 step 与中断日志、候选导出及同一服务 loader 校验；机制单测不计实际角色训练 |
| 固定角色回归 | `scripts/run_state_tune.py evaluate`：当前阶段 Selector，从持久化快照调用同一输入 builder、Native 服务及生产三菜单投票；固定 dev/confirmation 同时比较 zero/候选，逐菜单与最终投票都不得退化 |
| 当前角色 State 改善 | 未训练、未得到新 State，也没有修复后 Agent 提升证据 |

当前数据接口与文件字段详见 [生产 trace 使用说明](ROLE_TRACE_DATASET.zh-CN.md)。测试 mock、作者参考实现和私有验收不能填充正式角色数据数量。

评测规则须在优化器之前登记。Selector 同时报告菜单准确率、完整三菜单组准确率、服务失败与未运行数量；缺少的菜单不补造、不额外调用，不完整组单独报告。zero 已达标且候选没有改善时优先保留 zero 作为该阶段基线。角色合格只决定是否进入下一阶段采集，评测器始终不宣称 Agent 正式保留通过。后续角色的语义评测必须沿用既有独立复核标准，不能把 Selector 的分类评分直接套给 Auditor 或 Finalizer。

## 按角色推进，不以 Agent 达标作为训练前提

Selector 先学习正确工具选择；足够数据和本阶段验证条件满足后训练。固定合格 Selector 后继续真实参数填写与执行，收集 Executor 的失败恢复与正确执行，再依次推进 Step Auditor、Finalizer、Final Auditor。每一步只要求当前角色的预注册覆盖；未到达后序角色会减少那些角色的数据，不会使前序角色自动无效。

历史 R7 停在首次目录观察后的错误控制分支；随后控制流整改后的真实采集又暴露旧网关与数值 State 边界问题。后者已通过真实 GPU 的精确前缀、重试与重启验证，仍需新完整任务验证后续角色。训练所需的“合格 trace”指输入、原始输出、State、因果与标签可信，并不要求任务已经成功；语义错误可以在同一真实边界复核纠正。只有缺失关键原始事实或矛盾的来源不能靠补造恢复。

Agent Strict、完成率、mutation 和终止原因持续观察；最终组合仍按既有 Agent 验收和消融决定是否保留。只换目标 State 的阶段比较与整个 Agent 是否达标分别登记。

## 历史 StateTune 与当前政策

项目过去确实存在 StateTune 数据入口、角色训练及 State 记录。旧合成数据生成器、旧协议和旧 State 已清理，历史事实不会因删除文件而消失，也不应恢复成当前的第二套架构。按具体冻结提交在 Git / GitHub 查询即可；不在工作树重建 retired/archive 或兼容入口。

历史盘点涉及旧 G1i 的 27 个 WKV 训练族和当前 G1J 不完整的逐 run 证据；这不能直接相加，也不能推导当前次数为零。[历史对账报告](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/TRAINING_ROUND_ACCOUNTING_REVIEW.zh-CN.md) 的 SHA 为 `19111348578a9380617e8cd9d825f385050c761143493a97d11d9946a81599a8`，其中旧额度政策已被 2026-09-09 owner 决定替代，历史报告保持原样。

**固定三轮上限已取消。** 后续依据预注册指标、最大 steps/时间/资源预算和真实训练 run 管理，不再使用“剩余轮次”。每个 run 绑定模型/词表/协议/数据/训练器 SHA、初始化 State、实际更新 steps、日志和输出 State，失败与中止同样记账。具体字段见 [训练管理记录](../data/experiments/STATETUNE_ENTRY_REPAIR_R1_20260909/TRAINING_POLICY.json)。

## 架构判断与模型升级

当前拆分把操作选择、参数执行和语义判断分开，适合定位并分阶段训练。已经发现的根因主要是 Controller 错误中断、自动标签权威过强和证据记录不足；尚不能从未调用的后序角色断言角色划分失败。多次菜单求值及每动作审计的成本可以在固定条件下消融评估，不因一次低分新增 Head、替代模型或平行状态机。

通用性来自稳定的角色合同与 State/模型适配边界。新 RWKV 首先核验模型、tokenizer、State 形状/精度、上下文、生成/停止与服务能力，复用当前 builder 和数据消费接口；需要调整的训练器适配也须有 SHA 与验证记录。只有语义合同确实改变才替换协议，旧实现从工作树删除、历史留 Git。本轮从权重读取低秩/FFN/State 几何，去掉原 13.3B 尺寸假定；2.9B 在当前 head64、BF16 权重、FP32 State / FP16 token Native 后端已通过数值兼容验证。未验证的几何/后端仍明确拒绝，不能自动复用旧 State，也不能将兼容验证写成角色训练改善。
