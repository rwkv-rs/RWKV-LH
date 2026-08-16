# Round95 E2E-B02 人工因果分析

## 结果

- Agent FAIL / External FAIL / Strict FAIL。
- FP 已从 Round93/94 的 1 降为 0。
- Final 非空且等于 RWKV原始回答。

## 链路

1. 初始 Goal lane 一次创建两个因果 Task：读取 input.txt；创建并观察 report.json。完整剩余工作提示已生效。
2. T1 成功读取并由 RWKV显式完成。
3. T2 第一次调用为：`function=lh_task_call`，`params` 中显式给出 `operation=read_file` 和完整 `operation_args`，`task_id=T2` 放在顶层。
4. 旧转换层只接受 task_id 位于 params 或完全 flattened operation_arguments；它把这个顶层字符串当成非法 annotation，报 `call-envelope annotations outside the argument object must be objects`。
5. RWKV此后重复同一完整显式调用，累计 13 次 protocol rejection 后 blocked；没有任何 T2 Attempt被执行。

## 根因与边界

- 根因是简单等价外壳接入缺口，不是 operation 选择缺失。
- `task_id`、`operation`、`operation_args` 全部来自同一 RWKV payload，可以做无语义搬运。
- 若 params 与顶层 task_id 冲突必须拒绝；若缺 operation 或 args 仍必须拒绝。
