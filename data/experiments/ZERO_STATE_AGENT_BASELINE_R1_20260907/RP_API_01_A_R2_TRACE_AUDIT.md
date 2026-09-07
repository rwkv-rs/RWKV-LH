# RP-API-01 · all-zero A / R2 只读首错审计

本题记录为 `passed=false`、`agent_completed=false`，执行了 3 个 action，mutation 为 0，未产生 Final。导出的 `run_state.status=running` 表示已让出、可恢复的未完成运行。直接中断原因是修复规划请求遇到上游 HTTP 500：不是 200 次 transition 预算耗尽，也不是 RWKV 自行宣布完成。记录实际消耗 9 次 transition、续跑 0 次，`goal_transition_budget_exhausted=false`。

分析只使用本题导出的 audit/model/event/causal 记录和公开 workspace README；另外两题只核对终止模式。未读取 private verifier、reference、隐藏验收内容或 Holdout，未打开 SQLite，未调用模型，未修改冻结源文件、指标、服务或原始运行工件。完整 ID、原生成内容、错误、因果边及来源 SHA 保存在同目录 `RP_API_01_A_R2_TRACE_AUDIT.json`；本文件的判断不替代冻结评分。

| 顺序 | 原始证据 | 观察与归因 |
|---|---|---|
| 当前任务阶段 | `CE-000003`，Planner patch `GPP-b6498227116f4f82`，S1/observe | 要求检查 README、server.py、verify_public.py，当前禁止改文件；实现位于后续 S2。 |
| 首个明确拒绝 | request `MR-5cf7666195fd4390` → decision `D-220d193b98dc4f2f` → `CE-000009` | Executor 生成 `search_text`，`pattern="TODO\|FIXME"`、`path="."`；被 `operation_target_contract` 拒绝，原因是 `.` 超出本步骤的三个文件目标。JSON 已解析成功，不能称为 JSON parse error。 |
| 首次纠正 | `MR-8d44bbf0cd294258` → `D-b2a20110e0734d93` → `A00001`，事件 13/14 | 改为搜索 README.md，执行成功，0 命中，无文件正文证据。 |
| 第二个目标拒绝 | `MR-bcc6067a3a4742a6` → `D-fe953da81fd34618` → `CE-000025` | 新 action 会话仍搜索 README.md，而当时剩余目标为 server.py、verify_public.py；拒绝后纠正为 server.py。 |
| 后续动作 | `MR-3613c11898f148c7` → `A00002`；`MR-dadbe387e3b84d3f` → `A00003` | 分别搜索 server.py、verify_public.py，仍为同一模式，均 0 命中。三个 action 的 workspace 前后 digest 均为 `7d680298a31f92a5d7ee5265a09f8907c6f92879d11a5b62325b8a6bd27100cb`。 |
| 语义审计 | `MR-80b6fbc64ec044e4`，audit `AUD-629da0a523af440f`，`CE-000047/49` | Step Auditor 给 `repair`、`evidence_incomplete`，完成步骤为空，并指出三个文件的阅读语义及成功标准尚未证明。审计被接受，未放行完成。 |
| 真正中断 | Strong call `SUP-9d719be01df5484fb546`，`CE-000052` | 修复所需的 `goal_plan` 请求尝试两次 HTTP 后返回 500，分类为 `upstream`，可重试。没有得到可评价的修复计划。 |
| 保留未完成状态 | `CE-000053` → `CE-000054` | 写入 `SUP-PENDING-goal_plan-0001`，随后 `run_yielded`：`strong_planner_unavailable`、`resumable=true`、`termination_permitted=false`、`continuation=controller_resume`。 |

Selector 的三次 ensemble 选择均为 `search_text`，每次三个菜单顺序都投相同票，共 9 次精确选择。候选菜单是 `search_text/read_file/file_digest`。在 S1 的 inspect 阶段使用搜索是合理的可选手段；此时没有写入不构成 Selector 缺陷。实际不足在于工具与参数组合只搜索 TODO/FIXME，未取得所需接口、实现和验证程序内容。仅凭此轨迹不能认定某个唯一正确工具标签，也不能把这一结果全部归因于 Selector。

