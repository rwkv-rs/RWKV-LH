# Round4 独立 Criterion Proof 专项分析

本分析只在 90 题全部结束后执行。隐藏 acceptance 和 Codex 标准答案没有进入 RWKV 请求、claim
生成或 proof 求值。

## 结论

`independent_criterion_proof_boundary.v1` 在防止错误完成上 fail-closed，但当前协议不适合这版弱
RWKV：`84` 次 criterion evaluation 中没有一次 proof 通过，Agent completed 为 `0/90`。因此
FP `0` 是“没有任何完成”的空洞结果，不能视为精度提升，也不满足上传条件。

固定 E2E 指标为：External `7/90`、Strict `0/90`、Agent completed `0/90`、FP `0`、FN `7`。
Basic/Medium/Hard 的 External 分别为 `6/30`、`0/30`、`1/30`。完整因果链 `90/90`。

## Proof 阶段

- 26 题进入 `validation_cross_check`，共启动并返回 132 个请求；131 次 JSON parsed、1 次 JSON protocol
  error。按原始事件重新核对后，另有 93 次 `invalid validation schema` contract error；84 个
  criterion-cross-check attempt 中仅 38 个 contract 有效、46 个在两次响应均无效后 fail-closed。早期报告把
  “JSON 可解析”误写成“contract 有效”，现已纠正，External/Strict 等主指标不受影响。
- 26 题产生 84 个 `criterion_claims_evaluated` 事件：RWKV pass 34，replan 50。
- exact claim coverage 36 次成立、48 次不成立；proof pass `0/84`。
- 实际持久化 55 条 claim，全部 REJECTED；没有 VERIFIED claim，也没有 CriterionEvidence。
- 55 条 claim 少于 84 个事件，是因为许多 replan 或 pass 响应给出了空 claims；控制器没有自动补齐。

主要拒绝原因：

| 原因 | 条数 |
| --- | ---: |
| comparison 不是 `exact_equals` | 16 |
| subject 超出当前 task/direct dependency scope | 7 |
| 自创 `read_json` proof op | 7 |
| RWKV 选择 replan，proof 未执行 | 6 |
| expected 指向 mutable workspace | 5 |
| literal 的 quote 不是 Goal 原文逐字片段 | 3 |
| 其他自创 op/source/字段或 producer 越权 | 11 |

模型还提出 `exists`、`contains`、`valid_json`、`sorted` 等 comparison，以及 `read`、`read_file`、
`json_field_equals`、`directory_files` 等未注册 op。这说明问题不只是 schema JSON 是否闭合，而是 combined
semantic decision + DSL authoring 对当前 RWKV 的协议负担过高。

## 外部正确但内部未完成

7 个 FN 是 `E2E-B04/B06/B13/B19/B22/B26/H09`，全部以 Goal evidence 缺失结束：

- B04、B06、B13、B26 至少出现 RWKV pass claim，但均被上述 proof 合同拒绝；
- B19、B22、H09 的 criterion evaluation 全是 RWKV replan，没有 proof pass；
- 7 题 CriterionEvidence 均为 0，控制器没有把外部验收结果反馈给模型或据此补答案。

## 与历史轮次

| Round | External | Strict | Completed | FP | FN | Requests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Round2（当前最佳） | 8 | 7 | 19 | 12 | 1 | 809 |
| Round3 | 4 | 2 | 11 | 9 | 2 | 583 |
| Round4 | 7 | 0 | 0 | 0* | 7 | 802 |

`*` Round4 FP=0 为全阻断结果。Round4 比 Round3 多 219 个请求，却失去全部 completion。原始 attempt
复核显示本轮实际 84 个 cross-check 全是 optional `criterion_cross_check`，没有显式
`model_cross_check + criterion_cross_check` 重复调用可供归因；132 个 validation 请求主要来自 contract
纠正重试。单调用复用仍是合理的结构防线，但 Round4 数据不能证明它能降低请求数。

## 可借鉴与不可借鉴

可以保留 Prime Agent 式的边界思想：统一内部协议、raw/parsed/evaluated 全链路、失败 fail-closed、最终
重放验证。不能保留当前“一次让弱 RWKV 自由生成完整递归 DSL”的产品形态，也不能通过规则从 Goal
自然语言反推出 op/expected 来提高通过率；后者会由程序替 RWKV 做语义选择，违反不作弊约束。

机器可读明细见 `criterion_proof_analysis.json`。
