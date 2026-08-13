# Round34 预注册协议：纯格式别名转换

## 触发证据

Round33 Basic30 的完整 model trace 中，Task postcondition commit 出现：

- canonical 三字段对象 `long-horizon.task-commit.v1`：98 次；
- exact 三字段别名对象 `rwkv-lh.task-commit.v1`：9 次；
- `rwkv-lh.task-commit.v1` 但带额外字段：6 次；
- canonical schema 但带额外字段：31 次。

Task replan 中还各出现一次顶层为 `schema_version + tasks` 的 `rwkv-lh.task-batch.v1` 和 `rwkv-lh.task_batch.v1`；其中 B22 的 Task 字段完整，B28 的 Task 缺 `local_id`。转换层对二者都只改 schema，B28 随后仍必须被 Task validator 拒绝。`1`、`1.0.0`、`rwkv-lh.task.v1`、缺 schema、缺字段、额外 wrapper 等不登记为兼容格式。

原始数据固定为 `Round33_basic30_goal_frontier/cases/*/model_trace.json`；运行后不得增删别名来改善结果。

## 单一变更

在模型边界增加一个纯 schema 表示转换函数，只登记：

- `rwkv-lh.task-commit.v1` → `long-horizon.task-commit.v1`
- `rwkv-lh.task-batch.v1` → `long-horizon.task-batch.v1`
- `rwkv-lh.task_batch.v1` → `long-horizon.task-batch.v1`

转换函数只替换 `schema_version` 的精确字符串。其余 key、value、数组顺序和嵌套对象保持不变。转换后仍由唯一 canonical validator 检查完整协议。

## 明确禁止

- 不删除额外字段；因此带 `task_commit_status`、`task`、`task_status` 的对象转换后仍应失败。
- 不补缺失 schema、`local_id`、Task 字段、decision、reason、工具参数或答案。
- 不展开未登记 wrapper，不把 `task`/`task_batch` 猜成 `tasks`。
- 不更改 action 名称、路径、数值、文本、criterion binding 或最终回答。
- 不读取外部验收结果决定是否转换。
- 不承担语义校验、正确性判断、反作弊或恢复决策。

## 固定验证

1. 单元测试：三个登记别名只改变 schema 字符串；input payload 不被原地修改，嵌套对象和值保持相等。
2. 单元测试：转换器可输出带额外字段的 canonical 对象，但唯一 validator 随后拒绝，证明转换和校验职责分离。
3. 单元测试：未知 schema 和缺失 schema 原样保留，随后 fail-closed。
4. 审计：每次真实转换保存 raw/normalized payload、两者 digest、转换名与 `controller_semantic_fields_generated=false`。
5. Round33 trace 离线 replay：固定统计“仅通过格式转换可进入 canonical validator 的 exact 对象”，不模拟后续模型采样，也不把它宣称为 Strict E2E 提升。
6. 全量 pytest、LH-Control 30/30、E2E-90 validate-only 90/90。
7. Round34 只验证格式边界，不修改 prompt、memory capsule、规划或恢复逻辑。

## 成功判据

- 登记别名的 exact 对象进入唯一内部格式。
- 所有字段不完整、字段过多、未知 schema 和语义错误仍被原有 validator 拒绝。
- raw/normalized 变换完整可审计。
- 无离线、边界、异常或历史恢复回归。

Round34 即使通过也只说明格式边界更完整；它不能单独证明 Agent 任务正确率提高，不能作为上传依据。
