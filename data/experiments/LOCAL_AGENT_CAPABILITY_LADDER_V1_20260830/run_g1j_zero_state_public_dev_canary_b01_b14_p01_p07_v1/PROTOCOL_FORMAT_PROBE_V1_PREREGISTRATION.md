# G1J 全 zero State 分阶段输出格式探针 V1

时间：2026-09-02（Asia/Shanghai）

## 目的

在继续 Agent 能力基线前，使用已登记的五个 G1J 分阶段 train/dev 提示模板，直接调用当前真实 zero-State 服务，测量每个环节实际产生的原始输出形态。该探针只诊断协议格式，不计入 B01–B14 或 P01–P07 能力分数，不训练 Head 或 StateTune。

## 固定运行身份

- Selector：当前 G1J 2.9B hidden-feature + 已登记 Head，State profile 为显式 zero。
- Executor / Step Auditor / Finalizer / Final Auditor：当前 G1J 13.3B，State profile 为显式 zero。
- 生成温度：`0.1`。
- `top_p=1.0`、`top_k=0`、presence/frequency penalty 为 `0.0`、penalty decay 为 `0.996`。
- 停止串：生产登记的 `JSON_CALL_STOP_SUFFIXES`，不做输出修补或语义重采样。

## 固定样本

每个阶段分别从已登记的 train 与 dev 文件最多各取 16 条。选择算法为：当 split 不少于 16 条时，对文件总行数 `[0, n-1]` 使用包含首尾的 16 个等距下取整索引；当 split 少于 16 条时全量使用该 split；运行后不得替换样本。

启动前校验记录：最初预登记假定所有 split 均不少于 16 条，但 Finalizer dev 实际只有 12 条。第一次生成矩阵在任何模型请求发出前即失败。这里将样本规则修订为“不足 16 条则全取”，不改变输入变体或评价指标。最终样本数为 Selector 32、Executor 32、Step Auditor 32、Finalizer 28、Final Auditor 32；13.3B 生成请求总数为 404。

首轮 404 次生成完成后的必要旧协议对照：`production_full_plus_json_anchor` 仍把新 `ExecutorArgsPromptV1` 放在旧 lane 内，不等价于用户已长期验证的 `render_independent_executor_tool_disclosure`。为回答“为什么没有使用原格式”，对同一批 32 条 Executor 样本增加 `previous_verified_executor_full`，输入严格由独立 Executor bootstrap 加旧 request-last disclosure 组成，不改目标和指标。追加后 13.3B 请求总数为 436。

旧模板对照初次使用格式探针的 320-token 上限，其中 9/32 以 `length` 结束；生产 Executor 上限实际为 1800，Finalizer 为 1400。为避免把探针截断误判为格式错误，增加相同输入与相同样本的 `previous_verified_executor_full_production_limit`（32 条，1800 tokens）以及 `current_production_full_production_limit` Finalizer（28 条，1400 tokens）。这是预算一致性修正，原 320/512-token 记录继续保留。最终生成调用总数为 496。

