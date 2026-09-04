# Planner 精简契约整改 V1 预注册

- 日期：2026-08-30
- 依据：`PLANNER_INPUT_OUTPUT_ABLATION_V2_20260830/run_v2/RESULT.json`
- 依据 SHA256：`c89123a806f7c6a72e2f011076425c8d6fbe79c570bd7c21bea592c800743313`
- 架构不变：强模型只做 Planner/Reviewer；2.9B S66 Selector 只选工具；13.3B Executor 执行；独立 state；GPU0；本地 vllm-rwkv。
- 原始输出约束不变：不得修改、删除、重排、隐藏、截断、替换或“修复” RWKV 原始输出。

## 允许修改

1. Planner response Schema 只保留 obligation predicate/evidence kinds 和阶段图的 role/kind/effect/objective/dependencies/read/write scopes；删除 Planner 手写 assertion DSL、freshness、source preferences 和 action budget。
2. 所有 Planner obligation 作为 execution-evidence obligation；无 typed assertions 时由既有强 Reviewer基于公开 result capsules 审核，机械 veto 继续有效。
3. `write_roots` 上限从 2 提升到 8，以表达一个连贯的中型项目阶段；不得拆成标点拼接的伪路径。
4. capability projection、evidence hints、freshness 与 action budget 由 Controller 编译。投影来源继续是 `controller_capability_projection.v3`；Planner 不得选择具体 operation。
5. capability atom 的机械 action budget 上限从 4 提升到 12；legacy atom 仍保持 4。预算按阶段类型和写根数确定并记录规范化事件。
6. mutation 验证接受依赖图上的后续 verify；Controller 将其上游 mutation 写根并入 verify.read_roots。只有确实不存在后续 verify 时才添加一个通用安全 verify 节点，并记录结构规范化；不生成业务内容、工具或参数。
7. system prompt 精简；继续使用 strict JSON Schema、显式 `reasoning_effort="none"`、request 字节尾和 local repair 字节尾。

## 禁止修改

- 不改 Ladder 数据、隐藏验收、阈值或通过定义。
- 不根据 task ID、文件名或具体业务生成特判。
- 不让 Controller 选择具体工具、参数或业务实现。
- 不降低路径安全、图引用、无环、作用域、capability projection、Reviewer、事务完整性或网络策略边界。

## 固定验证

1. 单元测试覆盖精简 Schema、严格 JSON 参数、request 尾、机械预算、最多 8 个写根、legacy 预算不变、传递 verify scope 编译、缺失 verify 的机械安全节点、权限边界。
2. 相关测试与全项目测试全部通过。
3. 用相同 5 个公开任务做 Planner-only canary：5/5 HTTP/JSON/Schema/编译成功，具体 operation 越权 0，所有 mutation 有可达 verify，原始强模型输出哈希可复核。
4. 再按冻结 10 题、S66/G3/G6、GPU0 复跑真实 Harness；不覆盖旧基线。

