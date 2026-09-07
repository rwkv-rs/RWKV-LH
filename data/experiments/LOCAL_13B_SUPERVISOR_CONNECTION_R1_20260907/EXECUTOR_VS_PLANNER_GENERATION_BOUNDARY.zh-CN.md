# 现有 13.3B Executor 与 Planner chat 的生成边界

本报告只读当前源码与已保存开发运行证据，没有模型调用、代码/服务/配置改动。Executor 已有一次调用 JSON 能被接受，不代表 Planner 的 GoalPlanPatch 合同也能被满足；主代理新的 plain 完整输出诊断与生产预算不同，不能并入 1800 token 基线成功结果。

## 两条路径的实际差别

| 边界 | 当前 independent-selector Executor | 当前 Supervisor Planner chat |
| --- | --- | --- |
| 输入语义构造 | executor_args_v4.build_prompt_source / render_prompt | GoalPlanRequest.to_dict + 原 Planner system prompt |
| 最后生成前缀 | `\n\n**Tool Call:**\n\n```json\n` | RWKV chat renderer 默认 `Bot✿<think` |
| 推理调用 | 原生 `/state/create`、append / fork 后 `/state/generate` | `/chat/completions`，messages 经过服务 chat template |
| grammar | native SamplingParams 没有 structured_outputs | 原请求 json_object 触发结构化输出依赖校验 |
| 停止边界 | JSON_CALL_STOP_SUFFIXES，含关闭 fence 与后续对话分隔 | chat 默认 Bot 分隔 / EOS，Supervisor 未发同一套 stop |
| 输出验收 | function / params 单调用，操作及参数合同另检 | GoalPlanPatch / GoalStageReview 原结构和 Controller 语义校验 |

`rwkv_lh/goal_state_protocols/executor_args_v4.py:482` 的 render_generation_prompt 只做 render_prompt(source) + TOOL_CALL_JSON_CONTINUATION_ANCHOR。前缀常量定义于 `rwkv_lh/model_io.py:21`。当前 independent Executor 的 bootstrap 仅固定角色职责和等待已选择操作（model_io.py:203），随后 model.py:2577 / model_session.py:258 将唯一当前协议输入及 Tool Call anchor 放到实际续写末端。model_io.py:249 的 validate_independent_executor_generation_input 验证协议来源、字节、最后 anchor；第 294 行附近明确拒绝在当前 Executor 输入前插入旧 Assistant JSON anchor。

需要区分日志标签和真实输入：model_session.py:1004 的 bootstrap 事件在 native_tool_call_json 默认 false 时记录 generation_anchor=`assistant_json`。该字段没有作为请求送给服务器，也不是一种引擎 decode mode；当前 independent Executor 后续实际生成由 render_generation_prompt 的 Tool Call anchor 决定。不能从这一标签推断它走 `Bot✿<think` 或一个 assistant_json 服务解码器。

NativeRWKVModelSession.generate（model_session.py:1285）校验当前协议并调用 native_client.state_generate（第 1317 行）；runtime/openai_compat.py:641 传 parent_state_ref、绑定摘要、采样、max_tokens 和 stop 至 `/state/generate`。服务器 `vllm/plugins/rwkv_native_state.py:584` 取得明确 parent binding，用 pending token 和原生 State 续写；第 312–341 行直接构造 SamplingParams + TokensPrompt。这里没有 messages、chat template、reasoning parser、response_format 或 structured_outputs，故正常 Executor 不会遇到 Planner chat 的 `<think` 前缀和本次 LMFE 导入故障。

本仓库 `state_router/local_backend.py` 是 Selector direct-model/身份装载相关入口，没有 assistant_json 生成或 JSON 提取实现；不应把它视为当前 13.3B Executor 服务的聊天转换器。Executor 实际使用上面的 native state endpoint。

## JSON 提取不能互换语义

`ModelSession.parse_with_trace`（model_session.py:686）先调用 `_restore_attested_stop_suffix`（第 144 行），仅当 finish_reason=stop 且原生成 token IDs 明确证明关闭 fence 被服务 stop 删除时恢复该原始 fence。它不会修补 length 截断内容。

随后 `model_io.py:581` 的 parse_model_command_with_trace 使用 `_extract_json`（第 472 行）：去首尾空白、处理完整 Markdown fence；对尾随第二个对象有单调用专属截取；另外有结构性转义引号的窄修复和 function/name/arguments 等调用 envelope 归一化。这里不是一个任意 prose 中查找 JSON 的函数，也不剥离不闭合或缺失起始的 think 标签。其最终目标是一个工具调用，不是规划 patch，不能把该 parser 用在 Planner 上并借此放宽 Planner 的原合同。

Planner 的 `_decode_supervisor_json_content`（supervisor_openai.py:859）仍只接受裸对象、确切小写 json fence、完整的已知 think/analysis 标签前缀等已有封装；GoalPlanPatch.from_model_value 与 Controller 后续验证负责 cardinality、字段类型、依赖、阶段和覆盖合同。修好 completion 封装只解决输送问题，不能把不满足这些合同的计划计为成功。

## 可复用组件及限制

现有通用原始文本入口是 `OpenAICompatibleRWKVClient.text_completion`（runtime/openai_compat.py:309）和 `TextCompletionRequest`（runtime/protocol.py:57、payload 第 75 行）。当前 vllm-rwkv-native profile 的路径是 `/completions`（openai_compat.py:157），其 prompt 是已经构造好的原始文本，不经过 Chat 模板；组件已有显式采样、zero profile pair、返回 token IDs、输出原文/摘要、预算调用链。这一 transport 可以作为接入候选复用，当前 SupervisorAPISettings / _wire_request 尚没有路由到它的配置。

可以复用 transport 的能力不意味着可复用 Executor 角色协议或 Tool Call prompt。若实施 Planner 原始文本输送，仍应使用原 GoalPlanRequest 和 Planner system prompt，保持同一字段、语义约束和原 Planner decoder。也不能复用已有 Executor 的 native State lane 给 Planner，以免改变角色 State 职责。`ASSISTANT_JSON_CONTINUATION_ANCHOR`（model_io.py:20）虽是已有文本常量，但是否用于 Planner 及如何组成完整请求目前没有生产接口或验证结果，本报告没有新增模板或角色协议。

## 源码 SHA

- executor_args_v4.py：`4aec4e16bf839ea87e4be95b628e6a077300aab7f3db72bd5736e4b8fa3bc5ed`
- model_io.py：`6e6a88099e17285eeb8cb15501c9d490f837d938d53feadd7807ba3bb76b014f`
- model_session.py：`a84acb2d6b35c94fc7abd719a46f7c0deec6aaa8eb5ad1595a4e6cbf9825350a`
- model.py：`5d995a19f834c03b38d73649796c6009cd8aad63f2e33e246b6c985e1df77095`
- runtime/protocol.py：`7c30cebf88ee25fa0dcf5b4733095841f5c7d31fe846314cb4548280a54a9003`
- runtime/openai_compat.py：`e5387de61d1793f82b2da0a7739d80a8b7f5be247838956514f20acc1b1c4d38`
- state_router/local_backend.py：`525fd436909dbc19fa72cd9d92f4c5e8ded43f0e91f0d1e9aebb0c806051cf41`
- 远端 vllm/plugins/rwkv_native_state.py：`159bf9a82a11052f5aad7efc374d176fc5699644960611358ea5c62ee98199fb`

这些源行与 SHA 对应当前只读审计时点；没有为此次对照修改协议、parser 或停止边界。
