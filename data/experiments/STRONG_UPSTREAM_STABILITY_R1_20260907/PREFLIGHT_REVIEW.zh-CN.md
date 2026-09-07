# 强模型上游有限稳定性预检审查

2026-09-07；状态：**离线审查完成，候选配置已由主任务准备，等待实际 wire 冻结与执行；本审查未发出推理请求，不能判定上游稳定。** 本代理只读当前源码和已有请求工件，不读取环境文件、密钥或 Holdout / acceptance，不修改生产、评分、训练或旧工件。源码和输入 SHA 固定于 `PREFLIGHT_REVIEW_SHA256SUMS.txt`。

主任务已明确沿用当前生产的 **Chat / Chat** 路由，两角色固定为既有 `gpt-5.6-sol`，减少变量。代码证据为 `rwkv_lh/supervisor_openai.py:78` 的 `_RESPONSES_API_PHASES` 为空，`:1084` 对 openai-compatible 两种 Goal phase 都返回 `chat_completions`。本轮不修改该路由，也不通过探针临时替换常量。

凭据由主任务在现有 `SupervisorAPISettings.from_env()` 边界处理（`:189` 起，只加载 Planner / Stage Checker / SUPERVISOR 前缀；`:1043` 附近组装认证头）。主任务已告知 owner 提供了 key，保存于本地 ignored `.env.strong.local`，权限 0600；它只是候选配置，没有替换生产。本代理未打开该文件或自行验证 key。主任务只记录 endpoint/model 与 `api_key_configured` 等公开状态；密钥不得进入请求证据、脚本参数或报告。

## 固定链路与当前契约

| 环节 | 本轮应保持的生产行为 |
| --- | --- |
| 输入 | 从下表既有材料恢复 typed `GoalPlanRequest` / `GoalStageReviewRequest`，再调用各自唯一 `to_dict()`，经 `_render_user_payload` 序列化。禁止手写另一套角色协议。 |
| Planner | `plan_goal_patch():2905` 使用当前无步数/阶段数量上限的 prompt 和 schema；输出预算 8192。旧 reconstructed body 里的 1800 和旧 system prompt 仅为历史证据，不直接拿来发送。 |
| Stage Checker | `review_goal_stage():3141` 使用完整原请求和原只读职责；输出预算来自 `max_contract_review_tokens=2400`，不是 `max_review_tokens`。 |
| HTTP | `backend_profile=openai-compatible`；两角色均 POST `/chat/completions`。body 为 model、system/user messages、max_tokens、`response_format={"type":"json_object"}`。这条路不使用 native RWKV prefill/zero-profile xargs；四个执行/审计 RWKV 角色的 State 配置不受此预检改动。 |
| API 外壳 | `_request_json_single():1302` 要求 HTTP 成功、JSON 对象外壳、有效 `choices[0].message.content` 非空字符串；完整保留原始外壳与响应状态。 |
| content | `_decode_supervisor_json_content():868` 只接受一个对象，或其已支持的完整精确 reasoning / 小写 JSON 围栏外壳。不得删除任意 prose、找最后花括号、补字段或边看结果边加兼容。 |
| 计划合同 | `GoalPlanPatch.from_model_value` 及首轮/续轮额外校验，随后在原因果前缀重建的 plan 副本上运行既有 patch/依赖/阶段/根/repair 校验。只解析 JSON 不能冒称 Controller 接受。Stage 的 stage、step IDs、evidence refs 继续由真实请求绑定。 |

完整 JSON Schema 当前没有作为 `json_schema` 发给服务，本地也不是通用 jsonschema 执行器。实际门包括 JSON 模式请求、严格内容解码和手写合同校验。须将 HTTP 可达、JSON 可解码、角色合同有效分别记录，不能用 HTTP 200 或一个合法对象替代全部条件。

## 已选定、执行前冻结的有界矩阵

主任务已采用以下 10 请求顺序与 gate；实际 wire 及配置 SHA 在首次生成前写入执行登记，本报告不根据未来结果改门槛。

