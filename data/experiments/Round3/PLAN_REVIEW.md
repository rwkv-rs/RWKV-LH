# 分阶段改造计划审查：基于 Round1–Round3 因果数据

审查日期：2026-08-12

审查对象：用户提供的《RWKV-LH 分阶段改造计划》。本文件是运行后架构分析，不进入 RWKV
输入，不读取计划来改变 Round3 的任何模型决定。

## 结论

计划的主判断正确：当前主要瓶颈是 Goal 完成证据和初始 obligation 协议，不是工具数量。
但不应原样把所有项目塞入 Round4–Round6；部分内容需要收紧不作弊边界，部分应拆成独立轮次。

| 计划项 | 决定 | 数据和边界 |
| --- | --- | --- |
| 相同失败 observation 不重复 cross-check | 保留 Round3 实现 | Round2 有 5 次历史重复；Round3 实际准备 42 个、登记 8 个有效失败，但重复/抑制为 0，因此本轮没有可归因收益。 |
| `EvidenceRef`、`CriterionClaim`、Task 成功与 Goal 成立分离 | P0 借鉴 | Round2 有 12 FP、63 条 criterion evidence，其中 34 条由 read-only action 持有；这是完成边界的直接根因入口。 |
| expected 与 producer 输出独立、producer/subject ownership、证据失效与最终重验 | P0 借鉴 | Round2 的 FP 外部失败以 `json_equals` 12 次、`file_content` 2 次、`aggregate_shards` 2 次为主；现有 `file_exists`/自生成 expected/RWKV 自检不能证明目标正确。 |
| 完整通用 `ProofExpr` DSL | 缩小后实验 | 只能执行 RWKV 明确选择的 ref/operator；程序不得从 criterion 文本自动合成 proof。第一版不一次加入全部算子。 |
| 删除 legacy `satisfies_criteria <- goal_criteria` 回退 | 借鉴，独立轮次 | 回退把“与 criterion 相关”混成“直接满足”。删除后缺失必须保持空，不由程序补声明。 |
| 初始计划不强制一次覆盖全部 required criterion | 借鉴，但在完成证据边界之后 | Round2 有 43 题、Round3 有 46 题在执行前因此拒绝。若先放宽而没有可靠 obligation/evidence 边界，会扩大错误完成面。 |
| Goal 级 obligation recovery | 借鉴，和证据边界拆轮 | 只能由 RWKV提出新增/修正任务；无新任务、证据或 workspace 变化时阻塞。程序不能生成修复任务。 |
| Goal criterion 上限从 5 扩展到 16 | 借鉴，独立轮次 | Round2 实际是 **9 题** 超过上限，不是计划所写 8 题：6 条条件 6 题，7/8/9 条各 1 题。不得静默截断。 |
| Deterministic StateCapsule | 借鉴，后置 | 必须由 Goal/Task/Evidence/Recovery/artifact hash 确定性生成；自由摘要只作索引，不能作事实或完成证据。 |
| Artifact index / Repo Map | 条件借鉴 | 只作输入视图，记录纳入/排除项；当前因果数据尚未证明“找不到文件/符号”是前两大瓶颈，不和 criterion cap 同轮。 |
| 剩余 G1i 外壳归一 | 借鉴，精确拆分 | 3 题仅多顶层 `type=function`；1 题是单元素 `tool_calls` 但随后仍有参数错误；另 1 题没有真实工具名，必须拒绝。 |
| 同一已选工具的一次错误反馈 | 借鉴，和外壳归一拆轮 | 可以把真实 schema 错误原样作为 `Function output` 交回 RWKV；不能自动改参数名/值，也不能重开工具目录或选择候选。 |
| Round4 强制 FP=0 且后续永久继承 | 改为目标，不改官方门禁 | FP=0 是方向，不应成为唯一硬条件，否则会鼓励“全部阻塞”。恢复后的正式门禁仍是 FP 不高于上一轮，同时约束 External、Strict 和 FN。 |

## 数据校正与新增 Round3 证据

Round2 权威结果：External 8/90、Strict 7/90、Agent completed 19、FP 12、FN 1。终止入口为
43 个 `plan_missing_direct_criterion_claims`、9 个 Goal criterion 超上限、4 个剩余 G1i 完整外壳
拒绝，以及 12 个错误完成。

Round3 权威结果：External 4/90、Strict 2/90、Agent completed 11、FP 9、FN 2；90/90 因果链和
11/11 最终回答字节非干预完整。failed-equivalent-observation gate 的运行计数为：

- observation prepared：42；cacheable：42；
- 首次协议有效的 RWKV `replan` 失败记录：8；
- 同 lineage 相同 digest 的实际抑制：0。

因此 Round3 的总请求从 809 降至 583 不能归因于 gate；它由不同的 RWKV 输出/终止路径造成。
本轮也不满足 External/Strict 晋级条件，不上传为新的最佳回档。

## Round4 可以借鉴的最小完成证据边界

