# Round90 全调用逐题因果分析

## 结果

- Strict/Agent/External 均为 `2/4`；B01、H04 通过，B02、B03 双失败。
- FP `0`、FN `0`。
- B01 保持通过；Round89 的 H04 假阳性被消除并转为 Strict PASS。
- B03 从通过回归失败；B02 未改善。
- 四题继续全部有非空且精确匹配 RWKV Final lane 的回答。

## 因果结论

### 证据契约有效的部分

- B01 Goal 声明 `workspace_change`，实际 `write_file -> read_file -> task_done`，契约与
  独立观察均满足，完整通过。
- H04 虽把 create Task 声明成 `content_observation`，但只有真实写入后再 `read_file`
  才产生该证据，因此 Round89 的 `list_directory -> task_done` 路径不再可能通过；本轮实际
  完成写入、读取、Goal done 和 Final，完整通过。
- 这证明证据契约能恢复 FP 控制，不能撤回。

### B03 回归的最早环节

Goal 正确生成 read(`content_observation`) → update(`workspace_change`) →
verify(`content_observation`)。T1 正常读取并完成。T2 的**第一个模型输出已经包含完整正确的
`write_json` operation、path 和 value**，但用了另一种常见表示：

```text
function=lh_task_call + top-level task_id + operation_arguments{operation,operation_args}
```

当前格式层只接受 `params{task_id,operation,operation_args}` 或 direct operation，因而拒绝。
纠正后模型改为 `read_json`；workspace-change 证据契约正确拒绝其 Task done，随后模型在
recovery capsule 中重复读取直到 blocked。外部文件保持旧值。

因此 B03 的最早根因不是证据所有权，而是仍缺一个高频、值完整的 Task-call 表示转换。

### B02 的独立问题

Goal 把纯读取 Task 错误声明成 `workspace_change`。`read_file` 已成功，但这个契约按设计不能由
读取满足；模型又选择 `read_json` 并在真实失败后粘滞。Controller 不应从 objective 覆盖模型
声明。下一步应把证据类名称改成更不可误解的动词结果（如 workspace mutation、file content
read），而不是用规则猜测该 Task 的类型。

## 下一项整改边界

1. 格式层增加一个通用 Task wrapper 归一化：只有当 `task_id`、`operation` 和完整
   `operation_args` 都由 RWKV 明确提供时，才把 flattened/nested wrapper 投影为 canonical
   wrapper；不补任何字段、不解释值、raw 完整保留。
2. 证据类改用更明确的名称以降低规划误分类；Controller 仍只执行模型声明的契约。
3. 不放宽 H04 的结构证据要求，不用外部 acceptance 或自然语言规则筛选答案。
