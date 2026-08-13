# Round1--Round10 反向因果与错误放大分析

## 结论

这 10 轮不是一个瓶颈被逐步解决，而是三个瓶颈串联并发生迁移。最广的断点在执行前：359 个题轮因完整 `satisfies_criteria` 覆盖硬门终止，86 个题轮停在计划 schema/外壳，70 个题轮被 Goal 最多 5 条条件限制终止。进入执行后的 Round1--Round3 主要风险是错误计划/动作被局部验证自证后过早完成；Round4--Round10 又把瓶颈迁到证明协议与证据所有权，正确工作区也无法完成。后期把假阳性压到 0，却不是完整能力提升，因为 Strict 同时降到 0。

分析覆盖固定 90 题的 10 轮共 900 个审计记录。反向路径固定为：外部结果 → 完成门 → 证据/证明 → 绑定协议 → 局部验证 → 动作 → 计划 → Goal。`primary_stage` 是最早**可由已有审计证明**的偏离，不把无法观察的更早语义错误写成事实。

## 十轮结果与瓶颈迁移

| 轮次 | External | Strict | Completed | FP | FN | 请求数 | Prompt tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| R1 | 7/90 | 5/90 | 11/90 | 6 | 2 | 587 | 1236520 |
| R2 | 8/90 | 7/90 | 19/90 | 12 | 1 | 809 | 1732080 |
| R3 | 4/90 | 2/90 | 11/90 | 9 | 2 | 583 | 1210874 |
| R4 | 7/90 | 0/90 | 0/90 | 0 | 7 | 802 | 1738104 |
| R5 | 12/90 | 0/90 | 0/90 | 0 | 12 | 705 | 1398818 |
| R6 | 6/90 | 0/90 | 0/90 | 0 | 6 | 657 | 1318953 |
| R7 | 12/90 | 0/90 | 0/90 | 0 | 12 | 1148 | 2371055 |
| R8 | 12/90 | 0/90 | 0/90 | 0 | 12 | 1154 | 2438389 |
| R9 | 15/90 | 0/90 | 0/90 | 0 | 15 | 1101 | 2443147 |
| R10 | 15/90 | 0/90 | 0/90 | 0 | 15 | 983 | 2092687 |

关键断点：

- 900 个题轮记录的结果分布：`{"blocked_external_wrong": 775, "controller_false_negative": 84, "unsafe_completion": 27, "strict_pass": 14}`。
- 10 轮 External 全错题共 `62` 题；间歇正确 `28` 题。
- 曾经 Strict 通过但到 Round10 回退的题共 `10` 题。
- Round4 以后 FP=0 的直接原因包含 `Completed=0`；因此不能把它单独解释为完成边界已经可用。
- Round9 的单 claim G1i 仍为 0 个规范化绑定；Round10 加入 canonical 外层后已有 50 个规范化调用，说明外壳问题大幅缓解，但 13 个有效事件的 claim 全部未通过 proof，瓶颈已从 JSON 外壳迁移到引用所有权、直接依赖和 JSON Pointer 语义。

## 从最终错误向前回溯的共同链

