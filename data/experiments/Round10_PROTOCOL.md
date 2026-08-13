# Round10 预注册：Canonical G1i Outer Framing

预注册日期：2026-08-12（任何 Round10 RWKV-E2E-90 请求之前）

## 固定依据

Round9 External `15/90`、Strict/Completed `0/90`。17 题触发 33 个 single-claim scope，66 次响应全部未通过
标准 G1i normalization；63 次稳定输出 `{bind_criterion_assertion: ...}`。与成功 action lane 对比，Round9 有
one-item tool list，但任务正文没有复用 action lane 的明确句子：`Use the G1i function-call shape {name,
arguments}`。这是一项模型边界 framing 差异，不涉及 evidence 语义。

- Round9 results SHA-256：`548040b44914975103c6b5d9c530490f41d20f29bf04a330c1a0a4582fbe5712`
- Round9 G1i analysis SHA-256：`594e99a4e544c294ddfb6a4fa7351f3d74b7c55bb60b9e02e122785ebb6a42e7`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`

## 唯一结构变量

实施 `canonical_g1i_outer_framing.v1`：只在 Phase B 初始正文和 correction 中明确要求整个响应使用 exactly two
top-level keys `name` 与 `arguments`，`name` 精确为 `bind_criterion_assertion`，`arguments` 按 one-item tool
schema 填写。文字复用现有 action lane 的已验证 framing。

不添加示例 values，不补任何 arguments。标准 G1i normalizer 及其现有 canonical/function_call/typed
function/function alias/JSON-string arguments 白名单完全不变；Round9 的 `{tool_name: args}` 不登记、不猜测。

## 明确不改

Goal、plan、obligation、action、Phase A、single-claim 拆分、动态 tool schema、sampling、proof、evidence、replan、
final、数据、并发、transition、评价和上传门槛全部不变。不得修改/选择 RWKV final，不得读取 hidden acceptance
或 Codex answer 生成输出。

## 验证与门槛

新增 prompt exact-byte 测试，并运行完整离线、Control、E2E-90、边界/异常/恢复回归。报告 canonical call、透明
normalization、protocol-valid event、proof/evidence/completion。

上传仍要求 Agent completed > 0、FP≤9、External≥8、Strict≥7，且 External 或 Strict 至少一项严格超过
Round2；离线、Control、因果链、raw final byte equality 全过。否则不上传 Round10，当前最佳仍是 Round2。
