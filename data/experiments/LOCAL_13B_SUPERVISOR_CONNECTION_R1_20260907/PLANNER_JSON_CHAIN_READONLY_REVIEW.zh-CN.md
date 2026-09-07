# Planner JSON 链与 13.3B 原始响应只读复核

日期：2026-09-07。范围：本地源码与已经存在的公开开发任务诊断响应。此次复核没有 HTTP / 模型调用，没有训练或读取 Holdout / acceptance。下述行号、字段和五步限制描述对应**移除 Planner 步数限制之前**的源码，版本由 `PLANNER_JSON_CHAIN_OFFLINE_EVIDENCE.json` 和 `PLAIN_COMPLETE_CONTRACT_OFFLINE_EVIDENCE.json` 内的源码 SHA 固定；后续授权修改不改变本报告的历史结论。

结论：生产链要求模型返回一个 JSON 对象，并发出 `response_format={"type":"json_object"}`。完整 GoalPlanPatch JSON Schema 没有作为 schema 发送给上游，本地也没有通用 JSON Schema 验证器执行该 schema；实际是提示词约束、上游 JSON 模式请求、内容解析以及若干层手写结构和业务校验。HTTP 200、API 外壳合法 JSON、content 可解码、计划能被 Controller 接受，是四个不同条件。

| 环节 | 实际入口与字段 | 约束实际在哪里执行 |
| --- | --- | --- |
| 请求取材 | `rwkv_lh/stateful_goal_loop.py:1362` `_issue_strong_plan_patch`；`:1427` 创建 `GoalPlanRequest` | 当前 durable plan、不可变请求、最近审查、Harness workspace manifest 和 action facts。不是另写一套 Planner 输入。 |
| 唯一输入构造 | `rwkv_lh/goal_loop_protocol.py:629` `GoalPlanRequest`，`:716` `to_dict()` | 顺序为 `run_id, goal_digest, plan_revision, active_plan, latest_audit, latest_stage_review, latest_controller_repair, workspace_manifest, recent_action_facts, current_requirement`；有本地修复时最后加 `local_validation_repair`。内部 `immutable_request` 对外命名为 `current_requirement`。 |
| prompt 与序列化 | `rwkv_lh/supervisor_openai.py:2812` `plan_goal_patch`；`:136` `_render_user_payload` | system 规定角色、五个顶层字段、stage/step 嵌套结构、职责/依赖/根/义务规则和只输出 JSON；user 为 canonical payload 的紧凑 JSON，保持需求与本地修复位于末尾。 |
| HTTP body | 同文件 `:1067` `_response_format`；`:1083` `_wire_request` | 当前 `_RESPONSES_API_PHASES` 为空，实际 `/chat/completions`。body 只有 `model, messages, max_tokens, response_format`；messages 是 system/user，生产 Planner `max_plan_tokens=1800`。不含 `json_schema/strict/grammar/tools`，也没有显式 temperature/top_p/seed。 |
| API 外壳提取 | 同文件 `:1280` `_request_json_single`，`:1363` 起 | 先检查 HTTP，再对 API 外壳 `response.json()`；读取第一项 `choices[0].message.content`，必须是非空字符串。不把独立 reasoning 字段拼接成回答。`finish_reason` 会记录，但 `length` 本身不是独立拒绝条件，内容解析仍会执行。 |
| content JSON 解析 | 同文件 `:859` `_decode_supervisor_json_content` | 去首尾空白后 `json.loads`，必须为对象。只容忍下面列出的完整已知外壳，不创建或补齐计划字段。 |
| 局部结构与语义 | `rwkv_lh/goal_loop_protocol.py:403` `GoalPlanPatch.from_model_value`；`GoalPlanStep`/`GoalObligation`；`supervisor_openai.py:2977` 起 | 校验顶层/嵌套字段集合、阶段结构、职责、相对根、ID、义务和若干非空/冲突约束；首轮必须有义务和新增步骤且不能替换/丢弃，续轮不得重定义义务。 |
| durable plan 接受 | `rwkv_lh/stateful_goal_loop.py:1458` 起；`goal_loop_protocol.py:1188` `apply_goal_patch`；目标校验 `stateful_goal_loop.py:1577` 起 | 在副本上检查修订、已完成步骤不可改、依赖有效性、阶段关系、义务绑定、替换/修复等；通过后才进入接受流程及 `goal_plan_patch_committed`。无效输出记录拒绝并可能用真实错误发起有界修复，不由 Controller 改写成有效计划。 |

离线复现调用 canonical builder、生产 prompt 和 wire 构造器，并在 HTTP 前拦截：重建 body 与原始 `SUP-9bb02f7be600485aaedc.reconstructed_body.json` 的全部字段值及消息字符串相等，差异字段为空。这证明本地构造一致，不声称比较了实际网络传输的外层 JSON 字节。

