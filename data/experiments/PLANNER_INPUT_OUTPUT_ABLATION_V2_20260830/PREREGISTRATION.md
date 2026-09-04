# 强 Planner 输入—输出关系消融 V2 预注册

- 日期：2026-08-30
- 状态：API 调用前冻结
- V1 作废原因：误省略正式配置要求的 `reasoning_effort="none"`；V1 原始文件保留，仅作故障证据。
- 性质：控制面诊断，不是 Agent 能力发布分数。
- 数据边界：只读取 `rwkv_agent_capability_ladder_v1/tasks.json` 的公开任务与公开工作区；不读取 `acceptance.json`。
- 模型与固定参数：`gpt-5.4-mini`；无 fallback；显式 `reasoning_effort="none"`；temperature=0.1；max_tokens=4000。
- 每个格子一次独立 HTTP 请求；transport retry=0（总尝试数 1），semantic repair=0。
- 不启动 RWKV、不占 GPU、不改变产品服务。

## 固定矩阵

任务固定为：`AGENT-LADDER-L2-REPAIR01`、`AGENT-LADDER-L3-WEB01`、`AGENT-LADDER-L3-QUEUE01`、`AGENT-LADDER-L4-LEDGER01`、`AGENT-LADDER-L5-RWKV01`。

- `A_CURRENT_DENSE`：正式 system prompt + 正式 user payload + 正式 strict contract-plan Schema。
- `B_LEAN_PROMPT`：精简 strong-Planner prompt + 与 A 相同的 payload/Schema。
- `C_LEAN_CONTRACT`：精简 prompt + 相同 payload + 精简 strict Schema（可观察义务和阶段图，不含 typed-assertion DSL）。

三臂都必须实际发送 `response_format.type=json_schema`、`json_schema.strict=true` 与显式 `reasoning_effort="none"`；`request` 是 user payload 最后字段。

## 固定指标和决策规则

- 逐样本记录 HTTP、延迟、JSON 对象、对应 Schema 校验、公开请求路径在完整输出中的覆盖、节点唯一性/依赖/无环、mutation→verify 覆盖、具体 Harness operation 名称越权、输入输出尺寸。
- A/B 额外执行当前生产语义校验，只记录接受布尔值与原始拒绝原因；不发修复轮。
- 强模型原始 assistant content 逐字节保存并记录 SHA256/字节数，不做提取、删除、替换或补写。
- 若 B 优于 A 且不降低理解/图指标，删除过密 prompt；若 C 进一步优于 B且保持理解、结构和权限边界，则精简生产 Schema，并把机械安全约束留在 Controller。
- 若完整输出理解了路径、但仅因 assertion target/source 的词法精确匹配失败，判定为本地过约束，而不是强模型能力失败。
- 运行后不得改变数据、指标、分组或决策规则。

