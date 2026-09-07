# 原生 Supervisor 适配最终代码审查

2026-09-07。独立只读复核本轮 `git diff`、新增 `rwkv_lh/runtime/supervisor_vllm_rwkv.py`、对应普通单元测试与已存红绿日志。没有修改生产或测试、调用推理、访问服务器或读取 Holdout / acceptance。源码与日志版本见 `FINAL_CODE_REVIEW_SHA256SUMS.txt`；此报告写入后冻结。

**当前审查未发现阻塞问题。此前提出的响应 metadata 异常归类、失败原值审计，以及随后发现的 usage 整体容器缺口均已补齐。** 这是对本轮代码边界的结论，不代表真实任务能力或全面回归已经通过。

| 复核项 | 最终实现与结论 |
| --- | --- |
| metadata 异常归类 | `runtime/supervisor_vllm_rwkv.py:69` 起将通用响应解包产生的 `ValueError/TypeError/OverflowError` 归一为 `RWKVProtocolError`，再由 `supervisor_openai.py:1436` 转为 `SupervisorProtocolError`。不会把这些错误当作 GoalPlanPatch 语义错误。 |
| usage 整体容器 | helper `:58` 明确要求 usage 是 Mapping，或者缺失/null；`["bad"]`、数字及空列表都在响应边界拒绝，因此不会继续到返回审计中的 `dict(usage)` 而漏出 ValueError。 |
| 失败证据 | `supervisor_openai.py:1423` 在任何 native 解码前记录 `attempt` 与完整 `deepcopy(dict(data))`。被拒绝的 token IDs、choices 形状、非字符串 text、usage、模型/响应 ID 都保存在原外壳中；没有复制 HTTP headers 或配置密钥。原文与规范化结果分开记录。 |
| State 与采样隔离 | helper `:23` 直接构造 typed `TextCompletionRequest`；所有采样字段显式固定，未调用全局 `get_request_sampling/get_runtime_settings`，没有创建 Executor ModelSession、继承 checkpoint 或使用 recurrent-state handle。请求显式带 `zero` 与 64 个零的 profile SHA。 |
| 前缀与 JSON 边界 | prompt 末尾实际发送同一 `GENERATION_PREFILL="<think"`；native text 必须从 `>` 开始，解码前仅合回该发送前缀。闭合标签与 JSON 必须由模型生成，原严格 decoder 继续拒绝不闭合外壳、尾随文字、第二个对象及无效 JSON，没有补造计划字段。 |
| 截断拒绝 | helper 要求恰好一个 choice 且显式 `finish_reason="stop"`；`length/content_filter`、缺失或未知结束原因都拒绝，即使尾部碰巧已有完整 JSON 也不放行。 |
| 缓存身份 | `supervisor_openai.py:2291` 起将 backend、endpoint、transport 和 canonicalized wire body 纳入缓存 key；body 包括模板、prefill、采样、BOS、stop、零 State 身份与输出预算，切换后不会沿用旧 chat wire 的 key。请求身份去重仍沿原 canonical cache 规则。 |
| 角色影响范围 | native 分支只服务 `goal_plan/goal_stage_review`。两个角色继续调用各自唯一 request builder、既有 schema/语义校验及 Supervisor session/锁/重试/熔断。Executor、Step Auditor、Finalizer、Final Auditor 的调用链未修改。 |
| 预算与公开配置 | 默认 Planner 输出预算变为 8192，读取超时变为 240 秒；Stage Checker 仍使用独立的 `max_contract_review_tokens=2400` 默认值。配置公开输出不含 API key。预算增大不提供计划完成权限。 |

已读到的原始验证记录：`ADAPTER_GREEN_TESTS.log` 为 47 passed；响应边界先 `RESPONSE_BOUNDARY_RED_TESTS.log` 的 4 failed，再 `RESPONSE_BOUNDARY_GREEN_AND_REGRESSION_TESTS.log` 的 121 passed；usage 容器补测先 `USAGE_ENVELOPE_RED_TESTS.log` 的 3 failed，再 `USAGE_ENVELOPE_GREEN_TESTS.log` 的 3 passed。本审查没有重复运行这些测试；另只读执行的 `git diff --check` 无错误。

本报告冻结时，全量 `tests/` 由主任务继续验证，最终运行结果另行记录。真实 Planner / Stage Checker 连接探针与能力评价也由主任务分别报告；不能用上述 mock 回归或代码审查替代真实运行结果。

审查源码 SHA-256：

- `rwkv_lh/supervisor_openai.py`：`281193aa5a098634a7c687111aa0fa7cce96093f17da8de634a9b70f16c764b9`
- `rwkv_lh/runtime/supervisor_vllm_rwkv.py`：`38bb953398ee0585efcf4d4e93cbfcb198e1b0f2445ed0e17bcad574768bf99c`
- `tests/test_supervisor_openai.py`：`6424cb95ee94f2069cb3215840ba2b6d67eca51fcdf2c58852805ecac8c4074d`
- `tests/test_supervisor_vllm_rwkv.py`：`600f815bc0a7f1cdcf49476713d287f53adfab6cedb076461336cefc0588a38e`
