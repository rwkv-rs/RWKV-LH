# Round96 E2E-B02 人工因果分析

## 结果

- Agent FAIL / External FAIL / Strict FAIL，FP/FN 均为 0。
- T2 已产生真实 Attempt；top-level task_id 归一化生效。
- Final 非空且等于 RWKV原始输出。

## 链路与根因

1. Goal创建读取 input.txt 和创建 report.json 两个 Task。
2. T1完成。
3. T2 的 split-task-id `read_file(input.txt)` 被无语义归一化并真实成功执行。
4. 当前 evidence contract 只要求 `file_content_read`，没有声明该读取必须针对 report.json，因此读取 input.txt 后 `completion_protocol_ready=true`。
5. RWKV没有错误完成 Task，但继续选择 `read_json(input.txt)`，真实失败后形成重复循环。

结构根因：证据类型与证据对象未绑定。Controller不能从自然语言 done_when推断 report.json；应由 RWKV在 Task proposal 中显式声明 evidence_subject，运行时只做精确对象匹配。
