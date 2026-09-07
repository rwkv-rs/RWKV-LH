# 13.3B 输出与 Planner JSON 接入检查

日期：2026-09-07；轮次 `LOCAL_13B_SUPERVISOR_CONNECTION_R1_20260907`。本轮按 owner 要求先核对输出与 JSON 返回机制。只做连接诊断及离线分析，没有启动新的 Agent 评测，**无新增 Strict / completed / mutation / 终止原因指标**。此前 R2 A 仍为 Strict 0/12、completed 0/12、mutation 0、12 次 `strong_planner_unavailable`，B 未运行；本轮请求不计入该结果、双零噪声或训练数据。

结论：13.3B **能够在思考结束后生成语法合法的 JSON**，但当前服务的 JSON mode、思考前缀传递和 Planner 计划契约是三个分别需要处理的问题。不能把 HTTP 200、JSON 能解析或删去思考文本当作 Planner 已接入成功。本次完整计划没有通过诊断时的合同。owner 随后明确取消 Planner 的步数要求，数量整改另记于 `PLANNER_UNBOUNDED_PLAN_R1_20260907`；本报告保留修改前观察，不把 19 步本身作为新合同缺陷，不重评分旧输出。

## 1. 实际输出格式

完整 HTTP 外壳是合法的 OpenAI-compatible JSON；Planner 真正需要的对象位于 `choices[0].message.content` 的文本中。此次 `message.reasoning` 为 null，思考文本没有被单独放入 reasoning 字段。默认模型输入末尾是：

```text
Bot✿<think
```

API 只返回后续生成的内容，因此实际 content 结构是：

```text
>思考文本……</think>{
  "goal_obligations": [...],
  "add_stages": [...],
  "replace_stages": [],
  "discard_step_ids": [],
  "reason": "..."
}
```

其中省略号是本报告示意；逐字原文见 [PLANNER_RAW_CONTENT.txt](PLANNER_RAW_CONTENT.txt)。这与“模型没有输出 JSON”不同：起始 `<think` 已被服务预填，content 开头只有 `>`。当前 `_decode_supervisor_json_content()` 接受单个 JSON 对象，或完整 `<think>…</think>` / `<analysis>…</analysis>` 前缀，或严格的单个 JSON 围栏；它不会猜测并删除未知文本前缀。因此这份完整 content 被现有 decoder 拒绝是可解释的传输边界不匹配，不能据此认定最终 JSON 语法错误。

本轮先前名为 `WIRE_FAKE_THINK.json` 的请求没有真正启用 fake 模式。零生成 tokenize/detokenize 核对：open、fake 和非法自定义 mode 都得到相同 1,984 tokens、相同 `Bot✿<think` 尾缀；标准 `add_generation_prompt=False` 则生效。源码表明通用 renderer 过滤了只放在 RWKV tokenizer `**kwargs` 中的自定义选项。详见 [模板核对](TOKENIZATION_KWARGS_FINDINGS.zh-CN.md)。不能把该请求解释为“fake 生效后模型仍思考”。

## 2. 这次 Planner 实际生成了什么

使用原 R2 A 的 RP-API-02 Planner 请求重建工件，保持 system/user 消息逐字不变，仅将模型名指向现有 13.3B。为了查看完整输出，独立诊断删除 `response_format`，把本次请求的 `max_tokens` 从 1,800 增至 8,192，read timeout 设为 240 秒；**生产预算、生产配置与评分未改**。这不是重评分，也不是只改变一个变量的效果实验。

结果为 HTTP 200，66.047 秒，prompt 1,984 tokens，completion **4,876 tokens**，`finish_reason=stop`，`stop_reason=✿`。仅有一个闭合 `</think>`；离线查看其后的原文是完整、语法合法的 JSON，且该后缀本身通过现有 JSON decoder。后缀只用于检查，没有提交 Controller 执行或写入计划缓存。自然结束证明这次不是 JSON 尚未生成就被截断；原 1,800 上限不足以容纳此次完整输出，但不能由一个样本推导通用预算。

完整对象见 [PLANNER_OBSERVED_JSON.pretty.json](PLANNER_OBSERVED_JSON.pretty.json)；原始后缀见 [PLANNER_OBSERVED_ANSWER_SUFFIX.txt](PLANNER_OBSERVED_ANSWER_SUFFIX.txt)。主要合同偏离：