| 最早可证实阶段 | 题轮数 | 后续结果 | 平均总请求 | 偏离后平均请求 | 偏离后平均完成任务 |
|---|---:|---|---:|---:|---:|
| `plan_coverage_gate` | 359 | `{"blocked_external_wrong": 359}` | 3.429 | 2.345 | 0.0 |
| `action_arguments_or_semantics` | 159 | `{"blocked_external_wrong": 138, "unsafe_completion": 21}` | 20.415 | 12.189 | 4.107 |
| `plan_schema_protocol_gate` | 86 | `{"blocked_external_wrong": 86}` | 3.023 | 1.988 | 0.0 |
| `action_coverage_omission` | 78 | `{"blocked_external_wrong": 77, "unsafe_completion": 1}` | 14.333 | 11.987 | 2.538 |
| `goal_cardinality_gate` | 70 | `{"blocked_external_wrong": 70}` | 2.0 | 0.0 | 0.0 |
| `proof_semantics_gate` | 50 | `{"controller_false_negative": 50}` | 13.64 | 0.42 | 0.16 |
| `external_mismatch_unlocalized` | 36 | `{"blocked_external_wrong": 33, "unsafe_completion": 3}` | 19.722 | 17.417 | 5.5 |
| `binding_protocol_gate` | 16 | `{"controller_false_negative": 16}` | 26.625 | 11.875 | 3.688 |
| `none` | 14 | `{"strict_pass": 14}` | 13.5 | 0.0 | 0.0 |
| `binding_or_claim_gate` | 8 | `{"controller_false_negative": 8}` | 25.125 | 8.0 | 2.375 |
| `obligation_protocol_gate` | 7 | `{"blocked_external_wrong": 7}` | 4.143 | 3.143 | 0.0 |
| `plan_coverage_omission` | 6 | `{"blocked_external_wrong": 4, "unsafe_completion": 2}` | 22.833 | 20.5 | 6.667 |
| `evidence_coverage_gate` | 6 | `{"controller_false_negative": 6}` | 14.167 | 9.667 | 2.167 |
| `completion_gate` | 4 | `{"controller_false_negative": 4}` | 18.25 | 0.0 | 0.0 |
| `plan_protocol_gate` | 1 | `{"blocked_external_wrong": 1}` | 2.0 | 1.0 | 0.0 |

四条最重要的放大机制：

1. **Goal/初始计划输出不满足一次性完整契约 → 无动作 → 外部必错。** 这不是工具能力问题。Round7 的第二次 obligation 规划把覆盖硬门从 Round6 的 49 降到 24，却把请求从 657 增到 1148；后续仍有 24--32 题/轮被同一门挡住，说明同步补全整张图不是稳定解。
2. **计划遗漏 → 动作只实现错误计划 → 局部 verifier 自洽 → 错误完成。** 外部失败目标没有进入任务描述时，后续工具即使全部执行成功也只是在精确实现错误分解。
3. **动作破坏性覆盖/错误参数 → verifier 只验证新写内容 → 丢失约束不可见 → 错误完成。** `action_succeeded`、目标文件存在、甚至对新值的 exact check，都不能证明“保留无关字段/完整集合/跨文件关系”。
4. **工作区正确 → claim 表达失败或引用不合法 → 无 VERIFIED evidence → 完成门阻塞。** 这条链在后期成为主因；增加 prompt 或再包一层 parser 只能改善到达率，不能解决证据所有权。

## 全十轮都错的题

- basic: 8 题；`E2E-B08, E2E-B11, E2E-B12, E2E-B18, E2E-B23, E2E-B24, E2E-B25, E2E-B27`。
  这组 10 轮题轮的最早阶段分布：`{"plan_coverage_gate": 37, "action_arguments_or_semantics": 19, "goal_cardinality_gate": 10, "action_coverage_omission": 10, "plan_schema_protocol_gate": 3, "obligation_protocol_gate": 1}`。
- medium: 27 题；`E2E-M01, E2E-M02, E2E-M03, E2E-M04, E2E-M05, E2E-M06, E2E-M07, E2E-M08, E2E-M09, E2E-M10, E2E-M11, E2E-M13, E2E-M14, E2E-M15, E2E-M16, E2E-M17, E2E-M19, E2E-M20, E2E-M22, E2E-M23, E2E-M24, E2E-M25, E2E-M26, E2E-M27, E2E-M28, E2E-M29, E2E-M30`。
  这组 10 轮题轮的最早阶段分布：`{"plan_coverage_gate": 92, "action_arguments_or_semantics": 89, "goal_cardinality_gate": 29, "action_coverage_omission": 23, "external_mismatch_unlocalized": 17, "plan_schema_protocol_gate": 16, "plan_coverage_omission": 3, "obligation_protocol_gate": 1}`。
