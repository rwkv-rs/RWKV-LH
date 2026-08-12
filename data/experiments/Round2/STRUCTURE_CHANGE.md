# Round2：透明协议外壳归一

## Round1 证据

Round1 的 90 题全量因果分析显示：

- 30 题的 RWKV 输出包含完整任务对象，但数组位于 `task_graph.tasks` 或
  `task_graph.nodes`，现有结构层只读取顶层 `tasks`，因此在执行前失败。
- 10 题的 RWKV 输出包含唯一、完整的 function name 与 arguments，但使用
  `function_call`、`type=function + function` 或 `function + arguments` 外壳，现有
  G1i 规范层将其作为未知字段拒绝。
- 22 题缺少直接 criterion 满足声明，6 题 Agent completed 但外部验收失败；它们是独立
  语义/完成边界问题，本轮不修改。

权威证据位于 `../Round1/causal_analysis.json` 的 `transparent_format_findings`、
`terminal_reason_counts` 和逐题 audit。

## 唯一结构变量

增加 `transparent_protocol_envelope_normalization`：

1. 完整 `task_graph.tasks` 直接别名为顶层 `tasks`；完整 `task_graph.nodes` 仅在每个 node
   已自带 `dependencies` 时直接别名为 `tasks`。不从 edges 推导、增加或改写依赖。
2. 完整的三种单 function 外壳映射为现有 `{name, arguments}`；arguments 为 JSON 字符串时
   仍只做 JSON 解码。
3. 每次保存原始 parsed payload、normalized payload 和 transformation 列表。
4. 混合字段、多个 function、缺失 name/arguments、缺失任务或不完整 JSON 继续 fail-closed。

## 明确禁止

- 不补任务、criterion claim、动作值、工具参数或文件内容。
- 不根据题号、题面、acceptance 或标准答案决定是否归一。
- 不筛选多个候选，不修改 RWKV 最终回答。
- 不改变题集、采样、并发、transition 上限、验收或相似度算法。

## 预运行门禁

- 离线回归：117/117。
- LH-Control-30：30/30。

## 全量结果与回档判定

- External acceptance：8/90，Round1 为 7/90，变化 +1。
- Strict E2E：7/90，Round1 为 5/90，变化 +2。
- False positive：12，Round1 为 6，变化 +6。
- False negative：1，Round1 为 2，变化 -1。
- 因果链完整：90/90；completed run 最终回答非干预：19/19。
- 运行后门禁：离线 117/117、LH-Control 30/30。

虽然 External 与 Strict 提升，但 FP 翻倍，不满足 `external 提升且 FP 不增加` 的 GitHub 回档门禁。
Round2 因此不上传为最佳点；透明归一机制保留为候选，但下一轮必须先修复由它暴露出的完成边界。
