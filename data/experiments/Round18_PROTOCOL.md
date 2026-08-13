# Round18 预注册：RWKV-Committed Progressive Witness Disclosure

预注册日期：2026-08-13（任何 Round18 RWKV 请求之前）

## 固定依据

Round16 的嵌套判别联合将 selection 编译降到 `4/40`，proof/evidence 为 `1/90`；814 个条目把
source kind 当作 union `kind`。Round17 将分支平铺为 `expected_mode` 后仍为 `4/39` 编译、`1/90`
proof/evidence；657 次请求中 642 次 contract error。最主要的新错误是：

- 823 个 selection 同时携带 catalog ID 与 Goal quote/value；
- 622 个条目的 mode 本身合法，但附带了另一分支字段；
- 242 个条目仍把 source kind 当作 mode，71 个使用其他 mode；
- 只有 35 个 catalog shape、29 个 Goal shape 完整合法。

因此根因不只是字段名，而是同一 prompt 同时披露两个分支时，RWKV 倾向复制所有候选字段。Runtime
正确地 fail closed；若自动删掉另一分支字段，就会替模型做选择，违反不干预边界。

Round17 results SHA-256：
`be14cf2cf636707d8001198e8dd095d506cd8a01b2fa019812b7bebb5cffb52b`；score-independent
expected-mode analysis SHA-256：
`91c661e23fa98bafe7b08549405574540a1d56fe580adb3a658b44f396016fa9`。

## 唯一结构变量

实施 `rwkv_committed_progressive_witness_disclosure.v6`，把一个同时披露两分支的请求拆成两个职责单一、
连续审计的 RWKV 决策：

1. mode commitment：RWKV 只提交严格对象
   `{"schema_version":"long-horizon.witness-mode.v1","decision":"catalog_source|goal_literal|replan"}`。
2. 若 RWKV 提交 `replan`，立即返回 replan，不发 binding 请求。
3. 若 RWKV 提交 `catalog_source`，binding prompt 只披露 catalog schema：每项仅允许
   `criterion_id/actual_source_handle_id/expected_source_handle_id` 和可选 note。
4. 若 RWKV 提交 `goal_literal`，binding prompt 只披露 Goal schema：每项仅允许
   `criterion_id/actual_source_handle_id/expected_goal_quote/expected_goal_value` 和可选 note。
5. Runtime 仅按照 RWKV 已提交且已审计的 mode 选择后续 prompt/schema；不根据 source、artifact、
   verifier、历史分数或 reference 选择分支，也不生成、补全、映射、删除或改写 binding 字段。

这是一个协议渐进披露变量。两次调用不是对同一答案投票、重写或 verifier cross-check：第一调用只负责
分支承诺，第二调用只负责该分支的证据绑定，职责和输出字段不重叠。

## 不作弊边界

- mode 必须来自 RWKV raw/parsed payload；非法/额外字段、旧 shape 全部 fail closed。
- binding 只能使用 committed mode 的 schema；若 RWKV在 binding 中输出另一分支字段，严格拒绝，不丢弃。
- source eligibility、Goal 精确 quote、criterion coverage、WH binding、proof、obligation 与 completion 不变。
- 不以 external/reference、预览值相等或 Runtime 规则决定 mode、source ID、quote 或 value。
- raw response、parsed payload、mode→prompt 选择、binding、mechanical projection、proof 与状态完整审计；
  不改 RWKV final。
- hidden acceptance/reference 只在 90 题全部终止后加载。

## 明确不改

- Goal-obligation minimal envelope、预算、重复任务和重规划不改。
- Goal、plan、priority、action/G1i、recovery、sampling、并发、max transitions、数据、verifier、相似度、
  catalog 内容、proof engine 不改。
- 不修复已知 `priority="high"` 或其他错误，避免第二变量。

## 固定验证

- RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`，endpoint `127.0.0.1:29610/v1`。
- 并发 8、max transitions 200，sampling 与 Round17 相同。
- 运行前后 pytest、LH-Control-30、E2E catalog validation；冻结源码、协议和 runtime fingerprint。
- 保存所有 mode/binding prompt、raw、parsed、event、state、workspace；先做 score-independent 分层分析，
  再加载标准答案与 hidden acceptance。

## 预注册门

- mode 合法三分支、非法 mode、额外字段和旧 shape；两种 branch binding 的合法/混合/额外字段均有测试。
- binding prompt 不得出现未 committed 分支的字段名。
- selection 编译至少 `21/39`；proof/evidence 高于 Round17 的 1，目标超过 Round15 的 5；无非独立 proof。
- FP=0、pytest 全过、Control 30/30、因果链 90/90、需要 final 的 case raw byte equality 全过。

## GitHub 晋级门

只有同时满足 FP=0、Strict >7、Completed >7、External 不低于历史最佳 24、全量回归和审计通过，才可
提交并推送。否则保存本地 Round18 并标记 `do_not_upload`；远端保持 Round2 checkpoint
`b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