- hard: 27 题；`E2E-H01, E2E-H02, E2E-H03, E2E-H05, E2E-H06, E2E-H07, E2E-H08, E2E-H10, E2E-H11, E2E-H12, E2E-H13, E2E-H14, E2E-H15, E2E-H16, E2E-H17, E2E-H18, E2E-LH01, E2E-LH03, E2E-LH04, E2E-LH05, E2E-LH06, E2E-LH07, E2E-LH08, E2E-LH09, E2E-LH10, E2E-LH11, E2E-LH12`。
  这组 10 轮题轮的最早阶段分布：`{"plan_coverage_gate": 119, "plan_schema_protocol_gate": 55, "action_coverage_omission": 28, "goal_cardinality_gate": 26, "action_arguments_or_semantics": 25, "external_mismatch_unlocalized": 11, "obligation_protocol_gate": 3, "plan_coverage_omission": 2, "plan_protocol_gate": 1}`。

这些题应作为下一步的核心训练/消融组，因为它们排除了偶然采样下已经具备能力的情况。需要逐题检查三个不变量：Goal 条件是否完整投影到计划、每个动作是否消费了真实依赖产物、证明是否引用了独立于 producer 输出的 expected source。

## 典型因果链（多环节，不只看终点）

### E2E-H03 / Round1：目录要求在计划阶段丢失，后续七次写入放大

外部六个检查都因为 `/workspace/stages` 不存在而失败；RWKV 的任务图却写入根目录 `stage1.txt` 到 `stage6.txt`。最早可证实偏离是计划未覆盖 `stages/`，随后工具忠实执行错误路径，本地 `file_contains/file_exists` 又只验证这些错误路径，最终形成假阳性。这里先修 verifier 只能阻止错误完成，不能让产物变对；根修复必须发生在 Goal→Task 的覆盖与动作前 invariant review。

### E2E-M01 / Round2：覆盖写丢失无关 JSON 字段，局部新值校验掩盖破坏

外部 `json_equals` 发现原有 `port/threads/theme` 等字段被删除，但动作和本地验证只围绕 RWKV 新生成的 JSON。最早可证实偏离在动作参数/语义阶段，后续 `action_succeeded` 与自定义内容检查无法证明 preservation constraint，最终形成假阳性。需要让 RWKV先读真实 JSON、基于 dependency artifact 产生变换，再以执行前 artifact 为 expected source 验证未改字段；控制器不能替 RWKV补字段。

### E2E-B01 / Round10：工作区已经正确，证明绑定仍把直接依赖选错

外部 `greeting.txt` exact check 已通过，三个任务也完成。Round10 canonical G1i 外壳已被接受，但 T3 的 claim 引用了非直接依赖，proof 被确定性层拒绝，最后 `required_goal_evidence_missing`。这是正确的 fail-closed 行为，却暴露出证据设计被推迟到末端：RWKV在行动时没有持有可复用的 producer/consumer witness plan，事后仅凭复杂候选表重建引用关系。

## 对分阶段改造计划的取舍

| 原计划部分 | 数据后的判断 | 下一步处理 |
|---|---|---|
| Round3 unchanged observation cache | 保留。它减少重复验证，但不是正确率主因；应继续限于确定性、同 digest、同 verifier 的失败。 | 作为效率/恢复基础设施，不再单独期待提升 Strict。 |
| Round4 完成证据边界 | 方向正确，成功阻止早期 6/12/9 个 FP；当前实现一次把完整 proof DSL 和绑定职责压给弱模型，导致 7 轮 Completed=0。 | 保留 fail-closed 和独立 expected source；重做为贯穿计划、执行、验证的 witness lifecycle。 |
| 初始计划不强制一次覆盖 criteria | 需要修正。完全取消覆盖检查会让遗漏一直流到末端；执行前强制拒绝又会卡死。 | 允许增量计划，但必须由 RWKV显式登记每个未覆盖 obligation 及预计 producer；控制器只检查是否登记，不替它分配任务。 |
| Goal 接受 1--16 条条件 | 尚未落实且数据继续支持。10 轮共 70 个题轮被最多 5 条限制终止，完全没有进入计划/动作。 | 独立轮次移除 5 条截断，保留原始条件；超过 16 才让 RWKV做一次显式合并，控制器不替它删条件。 |
| StateCapsule / task-local projection | 强烈借鉴。十轮请求和 token 已很高，Round7 自动补任务还产生大量重复任务。 | 从权威状态确定性生成，不用模型摘要作事实；只投影当前 obligation、直接依赖、可选 evidence handles。 |
| 扩展更多 verifier | 只增加能覆盖已观测共同关系的通用 verifier；不是越多越好。 | 优先 preservation、集合完整性、跨 artifact 等假阳性根因；禁止根据隐藏检查选择 verifier。 |
| 继续增加 G1i 外壳兼容 | Round10 已证明 canonical 外壳可显著提升解析到达率；继续加外壳的边际价值已低。 | 冻结 transparent parser，只保留唯一 name/arguments、无语义补全；资源转向 witness ownership。 |
| Goal obligation 自动补任务 | Round7 出现大量空 ledger、重复 title/description，增加请求却无完成。 | 删除自动语义补任务；错误反馈交给 RWKV修改/追加现有计划，控制器只做 ID、DAG、scope 校验。 |