| 编号 | 输入来源 | 来源性质与保留要求 |
| --- | --- | --- |
| P0-A | `ZERO_STATE_AGENT_BASELINE_R1_20260907/PLANNER_WIRE_DIAGNOSTIC_R2/SUP-8069342ba94e4fc69692.reconstructed_body.json` 中的 user payload | 已有 RP-API-01 生产调用重建，revision=0。用当前 canonical builder 重新构造，保留材料，不重用旧 1800/prompt。 |
| P0-B | 同目录 `SUP-9bb02f7be600485aaedc.reconstructed_body.json` 中的 user payload | 已有 RP-API-02 生产调用重建，revision=0；与 P0-A 是两个固定来源。 |
| S1 | `VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/SMALL_STAGE_CHECKER_CONNECTION_FIXTURE_REQUEST.json` | 既有原测试捕获，真实 Harness write_file，全部模型/审计响应为 mock；完整 1 步 / 1 fact。不是生产 trace、评分或训练数据。 |
| S19 | 同目录 `STAGE_CHECKER_CONNECTION_FIXTURE_REQUEST.json` | 既有原测试捕获，真实 Harness reads、mock audits；完整 19 步 / 19 组 refs / 8 条原有有界事实，末步 revision=2。不得截断为小题。 |
| P1 | 同 Planner 重建目录 `SUP-9d719be01df5484fb546.reconstructed_body.json` 中的 user payload | 已有 RP-API-01 revision=1 的真实 repair continuation，保留 latest_audit 与 A00001、A00002、A00003 引用；不用初始请求伪造 continuation。 |

先按 **P0-A → P0-B → S1 → S19** 各执行一次。四项均过门后执行 P1；五项均过门后按 **P0-A → P0-B → S1 → S19 → P1** 再各执行一次。上限 **10 个逻辑请求、每个固定来源 2 次、concurrency=1**。任何预检失败都保留，停止本轮自动后续预检，剩余项记 `not_run`，不挑替代来源补满成功数。

主任务预检实例固定 `retry_attempts=1`、`semantic_repair_attempts=0`、`fallback_models=[]`、`plan_cache_enabled=False`，使每个逻辑请求对应一次可计数 HTTP 尝试；串行仍复用生产 session/请求锁。Planner 8192、Stage 2400、read timeout 240 秒、connect timeout 10 秒保持明确固定。预检不会通过重试、语义修复、备用模型或缓存吞掉首发失败。

19 步输入曾在本地 13.3B 的 16,384 上下文中预检为 15,067+2,400=17,467，未生成。该数字属于那次 native tokenization，**不能直接当作强上游 GPT 的 token 数**。本轮保留完整输入，按强上游实际能力检查上下文；若过长或能力未知并导致错误，应如实记录，不降低输入规模后仍标 S19 通过。

## 固定 gate 与证据

- 每次均须首发 HTTP 成功、在固定超时内返回、content 非空、结束原因明确且无截断，并通过当前 JSON 与角色合同检查。Chat 生产 decoder 本身没有仅凭 `finish_reason=length` 拒绝所有内容的独立门，因此预检另行记录并将截断视为不满足稳定运行条件；不修改生产 parser 或基线评分。
- 五个固定来源各两次全部通过（10/10）才报告「本轮有界连接与合同预检通过」。样本规模小，不能据此宣称长期稳定，更不是 Agent Strict/completed 分数。任何失败或 `not_run` 均不能报告全链 ready。
- Stage `advance` 和有依据、符合当前合同的 `repair` 都是合法角色输出。它们的语义内容单列，不能为了增加 advance 数重写事实或放宽审查职责。Planner 合同拒绝也必须单列为语义/结构失败，不能藏在 HTTP 成功数字中。
- 每次保存来源 SHA、canonical payload SHA、完整当前 system prompt/请求 body SHA、实际 model/endpoint/transport、call/attempt ID、HTTP 状态、elapsed、finish_reason、usage、原始响应外壳与 content，以及每层解析/合同结果。失败响应同样保留，禁止记录认证头。原响应不能经过截断、改字或字段修补后作为该次原始输出。
- 对 continuation 的 Controller 合同检查，应使用已有生产 trace 对应因果前缀的 plan，不能把现在工作目录里的其他 run 当作上下文。`temp/reconstruct_planner_wire_readonly_r2_20260907.py` 仅可用作历史重建来源说明；它写的是旧冻结工件且旧代码接口已变化，不应原地重跑覆盖历史。

凭据缺失属于尚未开始；HTTP/格式/合同失败属于已运行失败；基于既有 fixture 的连接验证属于测试来源。三者必须分开。即使预检通过，正式 Agent 双零运行也需要自己的完整冻结登记；本轮不生成角色数据、不训练、不改变评分，也不重新解释旧 baseline 结果。

当前主源码 SHA-256：`supervisor_openai.py=281193aa5a098634a7c687111aa0fa7cce96093f17da8de634a9b70f16c764b9`，`goal_loop_protocol.py=4df55bb88707887c5faee1f565ba818a77095622bba72451e547d92d69e0e98e`，`stateful_goal_loop.py=dfd87e18d3fe57454812a492ee8070f3cafeaeee71f2c661e689d907982d9245`。完整输入与配置加载源码 SHA 见清单。
