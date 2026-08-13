# Round17 预注册：Flat Explicit Expected Mode

预注册日期：2026-08-13（任何 Round17 RWKV 请求之前）

## 固定依据

Round16 在 90 题全部终止后得到 External `24/90`、Strict `0/90`、Completed `0/90`、FP `0`；
产品测试 `220/220`、LH-Control `30/30`。虽然 External 比 Round15 高 5，但 evidence 生命周期明显退化：

- 40 题到达 post-action witness selection，仅 4 题编译、1 题 proof pass 并保存 CriterionEvidence；
- Round15 对应为 42 题到达、20 题编译、5 题 proof pass/保存 evidence；
- 726 次 selection 请求中只有 9 次协议成功，704 次 contract error、13 次 protocol error；
- 460 次错误是 `expected witness kind must be catalog_source or goal_literal`；
- 1075 个可解析 expected 条目中，814 个把 `action_output/workspace/action_result/...` 等
  `source_kind` 当成 union 判别值，另有 27 个使用 `workspace_json/...` 等 read operator；
- 合法 catalog union 只有 10 个条目，合法 Goal union 172 个条目；
- obligation 重复任务实例从 Round15 的 263 增至 329，最终 replan exhausted 从 27 题增至 38 题。

这些计数在加载 hidden acceptance/reference 之前由 score-independent 分析器冻结。Round16 results
SHA-256 为 `ac49ff3baf17938ae6aa747e61fc193c6bbff835265b1d990b73a5bde5d92c73`；
expected-union analysis SHA-256 为
`2044f60a659af1bea00c810796e6e180f718ec28749d9239dec6b4c6584155b5`。

## 唯一结构变量

实施 `flat_explicit_expected_mode.v5`，只改变 post-action witness selection 中 expected 分支的表达：

1. `schema_version` 更新为 `long-horizon.witness-selection.v4`。
2. 删除嵌套 `expected` object 和名为 `kind` 的 union 判别字段。
3. 每个 selection 的公共必需字段为
   `criterion_id/actual_source_handle_id/expected_mode`，可选 `note`。
4. `expected_mode="catalog_source"` 时，还必须且只能提交 `expected_source_handle_id`。
5. `expected_mode="goal_literal"` 时，还必须且只能提交
   `expected_goal_quote/expected_goal_value`。
6. Runtime 在完整验证后仅机械投影到已有内部 WitnessIntent：catalog ID 原样进入
   `expected_source_handle_id`；Goal quote/value 原样进入 `expected_goal_literal`。Runtime 不选择 mode，
   不生成、修复、别名映射、丢弃或覆盖任何语义字段。

该变量直接检验 Round16 的主因：`kind` 同时出现在 union 与 source catalog 语义中，弱模型把两个层次
绑定。`expected_mode` 明确声明它只表示期望证据来源分支，不表示 source kind、read op 或 transform。

## 不作弊边界

- `expected_mode` 必须由 RWKV 输出；Runtime 不根据 source 是否存在、Goal quote 是否匹配、artifact
  是否正确、verifier 或 reference 结果替 RWKV选择分支。
- catalog/Goal 两种字段混合、缺失、额外字段、非法 mode、旧 v2/v3 shape 全部拒绝；不丢字段后接受。
- source ID eligibility、Goal 精确 quote、typed value、criterion coverage、WH binding、proof 与 completion
  语义不变。
- raw response、parsed payload、mechanical projection、proof 和状态继续完整审计；不改 RWKV final。
- hidden acceptance/reference 只在 90 题全部终止后加载。

## 明确不改

- Round15 的 Goal-obligation minimal envelope、预算、重规划和重复任务行为不改。
- Goal、plan、priority、action/G1i、recovery、sampling、并发、max transitions、数据、verifier、相似度
  算法、witness catalog 内容和 proof engine 不改。
- 不修复 `priority="high"`、不合并重复任务，不引入第二结构变量。

## 固定运行与验证

- RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`，endpoint `127.0.0.1:29610/v1`。
- 并发 8、max transitions 200，sampling 与 Round16 相同。
- 运行前后完整产品测试、LH-Control-30、E2E catalog validation；冻结源码、协议、数据和 runtime
  fingerprint。
- 保存 90/90 prompt/raw/parsed/event/state/workspace；先做 score-independent backward causality 与
  mode-shape 分析，再加载标准答案/hidden acceptance。

## 预注册诊断门

- v4 合法 catalog/Goal 两分支均可编译；混合字段、非法 mode、额外字段、旧 shape 均 fail closed。
- Round16 的 `expected witness kind must be catalog_source or goal_literal` 应归零，且不得靠 Runtime 映射
  source kind 达成。
- 至少 21/40 reached case 编译 selection；proof-pass/evidence 必须高于 Round16 的 1，目标恢复并超过
  Round15 的 5；不得引入非独立来源 proof。
- FP=0、Offline 全过、Control 30/30、因果链 90/90、需要 final 的 case raw byte equality 全过。

## GitHub 晋级门

只有同时满足 FP=0、Strict >7、Completed >7、External 不低于历史最佳 24、全量回归和审计通过，
才允许提交并推送。否则保存本地 Round17 并标记 `do_not_upload`；远端保持 Round2 checkpoint
`b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