Executor 的 5 次命令生成都形成可解析 JSON，2 次违反当前目标契约，3 次最终执行。5 次均沿用 `TODO|FIXME`；该表达式也出现在通用工具说明示例中。“被示例牵引”可作为后续分析假设，但本题不能证明其因果机制。两次目标拒绝的原始错误与生成内容均已保存；是否存在通用 contract 实现缺陷仍为 **unattributed**，本审计未据此判定 Harness 有 bug。

机械 gate 在每次成功搜索后减少尚未覆盖的路径，只表明对这些目标执行过观测操作；无命中搜索并没有带回对应的接口内容。Step Auditor 随后明确要求修复，保住了语义完成边界。其 `model_session_candidate_rolled_back` 标记为 `auditor_state_non_authoritative`，表示 Auditor 的 State 不进入 Executor；不是审计输出被拒绝。三个 Executor 会话独立从 zero 启动，后续会话投影已有 action facts，未继承前一 Executor State；未发现此次中断由 State 合并或协议版本冲突造成的证据。

`model_trace.json` 的 **42 条记录不是 42 次模型生成**：

- 6 条 generation_started + 6 条 generation_returned，实际 6 个生成 request：Executor 5、Step Auditor 1。
- 4 次 bootstrap、5 次 schema disclosure、9 次 event append、6 条 normalization、5 次 candidate commit、1 次非权威 Auditor State rollback。
- Selector 的 9 次精确选择及 Strong Planner 的 2 个逻辑请求另有事件记录；Strong HTTP 实际尝试共 3 次。Finalizer、Final Auditor 尚未调用，其能力没有被本题观测到。

后续只核对了相同中断模式：RP-API-02、RP-MAINT-01 均在首次 `goal_plan` 遇到上游 HTTP 500，`CE-000003 → CE-000004 → CE-000005` 对应失败、pending、yield；两题都为 0 个 RWKV model trace、0 action，预算仅消耗 1 次。这支持存在跨题的上游可用性问题，不能把这两题的未完成解释为 RWKV 项目开发能力失败。

当前结论应并列保留：本题已有的观察动作没有满足 S1 的语义目标，而修复机会又被上游服务中断。尚未进入实现、真实启动、重启、并发验证阶段，不能据此评价这些能力，更不能在双零运行中修改代码或评分。后续处理由冻结运行纪律及全题结果决定。

可复核来源 SHA-256：

| 文件（相对本实验目录） | SHA-256 |
|---|---|
| `real_project_zero_a_r2/cases/RP-API-01/audit.json` | `545ba5327aaab77970a1ea40066260b430e7caeda8a320a4c80bf1c5f3a6f158` |
| `real_project_zero_a_r2/cases/RP-API-01/model_trace.json` | `b5e591436fbb21c6e718ff57cfb2e878269d4a759b7c8280485eeb9c94cb7ede` |
| `real_project_zero_a_r2/cases/RP-API-01/event_log.json` | `dbe6f61aab4cab7cbe0ffb6f41fd61b3bd6ec18855fc2fb60cc39f06acf7c17c` |
| `real_project_zero_a_r2/cases/RP-API-01/causal_ledger.json` | `52233581501c243b7c453624133d0b0f023301c0c64bbb5f6fddf6ba9b2ae6b1` |
| `real_project_zero_a_r2/cases/RP-API-02/audit.json` | `564c022fd0a2e78d3db2f3946b7926feda72c092aa21082903cf307fc5fb3d7c` |
| `real_project_zero_a_r2/cases/RP-MAINT-01/audit.json` | `5bf79b2c98137cbc8bb092483ffb692fbb1645ec43e2dcc4a9f0be67a69aaa9d` |
