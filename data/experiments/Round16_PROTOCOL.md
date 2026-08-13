# Round16 预注册：Discriminated Expected-Witness Union

预注册日期：2026-08-13（任何 Round16 RWKV 请求之前）

## 固定依据

Round14 与 Round15 的 score-independent 分析共同显示，post-action witness selection 已经成为重复
obligation 任务无法转化为证据的主要瓶颈：

- Round14：507 次 selection 请求，19/38 题编译，5 题 proof pass 并保存 evidence；
- Round15：729 次 selection 请求，20/42 题编译，5 题 proof pass 并保存 evidence；
- Round15 在 47 题保存 115 次 obligation replan、追加 440 个任务，其中 263 个任务实例在同一题内
  具有重复的 title/description/criterion 语义；首次保存 replan 后又发生 1641 次请求、427 次 action，
  但只有 5 次 proof pass；
- Round15 selection 错误中，211 次是“选择 catalog expected source 的同时又提交非空 Goal literal”，
  279 次是 expected source ID 不存在或不具 expected 资格，126 次 Goal quote 不是原 Goal 精确子串。

当前 selection item 强制同时携带 `expected_source_handle_id` 与 `expected_goal_literal`，并用空字符串/
空对象表达二选一。这个表示让弱模型很容易同时填两个分支。运行时若丢弃其中一个字段，就会替 RWKV
选择证据来源，违反不干预原则；因此 Round14/15 正确地 fail closed，但产生了大量重复重试。

权威非计分记录：

- Round15 results SHA-256：
  `24e724116aef9862092329a4603dc3b82fff01c34484481d41cabd67effad610`
- Round14→15 backward comparison SHA-256：
  `6d92ec2edf30593709f33d635f14399b5b0051b46d9bac4bdfb9c81bf14f6a42`
- Round15 witness selection analysis SHA-256：
  `fd192e708be68c12e41e0110564d56b18f9a6a4bbccc198893f9f7567c0b54e3`
- Round15 obligation amplification analysis SHA-256：
  `be7ac53d670d0ae37446c5f95f982e511690e1c9917ba2cae63056ab30898ec2`

这些分析不读取 hidden acceptance 或 Codex reference。Round15 后置成绩为 External `19/90`、
Strict `0/90`、Completed `0/90`、FP `0`；未通过 Git 晋级门，未上传。

## 唯一结构变量

实施 `discriminated_expected_witness_union.v4`：

1. witness selection 顶层仍为必需 `schema_version/decision/witness_selections`、可选 `reason`。
2. `schema_version` 更新为 `long-horizon.witness-selection.v3`。
3. 每个 pass selection 的字段改为必需
   `criterion_id/actual_source_handle_id/expected`、可选 `note`。
4. `expected` 必须由 RWKV 原样选择且精确匹配一个分支：
   - catalog 分支：`{"kind":"catalog_source","source_handle_id":"WS-..."}`；
   - Goal 分支：`{"kind":"goal_literal","goal_quote":"原 Goal 精确子串","value":<typed JSON>}`。
5. 两个分支不允许额外字段，不允许同时提交 source 与 literal，也不允许缺少分支判别符。
6. 只有在分支和字段完整通过后，Controller 才进行机械的内部投影：catalog 分支投影到已有
   `expected_source_handle_id`，Goal 分支投影到已有 `expected_goal_literal`。该投影不选择分支、不生成
   ID/quote/value，也不修改任何 RWKV 语义字段。

这是单一表达协议变量：用判别联合代替两个互斥字段加空值哨兵。actual source、criterion coverage、
source eligibility、Goal quote、typed value、WH binding、proof 和 completion 语义不变。

## 不作弊边界

- Runtime 不依据 source 是否存在、literal 是否匹配、artifact 是否正确或 external/reference 结果来替
  RWKV 选择 union 分支。
- 旧的同时含 source/literal shape 不自动迁移、不丢字段、不择一接受；Round16 只接受 v3 判别联合。
- 未知 source ID、非 expected-eligible source、非精确 Goal quote、未知/额外字段继续 fail closed。
- 不根据重复任务、相同 observation 或历史 evidence 删除/合并任务；本轮不改变 obligation 控制流。
- raw/parsed union、内部机械投影、最终 WS/WH、proof 与状态完整审计；final answer 不被改写。
- hidden acceptance/reference 仍只在 90 题全部终止后加载。

## 明确不改

- Round15 的 Goal-obligation minimal envelope、任务预算、重规划、重复任务处理不改。
- Goal、初始 plan、priority、action/G1i、failure recovery、sampling、并发、max transitions、数据、
  verifier、相似度算法不改。
- 不修复 `priority="high"` 的已知未捕获异常，避免在同轮引入第二变量。

## 固定运行与验证

- RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`，endpoint `127.0.0.1:29610/v1`。
- 并发 8，max transitions 200，sampling 与 Round15 一致。
- 运行前后完整产品测试、LH-Control-30；冻结源码、协议、数据和 runtime fingerprint。
- 保存 90/90 prompt/raw/parsed/event/state/workspace；先做 score-independent backward causality，再加载
  standard answer/acceptance。

## 预注册诊断门

- v3 合法 catalog/Goal 两分支均可编译；混合字段、未知 kind、额外字段、旧 v2 shape 均 fail closed。
- `catalog expected source requires empty expected_goal_literal` 这一旧空值哨兵错误应归零；不得通过丢弃
  literal 达成。
- 至少 21/42 以上 reached case 成功 compiled selection；proof-pass/evidence case 必须高于 Round15 的
  5 题，且不能引入任何不独立来源 proof。
- FP=0、Offline 全过、Control 30/30、因果链 90/90、需要 final 的 case raw byte equality 全过。

## GitHub 晋级门

只有同时满足 FP=0、Strict >7、Completed >7、External 不低于历史最佳 22、全量回归和审计通过，
才允许提交并推送。否则保存本地 Round16 结果并记为 `do_not_upload`；远端保持 Round2 checkpoint
`b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
