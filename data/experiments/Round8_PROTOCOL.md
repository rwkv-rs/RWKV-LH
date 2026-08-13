# Round8 预注册：Copy-Resistant Assertion Binding Contract

预注册日期：2026-08-12（任何 Round8 RWKV-E2E-90 请求之前）

## 1. 固定依据

Round7 External `12/90`、Strict `0/90`、Agent completed `0/90`。criterion assertion Phase B 共收到
79 个 RWKV binding response，只有 8 个严格通过现有 schema；71 个 contract error 中 53 个是 binding 对象把
输入侧的 `actual_read_op`、`expected_read_op`、`actual_required_argument_keys`、
`expected_required_argument_keys` 等 metadata 原样复制为输出字段。只有 8 条 assertion 进入 exact proof，2 条
VERIFIED，仍不足以覆盖任一 Goal。

当前 Phase B 把 SELECTED OPERATOR CONTRACTS 渲染为 JSON 对象；其字段名与目标 binding schema 不同，但两者
紧邻出现。弱 RWKV 复制最近 JSON 结构是可复核的协议污染，不是 evidence 语义错误。Prime Agent 可借鉴的
部分是模型边界协议工程：输入状态与输出协议必须明确分层；不能在响应后删除字段或把错误输出修成正确答案。

固定摘要：

- Round7 results SHA-256：`a2292aa6f873c26b862742e3f91c32ab30eb611333fbf5871800cc5c9b022076`
- Round7 obligation analysis SHA-256：`3b54a1ef1c0226c4fdd2d31bcabd96647eaa7e7417d3db61f0744995d78d1550`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`

## 2. 唯一结构变量

实施 `copy_resistant_assertion_binding_contract.v1`：只把 Phase B 的已选 operator contract 从 JSON metadata
对象改为非 JSON、逐 claim 的固定行协议。每段只显示 ordinal、criterion id、actual operator 名及其 required
argument names、expected operator 名及其 required argument names；输入中不再出现四个 input-only metadata
key。

目标输出仍是未经改变的 `long-horizon.assertion-binding.v1`：每个 binding 必须严格只含
`criterion_id/actual_arguments/actual_transforms/expected_arguments/expected_transforms`。现有 parser、exact fields、
argument types、intent order、operator choice 合并、transform contract 和 proof engine 全部不变。

第一次与 correction 请求使用同一行协议。raw response、JSON extraction、parsed payload、contract error、最终
assertion 和 proof trace 继续完整持久化。运行时不得删除 extra fields、重命名 key、从 metadata 补 arguments、
选择 operator、替换 evidence id、生成 goal literal 或尝试候选。

## 3. 明确不改

- 不改 Goal、planning、Round7 obligation ledger/supplemental lane、action/G1i、validation v4 Phase A、read operator
  catalog、Phase B 输出 schema、proof、replan、final、工具集、并发 8、200 transitions、recovery budget、数据集、
  hidden acceptance、相似度或采样值。
- 不增加 evidence handle，不自动把 active task 改成 direct dependency，不因同源/不等而替换 expected。
- 不放宽 unknown/extra field 拒绝，不做 parser coercion，不读取 hidden acceptance 或 Codex answer 生成绑定。
- 不修改或选择 RWKV final output，不在线调参或依据单题结果改协议。

## 4. 必测

1. Phase B prompt 的 selected contract 区不包含四个 input-only metadata JSON key，且精确保留 RWKV 已选 operator
   与 required argument name。
2. 现有合法 binding 解析结果完全不变；extra/unknown/missing fields、错误 arguments、错误 transforms 仍拒绝。
3. actual/expected operator、criterion/order、argument/value 全由 RWKV 决定；运行时只按原 intent 精确合并。
4. semantic replan、不完整 coverage、direct dependency ownership、same-source independence 与最终 proof replay 不变。
5. 完整离线、LH-Control-30、历史 schema/恢复/异常/并发和 E2E-90。

## 5. 固定指标与上传门槛

专项报告 Phase B request、contract-valid response、各 contract-error 指纹、进入 proof/VERIFIED/Evidence 数，以及
External、Strict、completed、FP/FN、tokens 与非干预。主要协议指标是 contract-valid response 必须严格高于
Round7 的 `8/79`；不能把 protocol-valid 当成 proof-valid 或 completion。

上传门槛保持：Agent completed > 0、FP≤9、External≥8、Strict≥7，且 External 或 Strict 至少一项严格超过
Round2；离线、Control、因果链和 raw final byte equality 全过。否则不上传。