**JSON 外壳处理的边界。** 直接对象可接受；精确的小写 ` ```json\n … \n``` ` 可去围栏；完整前缀 `<think>…</think>` 或 `<analysis>…</analysis>` 后紧接对象可去前缀。任意说明文字、缺少开始标签、未闭合标签、大写围栏、尾随说明、非对象 JSON 均拒绝。没有“寻找最后一对花括号”的兜底；这些去壳也不递归组合。去掉的前缀记录长度和 SHA，不补造语义字段。已有普通单测覆盖这些边界（`tests/test_supervisor_openai.py:1202` 起）。

**不能把这称为完整 schema 校验。** `_goal_plan_patch_schema():2632` 声明了类型、`maxLength/maxItems` 等，但 `_response_format` 显式丢弃传入 schema 和 name，仅返回 `json_object`。本地手写校验覆盖部分结构和业务规则，并未通用执行该 schema。若干字段通过 `str()` 转换，部分数组通过迭代取值构造 tuple；字符串不会总在数组边界被立即拒绝。各项 `maxLength` 等并非由 schema 统一兑现。JSON 解码采用 Python 默认 `json.loads`，没有显式拒绝重复键或非标准 NaN 常量。`from_model_value` 在缺少 `goal_obligations` 时仍有 legacy-v3 分支，尽管首轮额外义务门会拒绝空义务。以上是实际执行缺口和回归风险，并非本次改 parser 的授权。

| 已存探针 | 原始结果 | 经生产 decoder / 契约的含义 |
| --- | --- | --- |
| `EXISTING_WIRE_PROBE.json` | 原完整 Planner body、JSON 模式，HTTP 500，0.065 秒 | 无模型 content，不能据此判断模型 JSON 能力。 |
| `WIRE_MINIMAL.json` | 去 JSON 模式的最小探针，HTTP 200，65 completion tokens，stop；249 字符，开头是 `>`，只有 `</think>` 结束标签，随后有 `{"ok":true}` | 独立 reasoning 字段为空；原 content 未通过 decoder，因为缺少完整开头标签。 |
| `WIRE_FAKE_THINK.json` | 完整 Planner，省略 JSON 模式并传 fake_think kwargs；HTTP 200，1800 completion tokens，length，7139 字符；没有结束思考标签或计划 JSON | 已耗尽生产同等输出预算；不能当作已得到有效 JSON。现有 tokenizer 复核证实这些 kwargs 未改变 token IDs，渲染尾部仍为 `Bot✿<think`，不能声称 fake_think 生效。 |
| `OUTPUT_INSPECTION_PLAIN_COMPLETE.json` | 完整 Planner，省略 JSON 模式，**仅诊断**上限 8192；HTTP 200，66.047 秒，4876 completion tokens，stop；有结束标签和完整 JSON | 原 content 仍缺开头标签，production decoder 失败。诊断分离的 JSON suffix 可解码，但不是有效 GoalPlanPatch：7 阶段 / 19 步 / 8 义务，19 步 `success_evidence` 都是字符串，8 义务多出 `success_evidence`，11 个非 observe 步骤有 read_roots，12 处同阶段依赖。 |

对最后一条**原样 JSON suffix** 调用生产 `GoalPlanPatch.from_model_value`，首个实际异常为 `ValueError: success_evidence item must be non-empty`：字符串被逐字符转成 evidence，遇到空白而失败。未修改字段后重试，也未把诊断去壳加入生产。五步上限不是这条输出的唯一失败原因；8192 仅解释完整输出形态，生产 1800 未被这次诊断改动，也没有能力分数。

**JSON 模式的已证实故障在上游生成前。** `JSON_ERROR_STACK_JOURNAL.txt` 对应本轮复测 HTTP 500，链为 `input_processor._validate_params → sampling_params.verify → _validate_structured_outputs → backend_lm_format_enforcer`，最终 `ModuleNotFoundError: No module named 'lmformatenforcer'`。这是 structured outputs 参数验证/模块导入失败，尚未生成模型 token。离线检查另发现 xgrammar 缺失，但不能把它说成该次 traceback 的直接异常。JSON 模式在该服务中意图请求结构化生成约束，当前失败不能宣称 grammar 已成功生效；即使 JSON-object grammar 成功，也不等同于 GoalPlanPatch 完整 schema 得到遵守。

本次没有修复这些问题。下一轮应分别验证上游 JSON 模式可用性、native 思考外壳衔接、输出预算和模型字段遵循，避免把其中任意一项修好等同于整个 Planner 已可用。用户随后授权的 Planner 步数上限清理另行记录，不能倒改本报告里的原始诊断结论。

证据与源码 SHA：`PLANNER_JSON_CHAIN_READONLY_SHA256SUMS.txt`；两份离线证据内另固定所用生产源码 SHA。报告只摘要模型输出形态，不重复完整思考文本。