- 生成了 **7 个阶段、19 个步骤**；诊断时仍存在五步限制，owner 已明确要求删除。此数量只作原始输出描述，不作为整改后缺陷。
- obligation 对象增加了不允许的 `success_evidence` 字段。
- step 的 `success_evidence` 返回字符串，合同要求字符串数组。
- 多处步骤依赖同一阶段内的步骤，违反阶段内独立、依赖只能指向更早阶段的规定。
- 多个 mutate 步骤带有非空 `read_roots`，违反此 phase 的根路径合同。

这些是原始输出的检查结论，没有通过截掉多余步骤、改字段类型、重排依赖或重写计划来“修复”答案。单个完整样本不足以评价 13.3B 的整体 Planner 能力；当前明确的是接入和合同验证尚未通过。

## 3. Planner 怎样请求和接受 JSON

当前两个 Goal 监督阶段均使用 `/chat/completions`。`_wire_request()` 发送 `model`、system/user `messages`、`max_tokens` 和 `response_format={"type":"json_object"}`。Planner 输入通过 `GoalPlanRequest.to_dict()` 构造，当前模型对象要求顶层五个字段：`goal_obligations`、`add_stages`、`replace_stages`、`discard_step_ids`、`reason`。

完整字段结构及职责约束写在提示词中；`_goal_plan_patch_schema()` 虽定义 schema，但 `_response_format()` 丢弃 name/schema，并没有发送 `json_schema` 强制这些字段。收到响应后依次读取 API 外壳、严格解码 content、调用 `GoalPlanPatch.from_model_value()`、检查 initial/continuation 条件，再由 Controller 按 durable plan 校验依赖、phase/root 与执行目标。不存在一个统一执行全部 schema 关键字的 `jsonschema.validate` 调用，不能把当前本地检查泛称为完整 JSON Schema 验证。

因此需要区分：HTTP 外壳 JSON、content 内 JSON 语法、Planner 字段合同、依赖和执行语义，以及 Agent 实际完成任务；前一层成立不证明后一层成立。

## 4. `json_object` 的 500 根因

开启该服务已有的 `--log-error-stack` 后，对同一原始 JSON-mode 请求重复一次：0.132 秒返回 500。完整 traceback 在 [JSON_ERROR_STACK_JOURNAL.txt](JSON_ERROR_STACK_JOURNAL.txt)：

```text
SamplingParams._validate_structured_outputs
  -> backend_lm_format_enforcer.LMFormatEnforcerGrammar
  -> lmformatenforcer.TokenEnforcer
ModuleNotFoundError: No module named 'lmformatenforcer'
```

失败发生在 API 进程验证输入参数时，尚未提交 EngineCore 或执行模型生成。底层异常被包装为无消息 `EngineGenerateError`，解释了此前只看到的 500。它不证明 Planner 的 messages 字段格式错误，也不是模型输出了错误 JSON。环境另有 Xgrammar 缺失等独立发现，但本次直接 traceback 是 `lmformatenforcer`。只补一个依赖是否足以完成 structured output 尚未验证，不能提前宣称修复。

## 5. 变更范围与后续边界

未修改 `rwkv_lh/`、角色职责、协议 builder、解析器、State 或其他角色模型；没有调用中转服务，没有训练或新建数据集，没有读取 Holdout。为取得异常证据，只向现有 executor 服务 launcher 加入已有日志开关并从本地上传、重启；没有修改模型权重、采样参数或 engine 依赖。服务日志开关变更见 [LOGGING_DEPLOYMENT_CHANGE.json](LOGGING_DEPLOYMENT_CHANGE.json)。服务器未执行 Git。

待接入工作必须保持角色不变：正确处理当前 13.3B 原生生成边界，明确使用的 JSON 输出机制，并让原始模型结果通过现有 Planner 合同；Stage Checker 共用监督 endpoint，正式替换时亦需核验其合同。其他角色保持原样。不能通过放宽合同、替模型改计划或额外模型调用掩盖失败。当前没有宣称切换完成，也没有恢复全面测试。

本轮不是两臂中的一臂。后续更换 Planner 后端或运行参数时，必须另建执行冻结并从新 workspace/State 完整运行两遍，不与旧中转 R2 A 直接配对。本轮只更新现状文档，保留旧冻结文件与原始评分。

数量整改前完整测试为 **697 passed in 57.15s**，记录见 [FULL_TESTS.log](FULL_TESTS.log)；数量整改后的测试独立记录，不混用此结果。本轮全部证据和脚本快照 SHA 见 `ROUND_SHA256SUMS`；原始输出 SHA-256：`974b18376e57129363568916b6e9fec2e346fbe3c4cf032cc193c40b2a6f1186`。
