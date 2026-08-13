# Round35 预注册协议：阶段专用紧凑 capsule

## 触发证据

Round33 Basic30 的 `25/30` Strict 失败中，23 题没有进入 Goal evidence 收口。逐题 trace 显示共同链路：

1. 动作 prompt 的 ACTIVE TASK 暴露 `action.type=model_action`、空 completion criteria、commit status 和内部状态字段；RWKV 在 B06、B08、B09、B11、B15、B16、B17、B21、B30 复制这些字段为工具名或参数。
2. dependency snapshot 以完整审计对象呈现，`source_label`、`source_url`、schema、artifact 元字段被复制进工具参数。
3. Task postcondition capsule 包含完整 Task/causal state；RWKV 频繁输出 `task_commit_status`、`task` 或 causal-state 对象。
4. 第二次协议请求回显 rejected JSON，错误字段在最近上下文中被再次复制。
5. B25 的 Goal parse prompt 直接暴露运行时绝对 workspace root，RWKV 把它写进 Goal constraint，后续动作再复制该绝对路径并被 Harness 正确拒绝。
6. 多题在生产动作已有 action result、deterministic check 和 post-action snapshot 后，又规划独立 verify/read/list Task，扩大协议失败面。

详见 `Round33_basic30_goal_frontier/CAUSAL_ANALYSIS.md`。

## 单一结构变更

为在线活跃阶段构造确定性的 phase-specific capsule，不再复用完整通用状态投影：

- Goal parse / plan：模型可见 workspace scope 固定为相对 `.`；真实绝对 root 只在运行时 GoalState 中保存。
- Action commit：仅包含 immutable Goal 摘要、五字段 active Task contract、真实 dependency observations、与当前恢复直接相关的最近失败以及固定 G1i action catalog。不得包含 `model_action` 占位符、completion criteria、commit status、causal-state schema 或无关 Task ledger。
- Task postcondition commit：仅包含 active Task contract、已提交的真实 action、observed action result 与 deterministic effect checks。不得包含全局 Goal criteria、完整 causal state、历史 Task status 或 artifact revision ledger。
- Failure analysis / replan：只呈现失败 Task contract、已观察 action/result/check failure、真实依赖和最小恢复 lineage；不重复完整 RunState。
- Protocol correction：只呈现确定性错误类别和唯一 canonical contract，不回显 rejected JSON 内容。

所有 capsule 都由已有 RunState/MemoryEntry 确定性投影；不生成任务内容、工具参数、decision、criterion 或答案。

## 规划提示的职责说明

明确告知 RWKV：每个生产动作后，运行时自动保存 action result、执行 deterministic effect checks、捕获 post-action workspace snapshot，并单独询问该 Task postcondition。若同一个生产 Task 的自动观察已足以判断其 postcondition，不要再增加仅为重复读取/列出同一产物的 Task。控制器不删除或合并 RWKV 生成的 Task；最小因果前沿仍由 RWKV 决定。

## 明确禁止

- 不根据题目关键词由规则选择、删除、重排或合并 RWKV Task。
- 不根据外部验收、隐藏标准答案或文件内容替 RWKV 决定 pass/replan。
- 不修改工具 action、arguments、workspace 结果或最终回答。
- 不把 summary 当作原始 dependency content；复制/计算所需的真实已观察内容必须保留。
- 不在 capsule 层补缺失 schema、字段或答案。
- Round35 不增加任何新的格式别名；Round34 转换表保持冻结。

## 固定验证

1. 单元测试：action capsule 不含 `model_action`、completion criteria、commit status、causal-state schema、workspace absolute root；包含真实 dependency content 和 pagination metadata。
2. 单元测试：postcondition capsule 只含五字段 Task contract 与真实 committed action；action result/checks 只出现于各自固定 prompt 区域。
3. 单元测试：Goal parse/plan prompt 不出现运行时绝对 workspace root，GoalState 仍保存真实 root 供 Harness scope enforcement。
4. 单元测试：第二次 goal/plan/action/task-commit/failure/replan 请求不包含第一次 rejected JSON 的唯一标记。
5. 单元测试：31 文件并行 fixture 仍按 list → bounded reads → per-file summaries → aggregate 执行；frontier 上限 8、真实内容可达。
6. 全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90、边界/异常/历史恢复回归。
7. 真实顺序：先 B02、B06、B13、B25、B29 定向 canary；因果链改善后再跑 Basic30。Medium/Hard 在 Basic 提升前不运行。
8. 保持 raw RWKV final output 字节级直通；冻结相似度算法不变。

## 成功判据

- 定向 canary 不再因内部 placeholder/audit 字段复制或绝对 runtime path 泄漏而失败。
- 仅 schema alias 的 B13 可由 Round34 纯格式层通过，同时多字段对象仍 fail-closed。
- Basic30 的 Strict E2E 高于 Round33 `5/30`，且新增 FP 单独报告；本轮暂不要求 FP 不增加，但不得使用 controller 语义规则压低 FP。
- 模型请求数、冗余 Task 数、格式拒绝数与首次错误阶段一并量化，不只报告 Strict 分数。
- 未达到改进前不提交、不上传。
