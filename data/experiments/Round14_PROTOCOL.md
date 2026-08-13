# Round14 预注册：Semantic-Minimal Witness Selection Contract

预注册日期：2026-08-13（任何 Round14 RWKV 请求之前）

## 固定依据

Round13 的 score-independent lifecycle/trace 分析显示：

- 34/90 题到达 post-action witness selection，合计 355 次真实请求；
- 352/355 个 parsed payload 的语义 decision 是 `pass`；
- 348/355 请求被 contract 拒绝，仅 6 次 `ok`、1 次 protocol error；
- 209 次顶层 exact-key 拒绝中，203 次唯一缺失字段是 `reason`；这 203 个 payload 均已有
  `schema_version/decision/witness_selections`，具体 selection 通常又有 `note`；
- 其余 `goal_quote` 非原请求子串 98 次、Goal literal 结构错误 22 次、coverage 7 次、expected
  source/literal 冲突 9 次、未知 expected WS ID 3 次，属于证据语义/绑定错误，不可归入格式字段省略。

该分析脚本不读取 hidden acceptance 或 Codex reference。权威记录：

- Round13 results SHA-256：
  `7ddce9e175ea2e192f546c2856c7a8f7aa419099b2f200d9f1e23e30a33a37e7`
- Round13 backward analysis SHA-256：
  `6410f486372d990cefb18a1447a40982a6dd326c62d43a7d78edc169177a5b5b`
- Round13 witness selection analysis SHA-256：
  `be31140f0b1cf67b580aa74ffb62ed35233b2d40f70c9d824507a845b3adcd48`

Round13 post-run score 为 External `20/90`、Strict `0/90`、Completed `0/90`、FP `0`、FN `20`；
它证明动作可达性改善，但并未通过结构诊断或 Git 晋级门。

## 唯一结构变量

实施 `semantic_minimal_witness_selection.v3`，只把非语义解释字段从 hard gate 中移除：

1. witness selection 顶层必需字段固定为 `schema_version/decision/witness_selections`；`reason` 允许
   RWKV 自愿提供，但不得由 Controller 生成、补写、改述或替换。除此之外的额外字段继续拒绝。
2. 每个 selection 的语义必需字段仍为 `criterion_id/actual_source_handle_id/
   expected_source_handle_id/expected_goal_literal`；`note` 允许自愿提供但不参与 proof、选择、排序或
   completion。除此之外的额外字段继续拒绝。
3. prompt 不再要求模型重复输出 `reason/note`；若模型仍输出则原样审计。内部缺失值只记录为空，明确
   标记 `rwkv_reason_provided=false`，不能把空值描述成模型理由。
4. `decision` 枚举、每 criterion 精确覆盖、WS ID 存在/side eligibility、Goal quote 精确子串、typed
   value、source conflict、final WH selection、独立来源 proof 与 provenance 全部保持 Round13 原样。

这是单一协议变量：将“解释性文本”从控制流必需字段降为审计可选字段。它不增加 alias/coercion，
不展开未知 envelope，不重试其他选择，不推断 source/expected/criterion，也不改变 RWKV decision。

## 不作弊边界

- 缺失 `reason/note` 只代表“RWKV 未提供解释”，Controller 不生成任何替代文本。
- 绝不因为 artifact 相等、external 正确、reference 相似或历史通过而接受一个 WS/WH 选择。
- Goal quote、typed value、actual/expected WS 与 WH 均必须由 RWKV 原样提交并通过原有验证。
- raw、parsed、字段 presence、compiled selection 与 proof 完整审计；final 仍 byte-exact raw RWKV。
- hidden acceptance 与 Codex reference 仅在 90 题全部终止后使用。

## 明确不改

- Round13 的 post-action catalog lifecycle 和 source ID 方案不改。
- Goal 1--5 容量、plan、obligation replan、priority 类型、action/G1i、recovery、sampling、并发、
  max transitions、数据、验收和相似度算法不改。
- 不放宽 Goal quote、source ID、coverage、proof 或 completion；不增加 verifier/预算/模型调用类型。

## 固定运行与验证

- RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`，endpoint `127.0.0.1:29610/v1`。
- 并发 8，max transitions 200，sampling 与 Round13 一致。
- 运行前后完整产品测试、LH-Control-30；冻结源码、协议、数据和 runtime fingerprint。
- 保存 90/90 prompt/raw/parsed/normalized/event/state/workspace；先进行 score-independent backward
  causality，再加载 standard answer/acceptance。

## 预注册诊断门

- Round13 的 203 次“仅缺 reason”以及 selection item“仅缺 note”不得再触发 contract error；字段
  presence 必须可审计，缺失理由不得被伪装为 RWKV 输出。
- Goal quote/WS/coverage 错误继续 fail closed；若这些计数上升，应归因于更深 reach，不能声称被修复。
- 至少 2/34 以上 reached case 成功 compiled selection，且至少一条 proof passed、一条 VERIFIED
  CriterionEvidence 和一题真实 Completed；否则结构诊断失败。
- FP=0、Offline 全过、Control 30/30、因果链 90/90、需要 final 的 case raw byte equality 全过。

## GitHub 晋级门

只有同时满足 FP=0、Strict >7、Completed >7、External 不低于 20、全量回归和审计通过，才允许提交
并推送。否则保存本地 Round14 结果并记为 `do_not_upload`；远端保持 Round2 checkpoint
`b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
