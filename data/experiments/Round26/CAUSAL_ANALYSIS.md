# Round26 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：0/90（0.00%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 0
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 0/30 | 0/30 | 0/30 | 0 | 0 |
| medium | 0/30 | 0/30 | 0/30 | 0 | 0 |
| hard | 0/30 | 0/30 | 0/30 | 0 | 0 |

## 固定诊断指标

- 模型请求：271
- 本地输入 / 输出 token：755446 / 339962
- 平均模型决策时延：27418.36059479554 ms
- 可配对产物 byte-5gram 平均相似度：0.789417249498
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- task priority must be an integer: 18
- invalid_plan_schema: 15
- task_graph.edges must be empty; dependencies are authoritative: 14
- task required must be a boolean: 11
- causal task has unknown fields: ['required_postconditions']: 6
- expected_outcomes must be an array: 5
- plan_tasks_array_missing: 3
- causal task has unknown fields: ['required_arguments', 'required_postconditions']: 2
- task dependencies must be an array: 1
- registered plan wrapper requires exactly schema_version and task_graph: 1
- invalid expected_outcomes: ['services/api.json', 'services/web.json', 'services/worker.json']: 1
- invalid expected_outcomes: ['calculator.py contents are known']: 1
- causal task is missing fields: ['dependencies']: 1
- goal proposal has no success_criteria array: 1
- g1i_function_envelope_rejected: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：1 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：

## 本轮 observation gate 触发情况

- Prepared：0
- Cacheable / uncacheable：0 / 0
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- transparent_protocol_envelope_normalization: 1 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。
- goal_criterion_capacity: 0 题；goal proposal exceeded the fixed five-criterion contract。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

## 人工逐链复核

自动统计之后又逐题检查了 90 份 event log 与原始模型输出。89 题的第一个不可恢复断点在任务物化之前，只有
E2E-LH04 生成了 10 个 Task；它随后正确选择 `read_json` 和 `events/source.json`，但用 G1i 等价字段
`tool` 承载工具名，被当前边界拒绝。因此本轮没有证据表明读取决策本身是首要失败源。

任务物化前的错误不是 89 个独立能力缺陷，而是同一宽接口在相邻概念间放大的结果：

1. 模型同时看见 Task、完整 Action contract、task_graph edges、dependency_outcomes、expected_outcomes、
   required、priority、required_postconditions 等概念；它把执行器字段带回 Task，造成 priority 字符串、required
   字符串、required_postconditions 额外字段等 37 个主要终止。
2. dependencies、task_graph.edges 和 dependency_outcomes 同时表达因果关系，模型在字符串依赖、对象依赖和
   edge 列表之间重复表达；14 题的 edges 与 node dependencies 实际同向，却因冗余外壳被整体拒绝，另有对象依赖。
3. postcondition、expected_outcomes 和 verifier kind 同时表达“任务后应当看到什么”，模型把文件路径、自然语言事实、
   verifier 名称或对象写进 expected_outcomes。该字段并非启动读取所必需，却让至少 12 题在读取前失败。
4. plan/obligation/replan 虽共享 TaskNode，仍使用三个不同 envelope 和不同必填字段；这不是一个在线结构。
5. Goal-obligation capsule 把 `action_observations` 固定为空，并明确排除了全部 action-result memory。即使目录读取成功，
   下一轮 Task 扩展也看不到真实文件清单，无法完成“发现成员 -> 动态 fan-out”。
6. Controller 每轮只取 `ready[0]`，所以当前图即使有多个独立文件任务也不会并行执行。

因果链是：宽而重复的规划接口 -> RWKV 混用相邻字段 -> 严格 parser 在 Task 前拒绝 -> 没有读取 observation ->
obligation/fan-out/并行/聚合全部不可达。下一轮必须先缩成一个最小 Task batch，再让真实读取 observation 驱动后续扩展；
不能为每类错误增加 coercion 或答案筛选规则。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
