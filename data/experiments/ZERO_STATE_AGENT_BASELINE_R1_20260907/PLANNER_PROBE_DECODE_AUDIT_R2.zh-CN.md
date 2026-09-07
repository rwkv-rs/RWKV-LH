# Planner 已保存探针的离线解码与请求格式审计

本次只读核查已保存的请求与响应，离线调用现有解码器；没有发送 HTTP、调用模型或修改生产代码、测试、冻结参数。此前 `PLANNER_WIRE_DIAGNOSTIC_R2/` 中的请求重建与报告保持原样。

已证实：不能把本次完整 Planner 请求的 HTTP 500 归因于 `response_format` 字段。最小 JSON mode 请求完全相同的两次发送分别返回 500、200；完整请求保留和仅删除此字段均返回 500。最后一种对照只改变这一顶层字段，失败分别耗时 30.661 秒、31.111 秒。故删除字段不是已验证有效的修复。提供方内部路由、转换、计量和约 30 秒边界尚未归因，响应本身没有说明服务内部根因。

| 已保存探针 | HTTP | 当前内容解码器结果 |
| --- | --- | --- |
| PLANNER_ENVELOPE_PROBE_R1_json.json | 500 | 无成功模型内容 |
| PLANNER_ENVELOPE_PROBE_R1_plain.json | 200 | `{"ok":true}`，normalization=null |
| PLANNER_ENVELOPE_PROBE_R2_json.json | 200 | `{"ok":true}`，normalization=null |
| PLANNER_FULL_REQUEST_REPLAY_R1.json | 500 | 无成功模型内容 |
| PLANNER_FULL_WIRE_R1_plain.json | 500 | 无成功模型内容 |

plain 成功内容在 JSON 对象之后多一个换行，现有 `_decode_supervisor_json_content` 的 strip + json.loads 直接接受。两个成功内容都没有触发 Markdown/标签移除，也没有生成或补全语义字段。这个最小响应只证明内容封装可解析；`{"ok":true}` 不是 GoalPlanPatch，不能据此声称完整 Planner 角色协议已通过。

最小成功响应报告的 prompt_tokens 不同：plain 为 709；JSON mode 为 4416，其中 cached_tokens 为 3840。已核对两份存储请求仅差 `response_format`。这是提供方报告的计量差异，不能当作我方实际 messages 长度差异，也不足以证明其内部具体转换规则。

当前生产入口 `OpenAIGoalSupervisorClient` 只开放 `plan_goal_patch` 和 `review_goal_stage` 两种 Strong 角色调用（`rwkv_lh/supervisor_openai.py:3685`）。

| 当前阶段 | 模型路由与预算 | 实际 HTTP 格式 |
| --- | --- | --- |
| goal_plan，含初始、后续修订及本地验证修订 | Planner 主模型及配置的 fallback；`settings.max_plan_tokens` | `/chat/completions`，model、system/user 两条 messages、max_tokens、response_format=json_object |
| goal_stage_review | 仅 stage_checker_model；`settings.max_contract_review_tokens` | 同一 `_wire_request` 构造函数和相同字段结构 |

`_RESPONSES_API_PHASES` 当前为空（第 76 行），没有当前 Goal 阶段走 `/responses`；其分支保留代码不会由这些阶段选中。`_response_format` 第 1067 行对所有阶段返回 JSON mode；完整 schema 由本地类型转换和 Controller 验证约束，并未以 json_schema 发送。当前 GoalPlan 调用第 2964–2977 行和 Stage Review 调用第 3110–3117 行均走 `_request_json`，再统一进入 `_wire_request`。本轮没有完成 stage review 调用，因此不能从 Planner 探针对另一模型声称已验证兼容。

已有测试覆盖：`tests/test_supervisor_openai.py:901` 的 Goal Planner 测试断言 JSON mode、chat endpoint、1800 token 预算及角色边界；第 1145 行的 Stage Checker 测试断言 JSON mode 和独立模型、固定三字段输出；第 1202–1248 行覆盖裸 JSON、确切 json fence、已知标签封装，以及未知前缀、尾随文本、未闭合标签、非对象内容的拒绝。通用 supervisor 的其他入口也在第 1342、1512、1697、1778 行断言 JSON mode，HTTP 重试测试位于第 1561、1958、1992、2116 行。这些是 fake session/离线单测，不能证明提供方服务稳定。

目前没有需要立即实施的格式修复。若后续受控证据确认需要改变 transport 或输出格式，通用修复范围应为统一 `_wire_request`/`_response_format`，以及第 1331 行当前硬编码的请求审计 `response_format` 字段；须让日志准确描述实际发送内容。回归应同时覆盖两个当前 Goal 阶段、完全相同的重试 body、日志与实际 body 一致、裸 JSON 成功和不合法响应仍被拒绝，保持 GoalPlanPatch/GoalStageReview 与 Controller 语义约束。不能只针对某题、某个运行或第几次重试改格式；任何生产修改之后由主代理作废并重跑冻结的两臂。

机器可复核证据：`PLANNER_PROBE_DECODE_AUDIT_R2.json`，SHA-256 `115135ab408850aed9c00dc5c53c2dbbde59658051c575c628aca6213f2ae5ea`。该文件绑定本次全部五个输入证据、解码器源码、现有测试源码和作者脚本 SHA，记录逐项内容解码结果及请求字典对照。作者脚本为 `temp/audit_planner_probe_decode_readonly_r2_20260907.py`，已拦截 requests/session 和 socket connect；用项目 `.venv/bin/python` 通过其绝对路径运行成功。
