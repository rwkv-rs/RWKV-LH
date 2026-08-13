# Round9 预注册：Single-Claim G1i Assertion Binding

预注册日期：2026-08-12（任何 Round9 RWKV-E2E-90 请求之前）

## 1. 固定依据

Round8 External `12/90`、Strict `0/90`、Agent completed `0/90`。copy-resistant 行协议把 accepted binding
response 从 Round7 的 `8/79` 提高到 `13/88`，但 45 个 Phase B event 仍有 32 个在两次响应后合同失败；13 个
合法 event 形成 15 条 assertion，全部 proof rejected。

RWKV-LH 的 action lane 已采用“RWKV 先选一个 action type，再用单工具 G1i 调用填写 arguments”的边界。固定
E2E 中该协议明显比多对象自定义 JSON 稳定。Prime Agent 可借鉴的核心也是统一内部工具协议、适配只发生在模型
边界，而不是为每种状态发明不同的通用产品形态。

固定摘要：

- Round8 results SHA-256：`619bcfb1f3c065d2c5a3992a60fe3026490ec0dddfea56e78f50d30349d5b4aa`
- Round8 binding analysis SHA-256：`7e5ae0eeaddf86cbd93a622e45ee22af5d73914aebb83ab4b36569ff44b8296c`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`

## 2. 唯一结构变量

实施 `single_claim_g1i_assertion_binding.v1`：validation v4 Phase A、read operator catalog 与 intent 内容完全
不变；Phase B 不再要求一个 RWKV 响应同时返回多 claim binding 数组，而是按 Phase A 的原顺序，对每个 intent
分别发出一个只含 `bind_criterion_assertion` 的 G1i tool dialog。

每个动态工具合同只暴露该 intent 已选 actual/expected operator 所需的四个 arguments：
`actual_arguments/actual_transforms/expected_arguments/expected_transforms`。operator 名、criterion id、subject、
producer 与 comparison 已由同一 RWKV 的 Phase A 决定，因此像 action type→arguments 一样作为本次单工具作用域
固定，不要求 Phase B 重复输出。Phase B 仍由 RWKV 自己填写 path/task/artifact/memory id、pointer、Goal quote、
typed value 和所有 transform。

运行时只接受标准 G1i `{name,arguments}` 及已登记的透明单 function 外壳/arguments JSON string；name 必须精确
为 `bind_criterion_assertion`，arguments 必须精确匹配四字段及所选 operator 的参数合同。每 claim 最多一次
correction；任一 claim 失败则本 event 不执行部分 proof。程序只按原 Phase A intent 顺序一一组合，不修改任何
RWKV 字段或尝试候选。

## 3. 明确不改

- 不改 Goal、planning、obligation、action、validation v4 Phase A、operator 选择、proof、evidence、replan、final、
  工具集、并发 8、200 transitions、recovery budget、数据集、hidden acceptance、相似度或采样值。
- 不自动把 active task 改成 dependency，不过滤同源、不替换 expected、不生成 Goal quote/value。
- 不删除 extra fields、不补 missing fields、不解析 prose、不基于 proof error 尝试别的 handle/operator。
- 不读取 hidden acceptance/Codex answer 生成 binding，不修改或选择 RWKV final output，不在线调参。

## 4. 必测

1. 每个 intent 只产生一个单工具 G1i scope，顺序、criterion/operator 固定为 RWKV Phase A 原值。
2. canonical、function_call、typed function、function alias 与 JSON-string arguments 的透明归一完整审计；混合/未知
   字段继续拒绝。
3. wrong tool name、extra/missing binding fields、错误 argument type、错误 transform 与部分多 claim 成功全部
   fail-closed。
4. 合并后的 assertion 与原 Phase A intent + raw Phase B arguments 字段逐字可追溯；proof/replay 不变。
5. 完整离线、LH-Control-30、历史 schema/恢复/异常/并发和 E2E-90。

## 5. 固定指标与上传门槛

报告 Phase B claim scopes、G1i response/normalization、event 全量合法率、claim/proof/evidence，以及 External、
Strict、completed、FP/FN、tokens 与非干预。协议指标至少应使 protocol-valid event 高于 Round8 的 `13/45`；
但 protocol-valid 不能替代 proof-valid 或 completion。

上传门槛保持：Agent completed > 0、FP≤9、External≥8、Strict≥7，且 External 或 Strict 至少一项严格超过
Round2；离线、Control、因果链和 raw final byte equality 全过。否则不上传。
