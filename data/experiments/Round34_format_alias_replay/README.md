# Round34 纯格式别名离线 replay

## 数据记录

- 来源：`data/experiments/Round33_basic30_goal_frontier/cases/*/model_trace.json`
- 来源版本：Round33 Basic30，2026-08-13，30 个 case 的原始模型请求/响应 trace
- 用途：在不重新采样 RWKV 的情况下，计算预登记 schema 别名转换的上限与 fail-closed 行为
- 文件范围：30 个 `model_trace.json`
- 文件集合摘要：按路径排序后，对每个文件运行 `sha256sum`，再对完整摘要流运行 `sha256sum`，结果为 `20c84c2cdd87bed9f418af8fbdf4f132f6441cebbd5dc7a42f56126fcc9ee1a1`
- 生成方式：使用 `jq` 读取 `model_protocol_parsed` 事件；不修改原 trace，不执行外部验收，不模拟后续模型采样

## 固定 replay 结果

### Task postcondition commit

| 对象类型 | 数量 | 纯转换后的结果 |
|---|---:|---|
| canonical schema，恰好三字段 | 98 | 原本已通过 |
| `rwkv-lh.task-commit.v1`，恰好三字段 | 9 | 只改 schema 后可通过同一个 canonical validator |
| `rwkv-lh.task-commit.v1`，含额外字段 | 6 | schema 被转换，但额外字段原样保留，canonical validator 仍拒绝 |
| canonical schema，含额外字段 | 31 | 不发生转换，canonical validator 仍拒绝 |
| 其他错误对象 | 5 | 不发生语义补全，继续拒绝 |

9 个仅受 schema 拼写影响的响应来自：

- B03：2
- B11：1
- B13：3
- B18：2
- B21：1

这些计数只说明该次响应可以越过 Task commit 的格式检查，不等于对应 case 最终会 Strict PASS；后续任务、恢复和 Goal 判断仍可能失败。

### Task replan

| Case | 原 schema | 顶层字段 | Task 字段 | 转换后的结果 |
|---|---|---|---|---|
| B22 | `rwkv-lh.task_batch.v1` | 完整 | 完整 | 只改 schema 后可进入现有 replan 校验 |
| B28 | `rwkv-lh.task-batch.v1` | 完整 | 缺 `local_id` | schema 被转换；缺字段不补，Task validator 仍拒绝 |

`1`、`1.0.0`、`task_batch.v1`、`rwkv-lh.task.v1`、缺 schema、`task`/`task_batch` wrapper 等均未登记，保持失败。

## 结论

纯格式转换有真实但有限的价值：冻结 trace 中 10 个响应（9 个 Task commit、1 个 B22 replan）在不改变任何语义字段的条件下可以通过其完整 canonical 校验；另有 7 个已登记 alias 响应仍因额外字段或缺字段失败。这个上限远不足以解释或修复 Round33 的 25 个 Strict 失败，验证了格式层不能承担流程整改或答案修正。