## 下一步顺序：先解除同步 obligation 硬门，再前置 witness lifecycle

下一轮（建议 Round11）的单变量应是：**把“初始计划必须立即覆盖全部 `satisfies_criteria`，否则同步调用 supplemental planner 并终止”替换为持久化 unresolved-obligation lifecycle。** 结构合法的 RWKV 基础计划先执行；遗漏条件以原文和 Goal digest 进入确定性 StateCapsule。现有可执行任务耗尽后，再由 RWKV看到真实依赖产物和未解决 obligation，决定修改现有计划或追加任务。Controller 只保存状态、检查 DAG/ID/scope，不生成任务、不把 criterion 复制到任务。这个改造同时对应 Prime Agent 可借鉴的状态胶囊与“同状态不重复 gate”，但保持 SQLite 为唯一权威状态。

Round11 若确实让更多题进入动作且不增加 FP，再做独立的 witness-lifecycle 轮次：**RWKV 在计划/修订阶段为 criterion 提出 producer、consumer 和 expected-source 类型；执行阶段系统只为全部真实观察生成不可变 handle；验证阶段仍由 RWKV通过单工具 G1i 选择 handle，确定性层只解析并计算。** Goal 1--16 条条件的解除也应作为独立变量运行，不能与这两项混在同一正式轮次。

具体边界：

- RWKV 决定 criterion 对应哪个任务、需要读取哪个依赖、选择哪个 evidence handle、是否改计划；规则不得自动选最相似/最可能通过的引用。
- Controller 只验证结构不变量：引用存在、是直接依赖或 Goal literal、hash 未变化、操作符类型匹配；不得改 name、arguments、expected、pointer 或最终答案。
- producer 动作执行前，把所有依赖产物按原样注册为 opaque handles；不按标准答案或 verifier 结果筛选候选。
- proof 失败返回精确的机器错误给同一 RWKV recovery（如 `not_direct_dependency`、`pointer_missing`），由 RWKV决定重绑还是修改计划；相同观察不重复 cross-check。
- 诊断时同时看三组：全十轮都错题、Round10 外部正确但未完成题、曾 Strict 后回退题；正式晋级仍跑固定 90 题，恢复 `FP=0`、External/Strict 不回退门槛。

## 可证伪指标

这项改造只有同时满足以下现象才算方向成立：

- Round11 的结构合法基础计划不再因 `satisfies_criteria` 未全覆盖而在执行前终止；每个遗漏 criterion 都原样进入 unresolved obligation，且没有控制器生成语义字段或补任务。
- Round11 的计划覆盖硬门应从 30/90 降为 0/90，并且更多题真实进入 action；如果只换成另一种补计划协议，视为失败。
- 后续 witness 轮次中，每个 required criterion 都有 RWKV 原生的 witness intent，且没有控制器生成 producer、expected 或引用。
- canonical binding normalized rate 提升后，proof-valid claim 也同步提升；如果只有解析率提升，说明仍停留在协议表层。
- Round10 的 15 个外部正确题中至少出现真实 completion，同时 FP 不从 0 回升。
- 全十轮都错题的 External 有提升；若只改善已有正确 Basic 题，则没有修复 Goal→Plan→Action 的根因。
- 每个完成题都能从 Goal digest 追到 task、action raw output、artifact hash、RWKV选择的 handle 和 proof result，最终输出保持 byte-exact raw RWKV。

完整逐题记录、阶段转移、放大量和来源哈希见 `cross_round_backward_causality.json`。
