# Round72 预注册协议：统一固定边界与当前事实前沿

## 目标

Round72 只消除 Round71 已证实的公共结构阻塞，使 RWKV 已表达的 Goal、动作、证据引用和判断能够通过同一条可审计链路执行。效率、请求数、耗时和 token 不作为门槛；不得由控制器选择、补写、纠正或改写 RWKV 的语义结果。

外部参考边界见 `Round72_REFERENCE_ANALYSIS.md`。本轮只采用其中“历史区与 live frontier 分界”的原则，不引入外部模型、Router、state classifier、MCP、搜索服务或自由文本摘要事实源。

## 冻结证据与数据

- 上传基线：commit `14d864d71bf670b479a33f4fdb63b4772b69d3c8`，完整 90 题 Strict `31/90`、External `32/90`、Agent `55/90`、FP `24`、FN `1`。
- Round71 fixed15：Strict `0/15`、External `1/15`、Agent `0/15`。
- 人工逐题归因：`Round71_canary/MANUAL_CAUSAL_ANALYSIS.md`。
- 固定 15 题与顺序沿用 `Round71_canary/RUN_PROTOCOL.json`：B01、B02、B10、M01、M03、M06、LH02、LH05、LH11、B24、M12、M16、M18、H12、H13。
- 可见任务来源摘要：core30 `0bf73c9a...481c4c`、lh12 `d813a7bc...457a5e`、extension48 `384d52b5...ec7b`；隐藏 acceptance 运行时不可见。
- Codex 标准答案 `947a4b49...82d89b` 只允许运行结束后对比。
- 模型、采样、并发、max transitions 和相似度算法与 Round71 保持不变。

## 预注册改动

### R72-1：固定工具边界 v11

只在调用方已经唯一固定 `expected_name` 时接受以下闭集表示：

1. 多个 identity 字段（`name/function/tool/action/action_type/type`）的字符串值全部等于同一个 `expected_name`，其余为一个 arguments object；折叠为唯一 canonical identity。
2. 一个或多个相同 identity 加已声明的内联参数；只有 required 字段齐全、其余字段全部属于该工具 schema 时才把参数移入 arguments。
3. 固定 review 工具的标量形式 `{"review_action":"approve|revise","reason":"..."}`；只移动原值到 `decision`，不推断或补写 decision/reason。
4. `continuation_cursor`、`observation_ref` 加入闭集 copied-observation decorations，只接受 string 或 null，分离后不进入动作 arguments。
5. 注册精确动作名同义表示 `read_text -> read_file`；仅改工具标识，不改 path、offset、内容或其他参数。

所有转换必须记录 raw payload、normalized payload、双 digest、转换名和 normalizer v11。identity 冲突、未知字段、缺 required、未固定 expected tool 继续 fail closed。

### R72-2：Task commit 单一证据注册表

在现有 `ACTION:<attempt>`、`CHECK:<attempt>:Vn`、Memory refs 之外，把当前 Attempt ID 和它实际持有的 Artifact IDs 注册为可选择证据：

- Attempt 条目只投影已经持久化的 action、outcome、tool result/metadata 和 artifact refs。
- Artifact 条目只投影已经持久化的 path、sha256、media type、owner task 和 summary。
- 不创建新引用、不替换 RWKV 引用、不把引用是否“好”作为控制器选择条件。

目标是消除“状态里存在、提示中出现、但 registry 不允许选择”的 B10/LH05 断裂。

### R72-3：live frontier 置于响应边界末端

1. `select_action`：历史 execution capsule 和 prior review reason 在前；末端重复当前 Task ID/title/description/postcondition、完整 compact action catalog、允许名称和“只调用 select_action”的固定响应要求。
2. selected action arguments：历史 capsule 在前；末端重复当前 Task postcondition、固定 selected action 和只能使用该工具 schema 的要求。
3. Task commit draft/final：draft（若有）和历史 capsule 在前；末端放唯一 authoritative packet，包含当前 postcondition、当前 Attempt ID、当前 ACTION result、当前 deterministic effect checks 和完整 AVAILABLE EVIDENCE refs。
4. authoritative packet 明确：成功 ACTION 输出已经是一条 observation；观察型 postcondition 不需要另造 task-level artifact。读/list 仍不得被解释为写/copy/mutation。

末端包只重复已存在状态，不生成语义、证据、参数或答案。

### R72-4：质量容量而非效率容量

1. Goal audit 三次尝试的输出上限提高到足以容纳完整五字段调用；首轮和重试都要求简洁但不降低到 700 token。缺字段仍不得恢复。
2. initial plan 与 goal-obligation plan 的 immediately-ready Task 闭集上限从 8 提高到 32，与现有 task-batch/recovery 结构容量一致。执行并发仍由 runtime 控制，不能因第 9 个合法 Task 丢弃整批。

### R72-5：本轮明确不做

- 不添加由规则判断正确 action/answer 的 selector、ranker 或 tie-break。
- 不做 Plan 自由修复；计划执行可达性自审单独登记为下一轮候选，以便量化 B24/M01/LH02 的因果效果。
- 不接入 hidden-state 路由。上游 `0.9325` 是 R0–R3 难度分类，且当前转发端点没有已验证的 state API。
- 不实现 UI 标题、search summary、MCP 或另一个 Agent。
- 不删除请求、不缓存模型判断；效率完全不作为本轮优化目标。

## 测试要求

### 离线

- 全量 pytest。
- LH-Control `30/30`、frozen subset `5/5`。
- compile/diff 检查。
- 新增以下回归：
  - 相同重复 identity 成功、冲突 identity 失败；
  - identity+inline declared args 成功、未知/缺 required 失败；
  - fixed review scalar 成功，其他 fixed tool 不发生该转换；
  - 两个新 decoration 的类型与分离审计；
  - `read_text` 仅归一到 `read_file`，参数不变；
  - 当前 Attempt/Artifact refs 全部进入 registry，历史/未知 refs 仍拒绝；
  - Task commit 最后一个状态段是 authoritative packet，final draft 位于其前；
  - Goal audit 不再用 900/700 上限；
  - 9 和 32 个 ready Task 接受，33 个拒绝。

### 在线 fixed15

- 逐题保留 model trace、event log、state timeline、causal ledger、workspace 与外部验收。
- 每题人工判断最早错误环节，不只读取 terminal 聚合分类。
- 门槛沿用：Strict `>=6/15`、FP `<=3`、FN `<=1`，且 B01/B02/B10 全部 Strict。
- 未达门槛时不跑完整 90 题；先写 Round72 人工归因并预注册下一轮。

### 完整 90 题上传门槛

只有 fixed15 达标才运行完整 90 题。只有同时满足以下条件才提交并上传：

- Strict `>31/90`；
- External `>=32/90`；
- FP `<24`；
- FN `<=1`；
- final output 与 raw RWKV 输出保持逐字节一致；
- 没有通过隐藏 acceptance、标准答案或控制器语义规则筛选答案。

效率指标只记录，不参与任何 gate。
