# Round55 预注册实验协议：Task 内多动作 Agent Loop

状态：在任何 Round55 代码修改和模型运行之前登记。

## 冻结基线与依据

- 已上传最佳代码：`14d864d71bf670b479a33f4fdb63b4772b69d3c8`。
- Round46：Strict `31/90`、External `32/90`、Agent completed `55/90`、FP/FN `24/1`。
- Round53 同源 pre-action reviewer：Strict `23/90`，已回退。
- Round54 ready-task atomization canary：`0/15`；模型在 B01 等原子 Task 中 199 次提交 `decision=refine`，同时 reason 明说“不需要细化”，已回退。
- 两轮共同说明：不能在 action 前再加独立 judge/meta-decision。现有根约束 `one Task = one action` 才是集合、复合 Task 错误的结构来源。

## 唯一架构变量

复用已经存在、且每个 action 后必经的 RWKV Task postcondition commit，将其决策从 `pass|replan` 扩展为 `pass|continue|replan`：

1. `pass`：当前及历史真实 action observations 已建立整个 active Task postcondition，Task 完成。
2. `continue`：本次 action 成功并对 active Task 产生真实进展，但整个 Task postcondition仍未满足。该 attempt 记为 action 成功；同一 Task 回到 pending，保留全部 memory/output refs/workspace revisions，由 RWKV随后生成下一个完整 Harness action。
3. `replan`：action/evidence 与 Task 冲突、没有有效进展、需要改变 Task/恢复策略，沿用现有失败恢复。
4. Controller 不根据 action 类型、Task 标题、case、路径或输出内容决定 continue；只执行 RWKV 的固定枚举决定。它不拆 Task、不生成成员、不选 action、不补参数、不改 RWKV最终回答。
5. continue 时仅清空已经执行完的 action commitment 和该 action 的 verifier specs；Task contract、依赖、postcondition、全部观察和 artifact lineage 不变。
6. 每个 observation 在产生时固化其真实 producer action；后续 action 不能把旧 observation 重新标成当前 action。同一 Task 的 output refs 累积而不覆盖，后续 action commit capsule包含该 Task此前所有可容纳的真实 action result memory，因此 RWKV 可逐成员/逐阶段推进。这是实现 `continue` 所必需的 provenance 保真，不根据内容判断或修正动作。
7. 全局 `max_transitions=200` 继续是统一终止上限；不增加按标题或 case 的循环规则。失败恢复预算只计算失败 attempts，不把成功 continue action 误算为失败重试。

## 明确不改

- 不修改 Goal、初始 Task DAG、Goal obligation extension、失败 replan 内容、criterion evidence、final answer。
- 不增加模型请求；复用现有 Task postcondition commit。
- 不修改 Harness 工具与 action 参数 schema，不增加格式归一，不读取 hidden acceptance 或 frozen reference。
- 不把 continue 自动改为 pass/replan，也不根据 reason 纠正 RWKV 的 decision。
- 不以请求数、token、延迟作为本轮淘汰条件。

## 因果假设

1. H12/H13/LH11 的“一个 Task 覆盖多个成员”可在同一 Task 中执行 read member 1 → continue → read member 2，而不被错误完成或被 replan 拒绝。
2. M01/M06/M18/H02/LH05 中，一个成员/manifest 不再自动完成整个 Task；RWKV可基于累积 observations继续行动。
3. 原子 Task 的首个 action 已满足 postcondition时仍选择 pass，保持 B01/B02/B10/M03/LH02 等控制组。
4. M04/M21/M24 等错误 mutation 仍可能发生；本变量只检验 action cardinality，不声称解决 effect role 或同源 evidence。
5. 如果 RWKV仍在明显未完成时选择 pass，表现为 FP；如果持续 continue，表现为 transition limit。两者都如实计入质量，不由 controller修正。

## 固定 Canary（运行前冻结）

| Case | 选择原因 |
| --- | --- |
| B01 | 单步写入控制，首步应 pass。 |
| B02 | 既有原子 DAG 控制。 |
| B10 | coding 闭环控制。 |
| M03 | 中等迁移控制。 |
| LH02 | 已原子 15 checkpoint hard 控制。 |
| M01 | 多 service 集合。 |
| M06 | 多文件 copy + manifest。 |
| M16 | primary/fallback 集合。 |
| M18 | 递归 digest 集合。 |
| H02 | 20 shards 聚合。 |
| H12 | 15 shards 单 Task。 |
| H13 | 多文档批 Task。 |
| LH11 | 40 artifact phases。 |
| B24 | 读后计算/写入的复合 Task。 |
| M12 | coding 正确写入不应被旧失败阻断。 |

## 固定验证

1. 单元测试：pass 完成；continue 保存 attempt/memory 后原 Task pending并重新 action selection；replan维持现有失败路径；continue 后第二 action可完成；后继不在 continue 时 ready；恢复预算不把 continue计为失败；事件记录 raw RWKV decision且 Controller不生成语义字段。
2. 完整 offline、LH-Control `30/30`、catalog `90/90`、31 文件架构验收。
3. 固定 15-case canary 后逐条检查所有 continue/pass/replan、Task action history和 outcome变化。
4. canary 出现相对 Round46 的质量信号且控制组未系统退化，才运行完整 E2E-90；否则回退。
5. E2E-90 后按固定 analyzer和人工逐题报告比较 Round46。

## 保留与上传门槛

- Strict `>31/90`；
- FP `<=24`、FN `<=1`；
- Basic/Medium/Hard 完整报告；
- 全部离线/架构回归通过；
- final output raw/delivered 字节一致；
- 无 case 特判、无 controller Task/action/答案选择或修改。

未满足则回退 Round55 源码/测试，只保留实验与分析，不上传为最佳架构。
