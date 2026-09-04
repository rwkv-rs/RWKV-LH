# Strong Planner 调用链诊断

时间：2026-09-02（Asia/Shanghai）

## 结论

中转站连接方式正确，但 Goal Planner 的生产调用链存在提示合同与重试控制问题。HTTP 429 不是端点、认证、模型名、JSON Schema、seed、temperature、reasoning effort 或最大输出 token 不兼容造成的。

## 传输证据

使用与基线相同的 `.env` 绑定、`gpt-5.4-mini`、`/v1/chat/completions`、`response_format=json_schema`、`temperature=0.1`、`reasoning_effort=none` 和 seed 做脱敏探针：

- `/models`：HTTP 200，配置模型存在。
- 256-token completion：HTTP 200，返回非空内容。
- 4000-token completion：HTTP 200，返回非空内容。
- B01 第一条完整 Goal Planner 请求：HTTP 200；system/user 字符数分别为 1320/1555，prompt 5619 tokens，completion 321 tokens。
- B01 第二条本地修复请求：HTTP 429；中转站正文为“当前分组上游负载已饱和，请稍后再试”。

因此 429 是第二条请求命中的上游分组瞬时饱和，不是调用协议被拒绝。

## 第一条请求为何没有进入 RWKV

第一条 HTTP 200 响应产生的 GoalPlanPatch 被本地校验器拒绝：

```text
plan root must be workspace-relative: '/workspace/probe_service'
```

B01 用户请求与 workspace manifest 都使用工程相对语义，没有向模型强调或注入这个绝对路径。根因位于 Goal Planner 合同：

1. `plan_goal_patch` 的 system prompt 没有声明 `read_roots/write_roots` 必须是 workspace-relative，也没有明确禁止 `/workspace/...`。
2. `_goal_plan_patch_schema` 对两个 roots 字段仅声明普通非空字符串，没有相对路径 pattern。
3. 同一实现内的旧 `plan_contract_graph` 明确写有 “Use workspace-relative paths from the request and manifest”，说明两个 Planner 路径的合同不一致。

这使模型一次本来成功的 200 响应变成无效 patch，额外触发第二次 Strong Planner 调用。

## 修复调用不受已配置参数控制

基线把 `RWKV_LH_PLANNER_SEMANTIC_REPAIR_ATTEMPTS=0` 和 `SUPERVISOR_SEMANTIC_REPAIR_ATTEMPTS=0` 固定为 0，但 `StatefulGoalLoop._ensure_goal_plan` 仍使用硬编码 `for semantic_attempt in range(2)`。因此该参数只约束 OpenAI client 内部的部分语义修复，并不禁止 Controller 对 GoalPlanPatch 再调用一次 Strong Planner。

第二次调用被记录为可见的 `strong_planner_patch_rejected` / repair，而不是隐藏重试，但它与“semantic repair attempts 为 0”的运行配置含义不一致。

## 可观测性缺口

生产 `_request_json_single` 在 HTTP >= 400 时只保留 status code，丢弃中转站错误正文和限流/请求头。原审计因此只能显示通用 `rate_limit`，无法区分账号配额、请求频率和“上游分组饱和”。本次通过临时包装器才获得准确原因。

## 当前处置

- 未修改 Strong Planner、Goal Controller 或任何生成参数。
- 未把 `/workspace/...` 自动转换为相对路径；这不属于输出信封归一化，自动改写会掩盖 Planner 合同缺陷。
- 本次 B01 归档为提示合同缺口与上游饱和的混合无效诊断，不计 zero-State Agent 能力分数。
- 在修复前直接重复 B01 可能偶尔越过 429，但仍会把一次多余 Planner 修复调用混入基线，不应作为最终冻结基线。
