# Round4 结构改动记录

## 单变量

Round4 实施预注册的 `independent_criterion_proof_boundary.v1`：Task 后置条件和 Goal criterion evidence
分离。RWKV validation v2 自己给出 claim、subject/producer、actual/expected expression 和 comparison；
程序只执行固定的纯数据表达式并做 exact typed equality。

## 实现

- Run schema v3 增加 append-only `CriterionClaim`、`EvidenceRef` 和 proof provenance；未完成 v2 run 的旧
  VERIFIED evidence 迁移为 `LEGACY_UNVERIFIED`，已完成历史 run 保持只读可加载。
- 新增有界 proof engine：深度 8、节点 64、claim 20,000 chars、value/source 2,000,000 bytes；只允许
  `ref/literal/count/sum/group_sum/object/object_set/sort/sha256`。
- expected 禁止引用当前 workspace/current action result；dependency 必须是直接 dependency 且 artifact
  hash 未变化；actual/expected 同源拒绝；未知字段、selector、op 和 comparison fail closed。
- Task 的 required deterministic postcondition 决定 Task completion；proof 失败不伪造成 RWKV replan，
  但不会创建 Goal evidence。
- run 完成前重放 active verified claim；workspace/hash/provenance 变化会使 claim/evidence invalidated。
- E2E runner 在首个请求前记录 tracked+untracked source tree manifest，避免未提交 `proof.py` 未被普通
  `git diff` 覆盖。

## 非干预

- 没有读取 hidden acceptance 或 Codex 标准答案来生成 proof；只在 90 题结束后用于评分和相似度。
- 没有从 criterion 文本、题号或 action 参数生成/补全/排序 claim。
- 重复 claim 整组拒绝，不选择其中能通过的一条。
- RWKV replan 不会被 matching proof 覆盖；final answer 路径仍保持 raw RWKV 字节不改写。

## 实验判定

Round4 不满足上传门槛：External `7` 未超过当前最佳 `8`，Strict 从当前最佳 `7` 降为 `0`，Agent
completed 为 `0`。因此保留全部本地因果数据，不提交为 GitHub 最佳回档。