用户随后指出 G1J 可以从字面输入 `**Tool Call:**` 续写以显露其 agentic 输出格式。单样本、无停止串的诊断表明，该锚点会生成 fenced `name/arguments` 调用，并继续伪造 `### Tool Output` 与后续 `### Assistant` 轨迹。为把这条线索变成可复核的全角色结果，在不改样本、目标、服务或评价指标的前提下，增加三个固定变体：协议原文后追加原生 `**Tool Call:**`；协议原文后追加 `**Tool Call:**` 并预开 ` ```json `；当前生产完整输入把末尾 JSON 锚点替换为 `Assistant: **Tool Call:**` 并预开 JSON 围栏。Executor 额外对已验证旧完整模板做相同替换。仍使用生产停止串，因此模型一旦生成闭合围栏即停止，不能把伪造的 Tool Output 当作真实环境结果。这些请求是格式诊断，不计入能力分数。

上述 Tool Call 首轮沿用格式探针预算（Executor/Auditor 320，Finalizer 512），出现的非 JSON 全部以 `length` 结束。为公平选择生产模板，追加相同 Tool Call 输入的生产预算对照：Executor 1800、Step/Final Auditor 400、Finalizer 1400；Executor 同时对当前错误拼接与旧式完整工具合同测试。样本、seed、采样参数、停止串和解析指标不变。

归一化后语义扫描发现 Final Auditor 的完整模板虽能 32/32 生成 `audit_decision`，但工具 schema 只声明 `step_id` 为任意字符串、`step_complete` 为任意布尔值；26/32 沿用 Step Auditor 语义填写了具体步骤，另 6/32 缺字段。生产内核要求终局审计不得完成步骤。为验证根因，追加 `current_production_full_terminal_constants`：输入仅把 Final Auditor 工具 schema 中 `step_id` 收紧为 `const: ""`、`step_complete` 收紧为 `const: false`，role payload、样本、seed、采样、预算和停止串不变。该变体只约束模型输出，不在解析或归一化后补写参数。

`terminal_constants` 的 320-token 首轮只有 6/32 通过完整终局语义，表明 schema `const` 本身不足以消除 Step Auditor 先验。追加两版 400-token 生产预算提示对照：`explicit_final_fields` 在 `current_question` 逐项要求六字段，并明确对 ready/repair 两种 verdict 都固定空 `step_id` 与 false `step_complete`；`explicit_final_skeleton` 再附带六字段参数骨架。两者都保留相同证据、候选、工具名、verdict 选择和内核校验，且不在输出后修改参数。

六字段骨架使 29/32 完整输出通过终局语义，剩余 3/32 都因 reason/gaps 展开过长而在固定 400-token 预算内截断。为在不放宽预算的情况下选择稳定模板，增加 `explicit_final_concise`：只要求 reason 为一句简洁句子、每个 gap 为简洁且唯一的条目，不重复证据或复述提示；并用相同输入分别测试旧 `Assistant: ```json` 与 `Assistant: **Tool Call:** + ```json` 边界。

Step Auditor 的原完整生产模板达到 32/32 表层解析、30/32 完整角色语义；仅有两条漏写 `step_id`，其余参数未被转换层修改。追加 `current_production_full_explicit_step_fields_production_limit`：在 `current_question` 明确六个必需字段、把 `step_id` 字面绑定到输入中的 active step，并声明 continue/repair 的 `step_complete`、evidence_refs 和 gaps 关系，同时要求简洁 reason/gaps。工具、样本、seed、采样、旧 JSON 锚点和生产 400-token 预算不变。

`explicit_step_fields` 导致 29/32 输出退化为缺少函数 envelope 的裸六字段 decision 对象；接受它需要由控制器推断 `audit_decision`，不符合纯表层归一化边界，因此淘汰。增加更窄的 `current_production_full_step_id_const_production_limit`：role payload 和原 `current_question` 完全不变，只在已展示的 Step Auditor 工具 schema 中把 `step_id` 设为当前 active step 的 `const`，仍要求模型自行输出完整 envelope。

`step_id_const` 完整角色语义为 25/32，低于原模板 30/32，亦淘汰。最后增加 `current_production_full_minimal_step_binding_production_limit`：tool schema 不变，不给 JSON skeleton，只把原 `current_question` 改为必须输出 `audit_decision` function call、保留六字段并逐字复制 `active_step.step_id`；采样、锚点和 400-token 预算不变。

## 固定输入变体

Selector 只走当前生产 Selector-Intent 服务与 Head，不调用文本生成。

四个生成角色测试：

1. `dataset_raw`：数据文件登记的 `prompt` 原文。
2. `protocol_plus_json_anchor`：`prompt + "\n\nAssistant: ```json\n"`。
3. `current_production_full`：当前生产代码实际构造的完整角色输入。Auditor 和 Finalizer 经通用 bootstrap；Executor 经独立 Executor bootstrap 后追加当前 G1J prompt。
4. `production_full_plus_json_anchor`：仅 Executor 增加，用于隔离当前生产完整输入缺少 JSON 生成锚点的影响。
5. `protocol_plus_tool_call_native`：协议原文后只追加 `"\n\n**Tool Call:**"`，观察原生完整 agentic 起始形态。
6. `protocol_plus_tool_call_json_open`：协议原文后追加 `"\n\n**Tool Call:**\n\n```json\n"`，由输入承担开围栏，输出在生产闭围栏停止串处截断。
7. `current_production_full_tool_call_json_open`：把当前生产完整输入末尾的 `Assistant: ```json` 生成边界替换为 `Assistant: **Tool Call:**` 加预开 JSON 围栏；当前 Executor 输入本来不以生成锚点结尾，故直接在其尾部追加同一 Tool Call 锚点。
8. `previous_verified_executor_full_tool_call_json_open`：仅 Executor；对旧式已验证完整 Executor 模板做同一锚点替换，用来区分完整 Tool contract 与 G1J 分阶段 payload 的影响。
9. `current_production_full_tool_call_json_open_production_limit`：与变体 7 字节相同，只把最大输出长度恢复到该角色生产预算。
10. `previous_verified_executor_full_tool_call_json_open_production_limit`：仅 Executor；与变体 8 字节相同，最大输出长度恢复为 Executor 生产预算 1800。
11. `current_production_full_terminal_constants`：仅 Final Auditor；完整生产输入中只收紧终局审计工具 schema 的两个常量字段。
12. `current_production_full_explicit_final_fields_production_limit`：仅 Final Auditor；在变体 11 基础上逐字段明确终局审计合同，使用生产 400-token 上限。
13. `current_production_full_explicit_final_skeleton_production_limit`：仅 Final Auditor；在变体 12 基础上增加六字段参数骨架，使用生产 400-token 上限。
14. `current_production_full_explicit_final_concise_production_limit`：仅 Final Auditor；六字段骨架加简洁/去重要求，使用旧 JSON 生成锚点和生产 400-token 上限。
15. `current_production_full_explicit_final_concise_tool_call_production_limit`：仅 Final Auditor；与变体 14 字节等价的角色合同，改用 Tool Call 预开 JSON 边界，使用生产 400-token 上限。
16. `current_production_full_explicit_step_fields_production_limit`：仅 Step Auditor；六字段与 active-step 绑定的显式合同，保留旧 JSON 生成锚点，使用生产 400-token 上限。
17. `current_production_full_step_id_const_production_limit`：仅 Step Auditor；原完整生产模板只增加 active `step_id` schema 常量，使用旧 JSON 生成锚点和生产 400-token 上限。
18. `current_production_full_minimal_step_binding_production_limit`：仅 Step Auditor；不改 schema 的最小六字段与 active-step 绑定提示，使用旧 JSON 生成锚点和生产 400-token 上限。

不得向任一模板添加基准工作区路径、服务器路径或解释性提示。

## 固定输出与指标

逐请求保存：输入哈希、模板来源和行号、原始可见文本、原始 token ids、token 解码文本、finish reason、严格 parser 结果和 parser 错误。

按阶段/变体汇总：

- `visible_empty_rate`
- `stop_only_rate`：可见文本为空，但原始 token 解码后仅为已登记停止串。
- `strict_parse_rate`
- `correct_function_rate`
- `target_exact_rate`

Selector 另记录期望 label、实际 eligible-logit argmax、准确率和完整 raw logits 摘要。

## 解释边界

- `final_answer` 只是 Finalizer 候选；只有 Final Auditor 返回合法 `ready_for_final` 后才具有 Goal 停止权限。
- 一次协议拒绝不是 Goal 停止条件。
- 本探针只用于冻结格式；不根据结果修改指标、样本或阈值。
