# Planner 精简契约 Canary V2 整改补充预注册

- 触发证据：`CANARY_V1_ANALYSIS.md`。
- 不改变原 5 个任务、模型、采样、严格 Schema、通过阈值或评价算法。
- 仍禁止任务 ID/文件名/业务特判，禁止 Controller 选择具体工具或参数，禁止修改任何 RWKV 原始输出。

## 唯一新增整改

1. 依据已经由 Controller 固定的 role/state，动态收紧 Planner 的 `kind` enum：
   - `role=work` 只允许 `investigate | mutate | verify`；
   - `role=finalizer` 只允许 `synthesize`。
2. 初始和纠错提示只描述 work kinds；replacement-finalizer 提示只描述 synthesize。其余精简提示不增加业务规则。
3. 保留现有 kind/effect 安全矩阵。不得将 `synthesize + mutation` 静默升级成写权限，也不得删除 Planner 原始响应中的字段来绕过校验。

这项修改是 response Schema 的通用权限约束：它让 strong Planner 在生成时选择合法工作阶段，而不是在响应后修补输出。

## 固定验证

1. 单元测试验证初始、纠错、finalizer 三种动态 enum，且非法组合仍 fail closed。
2. 相关测试和全项目回归通过。
3. 使用相同 5 题另存 `run_planner_only_canary_v2`，要求 5/5 HTTP、JSON、Schema、production 编译成功；operation 越权 0；原始和编译图的 mutation→verify 均为 5/5；伪路径 0。

