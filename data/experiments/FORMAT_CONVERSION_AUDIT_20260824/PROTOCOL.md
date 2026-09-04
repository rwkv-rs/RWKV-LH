# RWKV 原始输出与格式转换层统计协议

日期：2026-08-24

## 目的

统计当前 `direct-call-envelope.v1` / `action-arguments.v2` 边界面对真实 RWKV 输出时的格式分布、
转换使用率、通过率和拒绝原因；并以 SQLite 权威事件记录核对 `model_trace.json` 中的原始输出。
本轮只做离线审计，不修改模型、Prompt、转换规则、工具 schema 或业务逻辑。

## 固定数据

- 主数据：`data/experiments/Round162_typed_contract_full90_20260823/`。
- 数据版本：`RWKV-E2E-90 v1`，固定 B30/M30/H18/LH12 共 90 例。
- 运行协议：Round162 `tool_disclosure=full`，RWKV 为唯一工具操作者和参数生成者。
- Trace 总体：90 个 case 根目录下的 `model_trace.json`；统计单位为一条
  `model_session_generation_returned`，空 trace 的零请求 case 保留在 case 完整性统计中，但不进入
  “给定模型已经返回一次响应”的条件概率分母。
- 数据库总体：同一 Round162 目录下全部 `long_horizon.db`，包括 case store 和 atom worker store；
  从 append-only `events.data_json` 中读取 `model_call_accepted/model_call_rejected` 的完整
  `DecisionRecord.raw_output`，不使用 checkpoint 重复快照累计样本。
- 排除：Supervisor/GPT 输出、其他历史轮次、cache 内容、测试 fixture 和 benchmark verifier 输出。

## 预注册分类

### 原始表面格式

互斥主类：`empty`、`bare_json_candidate`、`fenced_json`、`fenced_plain`、
`unsupported_or_unclosed_fence`。另独立记录首尾空白。

### JSON 与调用信封

1. `canonical_function+params`：对象字段恰好为 `function`、`params`。
2. `alias_pair:<name-key>+<argument-key>`：name key 属于
   `function/name/tool`，argument key 属于
   `params/parameters/arguments/args/function_args`，且对象只有这两个字段。
3. `single_key_operation`：对象只有一个 operation 名字段，其值为参数对象。
4. `invalid_envelope`、`json_non_object`、`invalid_json`、`empty`。

以当前工作树的 `parse_model_command_with_trace` 重放，记录 exact transformation sequence、解析成功率、
operation 分布。格式解析成功不等于工具 schema 通过。

### 参数转换

从 SQLite 的 accepted decision 事件读取 `argument_normalization`，分别统计：

- 显式接口转换：alias、JSON 字符串解析、单位转换、固定 policy 字段删除、空 mapping、非语义注释；
- optional null 删除；
- registry default 填充；
- 完全无转换。

`final_answer` 不进入 action 参数转换分母。

### 结果与概率

- 所有比例报告精确 `count / denominator`、百分比和 Wilson 95% 区间。
- `accepted` 只以 SQLite `DecisionRecord.accepted` 为权威；trace commit/rollback 只作一致性核对。
- “转换后接受”仅表示响应经过透明格式转换并通过当前协议/schema，不表示任务语义正确。
- “转换救回”只报告可观测的格式边界反事实：非 canonical envelope 或 Markdown fence 若没有当前
  对应转换将无法进入 canonical call；首尾空白不单独计为救回，因为 JSON parser 本身可接受空白。

## 完整性与复核

必须输出：

1. 所有源 trace/DB 的绝对相对路径、字节数、SHA-256。
2. Trace request 与 DB decision 按 `request_id` 的覆盖率、raw output SHA-256 和字节完全一致率。
3. 每种观测格式以及主要拒绝类的确定性原始样本（保留完整 raw 字节字符串与来源引用）。
4. 机器可读 `statistics.json`、`raw_examples.json`、`source_manifest.json` 和中文 `REPORT.md`。
5. 发现任何一个 request 不一致时，不得把数据库/trace 合并为同一概率总体，必须分别报告。

## 当前代码边界说明

当前工作树默认 `tool_disclosure=progressive`，但 Round162 的正式数据使用 `full`。因此本报告只能估计
full-disclosure 下 RWKV direct-call 输出概率；`select_tool` 两阶段协议没有正式全量观测概率，不能从
Round162 外推。代码接受集合仍按审计时当前工作树静态列出，但不会把未观测格式记为模型输出。