Round4 应只做一个完整但最小的 `criterion_evidence_boundary.v1`，不同时放宽初始计划覆盖、不扩展
criterion 数量、不改 G1i：

1. `EvidenceRef` 必须绑定来源类型、workspace-relative path/artifact id、SHA-256，以及可选 JSON
   Pointer 或文本范围。Goal literal 必须是原始请求/immutable Goal 的精确 span，不能由模型自由写
   一个新 literal 再自证。
2. `CriterionClaim` 由 RWKV 提出，至少包含 `criterion_id`、`subject_task_id`、producer、actual ref、
   expected ref/expression 与 verifier kind。程序只验证引用存在、作用域、类型和确定性计算，不替
   RWKV选择这些字段。
3. actual 允许指向当前 producer 输出；expected 禁止指向同一次 producer 的输出。expected 只能来自
   immutable Goal span、执行前冻结的依赖 ref 或其受限确定性变换。
4. 第一版 proof 算子只加入 Round2 FP 直接需要且能安全解释的最小集合；每个算子必须纯函数、资源
   有界、无 Python/eval/文件路径搜索。新增算子只能由后续全量数据支持。
5. `action_succeeded`、`file_exists` 与 model cross-check 不能单独或相互组合提交 VERIFIED Goal
   evidence。任一 required deterministic proof 失败时，RWKV 的 `pass` 不能覆盖它。
6. Controller 不用自然语言关键词规则识别 “all/every”。若需要集合完整性，必须由 RWKV claim
   显式选择集合 ref 和集合 proof；Controller 只执行并记录。
7. Task postcondition 通过只完成 Task；Goal evidence 另行提交。read/list 验证 producer 时，owner/
   subject 指向 producer，不归读取任务自身。
8. run 完成前，按当前 workspace snapshot 重新执行所有已登记 proof；ref hash 或 observation digest
   变化则证据失效并真实阻塞/交给后续 RWKV recovery，不能沿用旧 pass。

这属于“RWKV选择证明，确定性工具执行证明”，不属于规则代答；反过来，若程序从 criterion 文本、
题号、标准答案或 acceptance 自动生成 proof/expected，就是作弊。

## 对外部项目引用的校正

[OpenCodeInterpreter 官方项目](https://opencodeinterpreter.github.io/)和
[论文](https://arxiv.org/abs/2402.14658)支持的是“把真实执行/编译反馈回传给同一模型以迭代修正”，
可以佐证 observation feedback 的方向，但它没有直接给出 RWKV-LH 所需的 typed criterion proof
或完成证据所有权设计。

[OpenBMB ToolBench 官方仓库](https://github.com/OpenBMB/ToolBench)及
[ICLR 2024 论文](https://proceedings.iclr.cc/paper_files/paper/2024/file/28e50ee5b72e90b50e7196fde8ea260e-Paper-Conference.pdf)
研究工具学习、调用链和评测。它可以支持受约束工具接口与真实执行反馈，不能被当作 `ProofExpr`
正确性的直接证据。证据 DSL 是否适合 G1i-13.3B 仍必须由固定 90 题单变量消融证明。

## 建议的剩余轮次拆分

为保持十轮目标和因果可解释性，建议按实际结果动态预注册，而不是提前把所有轮次锁死：

1. Round3：failed-equivalent-observation suppression（已完成，0 次实际触发）。
2. Round4：最小 criterion evidence boundary；不放宽 plan coverage。
3. Round5：删除 legacy criterion 回退，允许初始 plan 保留未解决 obligations，并由 RWKV做有预算的
   Goal-obligation replan。
4. Round6：Goal criterion 1–16 协议与无损、不截断验证。
5. Round7：剩余无歧义 G1i envelope 归一；缺失 name 继续拒绝。
6. Round8：同一已选工具的一次 schema-error feedback，由 RWKV修正参数。
7. Round9：只有前几轮数据证明上下文/检索是主要瓶颈时，消融 deterministic StateCapsule 或
   artifact index，二者只选一个。
8. Round10：由 Round9 结束后的全量因果数据选择一个通用变量；不得预先按隐藏失败题写特判。

每一轮仍执行 125+ 离线回归（以当时实际总数为准）、LH-Control-30、完整 E2E-90 和运行后全回归；
相似度算法、标准答案和隐藏验收口径不变。

## 门禁修订建议

- 实验完成门禁：90/90 终态、因果链 90/90、最终回答非干预全部通过、Control-30 与离线全过。
- Round3 起恢复的安全门禁：FP 不高于上一轮；同时报告 FN 和 completion precision，防止靠阻塞降 FP。
- GitHub 新最佳回档：External 必须高于当前最佳 8，FP 不增加，Strict 不回退，其他完整性门禁全过。
- Round4 的方向性目标可以写 `FP=0`，但正式判定应至少要求 FP 明显下降且 External/Strict/FN 不退化；
  不能在看到结果后修改阈值。
