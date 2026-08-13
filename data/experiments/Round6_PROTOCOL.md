# Round6 预注册：Progressive-Disclosure Read Operator Assertion

预注册日期：2026-08-12（任何 Round6 RWKV-E2E-90 请求之前）

## 1. 固定依据

Round5 External `12/90`、Strict `0/90`、Agent completed `0/90`、FP `0*`、FN `12`。28 题产生
58 个 assertion attempt；40 个顶层 validation 合同有效，55 条实际 assertion 全部 REJECTED，
无损归一化 `0/55`、proof pass `0/58`、CriterionEvidence 0。

55 条的首个拒绝原因是 source 不相容字段 39、联合枚举/占位 source 12、自创字段 4。模型常逐字输出
`workspace|action_result`，或在 workspace/action_result 中填满合同示意的全部可选字段。comparison 已有
49/55 正确输出 `exact_equals`，说明下一步应降低 source/selector 参数合同暴露面，而不是删除 RWKV 输出字段
或放松 exact proof。

固定数据与结果摘要：

- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`
- Round5 results SHA-256：`759ec15cd09ab538e2bb02902415d8839742827b6848d0772c03f69166c85fb6`
- Round5 assertion analysis SHA-256：`c4d850f021f057154c4fefd48b8a35b3b24d40fbf3c7bd2f86785e8c1aac4908`

## 2. 唯一结构变量

实施 `progressive_disclosure_read_operator_assertion.v1`：把 validation assertion 从同时暴露全部
`source + selector + optional fields` 的抽象联合 schema，改为“RWKV 先选具体只读 operator，再绑定所选
operator 参数”的两阶段协议。proof 的独立性、exact equality、scope 与 provenance 语义不变。

该结构借鉴 Prime Agent 的模型边界协议工程，以及 RWKV-LH 已验证的“紧凑 action catalog → 单个已选 G1i
tool contract”；不复制 Prime Agent 代码、provider、RLM、subagent 或产品形态。

### 2.1 Phase A：validation v4 intent

同一次 semantic cross-check 返回 `long-horizon.validation.v4`：

- `decision=pass|replan` 与 reason；
- decision=pass 时，每个 declared criterion 恰好一个 intent；
- 每个 intent 由 RWKV 给出 criterion、subject、producer、`comparison=exact_equals`、一个 exact
  `actual_read_op` 和一个 exact `expected_read_op`。

Phase A 只显示紧凑 read-operator catalog，不显示包含联合枚举字符串或全可选参数的 JSON 模板。Actual 可选：

- `workspace_text`、`workspace_json`、`workspace_json_pointer`、`workspace_sha256`、
  `workspace_directory_file_set`、`workspace_path_exists`
- `action_output_text`、`action_output_json`、`action_result_json_pointer`
- `dependency_artifact_text`、`dependency_artifact_json`、`dependency_artifact_json_pointer`、
  `dependency_artifact_sha256`
- `dependency_memory_text`、`dependency_memory_json`、`dependency_memory_json_pointer`、
  `dependency_memory_sha256`

Expected 只可选：

- `goal_literal`
- `dependency_artifact_text`、`dependency_artifact_json`、`dependency_artifact_json_pointer`、
  `dependency_artifact_sha256`
- `dependency_memory_text`、`dependency_memory_json`、`dependency_memory_json_pointer`、
  `dependency_memory_sha256`

每个 operator 名本身明确 source 与 selector。运行时不能根据文件类型、criterion 文本或 action result 替
RWKV 选 operator。

### 2.2 Phase B：仅披露已选参数合同

仅当 Phase A semantic pass 且 intents 顶层合同有效时，增加一次
`long-horizon.assertion-binding.v1` 请求；同一 attempt 的全部 intents 合并在一次请求中，不按 criterion
重复调用。请求逐 intent 只展示 RWKV 已选 actual/expected operator 的具体参数签名：

- workspace operator：只暴露对应的 `path`，以及需要时的 `pointer/recursive/path_type`；
- action operator：只暴露空参数或需要时的 `pointer`；
- dependency operator：只暴露 `task_id + artifact_id|memory_id`，以及需要时的 `pointer`；
- goal literal：只暴露 `goal_quote + typed value`。

Phase B 仍由 RWKV 给出所有参数和 transforms。零参数 transform 分别登记为
`{"transform_op":"count"}`、`{"transform_op":"sum"}`、`{"transform_op":"object_set"}`、
`{"transform_op":"sort"}`、`{"transform_op":"sha256"}`；`group_sum` 还必须由 RWKV 给出
`group_pointer/value_pointer`。prompt 以逐项签名列出，不提供可照抄的联合值。

绑定响应必须与 Phase A intents 数量、顺序和 criterion_id 完全一致。运行时按位置合并同一 RWKV 的 intent
与 binding，不选择候选；raw Phase A、raw Phase B、组合 assertion、operator→ProofExpr 转换 trace 和求值
结果全部持久化。

### 2.3 语义结果隔离

- Phase A semantic replan 不调用 Phase B，proof 不能覆盖 replan。
- Phase A semantic pass、Phase B 无效时，Task semantic decision 保持 pass，但 Goal assertion fail-closed，
  不生成 CriterionEvidence。assertion 参数失败不能反向把 RWKV 的 Task 判断改成 replan。
- explicit required `model_cross_check` 仍复用 Phase A semantic decision；不会再调用 optional criterion
  semantic check。
- 不增加 proof rejection 后的 semantic correction。Phase A 与 Phase B 各保留原有上限的一次格式纠正。

## 3. 明确不改

- 不改 Goal、plan、action、replan、final prompts；不改工具集、G1i action 协议、采样、并发 8、200
  transitions、recovery budget、数据集、hidden acceptance 或相似度算法。
- 不从 Goal 自然语言、task action、deterministic verifier、文件内容、题号、hidden acceptance 或 Codex
  标准答案选择 read operator、参数、transform、expected value 或 comparison。
- 不删除 null/多余字段，不把联合字符串拆成多个候选，不尝试多个 operator 后选能通过者，不补缺失参数，
  不把 proof rejection 改成 pass。
- 不修改、筛选、重写或替换 RWKV final answer。

## 4. 必测

1. 每个 operator 的 exact 参数集合与 actual/expected source 边界；未知 operator/参数 fail-closed。
2. Phase A 选择、Phase B 参数与 transform 顺序的无损组合；raw/combined/normalized 全可追溯。
3. binding 缺失/重复/乱序 criterion、数量不等、非法 transform 均整批拒绝，不选候选。
4. semantic replan 不 binding；semantic pass + binding fail 不改变 Task pass，但无 Goal evidence。
5. explicit model cross-check 的 Phase A 只调用一次；每个 pass attempt 最多一次合并 binding 请求。
6. final revalidation、v1-v4 state history、raw final byte equality、完整离线与 LH-Control-30。
7. 完整 E2E-90、Basic/Medium/Hard 各 30、全因果链、边界/异常/历史恢复回归。

## 5. 固定指标与上传门槛

报告 External、Strict、Agent completed、FP/FN、Phase A/B 请求、intent/binding/normalization/proof 通过率、
prompt/output tokens、产物相似度与 final 非干预。

Round5 不是 checkpoint。新 GitHub 最佳点必须有 Agent completed > 0、FP≤9，并相对 Round2 满足安全后的
Pareto 门槛：External≥8、Strict≥7，且 External 或 Strict 至少一项严格更高；离线、Control、因果链与
final 非干预全部通过。否则只保留本地完整实验数据，不上传。
