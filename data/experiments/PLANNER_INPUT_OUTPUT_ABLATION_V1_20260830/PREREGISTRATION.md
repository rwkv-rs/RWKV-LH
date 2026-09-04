# 强 Planner 输入—输出关系消融 V1 预注册

- 日期：2026-08-30
- 状态：API 调用前冻结
- 性质：控制面诊断，不是 Agent 能力发布分数
- 数据边界：只读取 `rwkv_agent_capability_ladder_v1/tasks.json` 的公开任务与公开工作区；不读取 `acceptance.json`。
- 模型：`gpt-5.4-mini`，无 fallback、无 reasoning_effort、temperature=0.1、max_tokens=4000。
- 每个格子只发起一次 HTTP 请求且不做 transport retry 或 semantic repair，使每一行对应一个独立的原始输入—输出样本。
- 不启动 RWKV、不占 GPU、不改变产品服务。

## 固定任务

1. `AGENT-LADDER-L2-REPAIR01`：相邻文件缩写、包内真实路径、不可修改验证器。
2. `AGENT-LADDER-L3-WEB01`：多文件现有 Web 项目。
3. `AGENT-LADDER-L3-QUEUE01`：跨模块状态机修复。
4. `AGENT-LADDER-L4-LEDGER01`：从零创建中型多文件项目。
5. `AGENT-LADDER-L5-RWKV01`：公开网络证据与多文件项目。

## 固定输入臂

- `A_CURRENT_DENSE`：当前生产 system prompt、当前 user payload、当前 strict contract-plan JSON Schema。
- `B_LEAN_PROMPT`：精简 strong-Planner system prompt；user payload 和 JSON Schema 与 A 完全相同。
- `C_LEAN_CONTRACT`：与 B 相同的精简 system prompt；user payload 相同；响应 Schema 只保留可观察义务和粗粒度阶段图，不要求 Planner 编写 typed-assertion DSL。

三臂均使用 `response_format={type: json_schema, json_schema: {strict: true, ...}}`。需求 `request` 保持 user payload 最后一个字段。

## 固定观测指标

- transport：HTTP 状态、延迟、错误类别。
- format：assistant content 是否为单个 JSON 对象、是否通过对应 strict Schema。
- understanding：公开请求中词法识别到的路径是否在完整输出中出现。
- typed burden（A/B）：路径是否全部出现在 assertion target/source；当前生产 `_contract_patch_from_value` 是否接受及拒绝原因。
- graph：节点 ID 唯一、依赖存在、无环；mutation 是否有覆盖全部写根的依赖 verify 节点。
- authority：输出是否出现当前 Harness 的具体 operation 名称；Planner 不应选择工具。
- size：输入各段 token/char、输出 byte/char、obligation/node 数。
- integrity：每个强模型原始 assistant content 原样保存，记录 UTF-8 SHA256 与字节数；不修改、补写或用修复轮替换。

## 固定解释与修改决策

1. 若 B 相比 A 提高合法结构率且不降低路径理解/图合法性，则删除过密提示规则。
2. 若 C 相比 B 进一步提高合法结构率，同时保持路径理解、图合法性和 Planner 权限边界，则生产 Planner Schema 精简为可观察义务 + 阶段图；typed 机械安全留在 Controller，不再要求 Planner手写 DSL。
3. 当前词法 typed-path 校验若拒绝了“完整输出已理解路径”的样本，判定为本地过约束，不把它计为强模型能力失败。
4. 不因本次输出修改数据、指标或判定口径；修改后另建验证目录，不覆盖本次原始结果。

