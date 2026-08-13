# Round7 预注册：RWKV Goal Obligation Expansion

预注册日期：2026-08-12（任何 Round7 RWKV-E2E-90 请求之前）

## 1. 固定依据

Round6 External `6/90`、Strict `0/90`、Agent completed `0/90`。49/90 在初始 plan 阶段因完整计划没有
一次声明所有 required `satisfies_criteria` 而阻断，是最大的单一终止阶段；这些题没有进入 action、validation
或 proof。Round4/5/6 同类题分别为 45/41/49，说明它不是单轮采样偶然。

现有 plan 在结构合法但 criterion coverage 不全时，把整个 plan 视为 contract error，并要求 RWKV 重写完整
计划。它丢弃了已经合法的任务图，也没有把“尚未分配的 criterion”建模为显式状态。这与 Prime Agent 的
状态/协议工程启示相反：可确定的剩余状态应被明确投影给模型，而不是重做已完成结构。

固定摘要：

- Round6 results SHA-256：`3c0ece575ee2980551353d7b9b69561391219bdb91fab201bcce421201e2f73b`
- Round6 operator analysis SHA-256：`6aece4a0fa3a502cc5886cd36b9eb429a08659aa1cbb5877dca609bd34f3de88`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`

## 2. 唯一结构变量

实施 `rwkv_goal_obligation_expansion.v1`：初始 plan 只要 schema、TaskGraph、task contract 和 criterion id
作用域合法就保留；Controller/Model adapter 确定性计算 required criterion ids 与 RWKV
`satisfies_criteria` 声明的集合差，形成只读 obligation ledger。若 ledger 非空，由同一 RWKV 追加规划缺失
obligation 的 supplemental tasks，而不是规则补 criterion 或要求重写完整计划。

### 2.1 初始 plan

- 保留 `long-horizon.plan.v2` 与原任务字段；结构/parser 错误仍最多一次完整 plan correction。
- 不再因为 coverage 不全而丢弃结构合法 plan。
- 未知 criterion id、环、未知 dependency、空 task 等仍 fail-closed。

### 2.2 obligation expansion

结构合法 plan 后，运行时只计算：

`missing_required = required Goal criterion ids - union(RWKV task.satisfies_criteria)`。

若非空，发出一个 `long-horizon.plan-obligations.v1` 请求，输入：Immutable Goal digest、缺失 criterion 的 id 与
原始 description、当前 RWKV plan、当前本地 task ids、workspace manifest 和 action catalog。RWKV 返回
`supplemental_tasks`，使用与 plan v2 完全相同的结构字段；dependency 可引用当前或同响应 local id。

所有 `satisfies_criteria` 仍由 RWKV 明确给出。程序只把 supplemental tasks 按原样追加并重新校验 combined
TaskGraph、criterion scope 与 coverage；不得把缺失 id 自动写入某个 task，不得修改现有 task，不得基于 action
或文件推断 owner。obligation 响应最多一次格式/coverage correction；仍不完整则 fail-closed。

raw initial plan、missing ledger、raw supplemental response、combined local graph、local→global id 映射和每次校验
结果完整持久化。ledger 是 Goal 与 RWKV 声明的机械集合差，不使用 hidden acceptance、Codex answer 或自然
语言规则。

### 2.3 完成边界不变

新增 task 只有在 RWKV 后续选择 action、deterministic postcondition 通过、RWKV semantic pass 且 independent
criterion proof VERIFIED 后才能形成 Goal evidence。obligation assignment 本身绝不视为完成证据。

## 3. 明确不改

- 不改 Goal parse、action/G1i、validation v4、assertion binding、proof、replan、final、工具集、并发 8、200
  transitions、recovery budget、数据集、hidden acceptance、相似度或现有采样值。
- 新 request type `goal_obligation_planning` 使用与 task decomposition 相同的固定 temperature `0.18`，不是新增
  探索调参。
- 不自动分配 criterion，不把 advances_criteria 升格为 satisfies_criteria，不选“最像”的 task，不修改 RWKV
  final answer，不读取实验答案生成 task。
- 不在线自改策略，不因单题结果放宽 coverage、proof 或 FP 门槛。

## 4. 必测

1. 完整 initial plan 不调用 obligation lane；缺失 coverage 时精确 ledger 与 description 可追溯。
2. supplemental dependency 可引用 base/new local id，combined graph 无环且 local→global 重写稳定。
3. 未知/重复 id、修改现有 id、仍缺 coverage、额外未知 criterion、空 supplemental tasks 全部拒绝。
4. 规则不修改任何 task 的 satisfies_criteria；raw supplemental 与 materialized task 字段一致。
5. obligation assignment 不创建 CriterionEvidence，不绕过 action/validation/proof。
6. 完整离线、LH-Control-30、历史 schema/恢复/异常/并发和 E2E-90。

## 5. 指标与上传门槛

报告 initial plan structural-valid 数、obligation lane 题数/请求数、expansion success、combined coverage、进入 action
的新增题数，以及 External、Strict、completed、FP/FN、proof、tokens 和非干预。

上传门槛恢复并保持：Agent completed > 0、FP≤9、External≥8、Strict≥7，且 External 或 Strict 至少一项严格
超过 Round2；离线、Control、因果链和 raw final byte equality 全过。否则不上传。
