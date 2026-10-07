# 项目与独立只读任务入口

在 WSL 中运行 `rwkv-lh --jobs /absolute/jobs.json --concurrency 2`。JSON 数组每项包含 `task_id`、`request`、`workspace`、`output_dir`、`tool_scope`、`max_calls`、`max_seconds`。各输出目录必须尚不存在、互不重叠，不能与任一输入工作区重叠。

```json
[
  {"task_id":"read","request":"阅读说明文件并总结主要内容。","workspace":"/absolute/source","output_dir":"/absolute/runs/read","tool_scope":"files","max_calls":6,"max_seconds":300},
  {"task_id":"fix","request":"修复已描述的问题，运行测试并如实报告。","workspace":"/absolute/project","output_dir":"/absolute/runs/fix","tool_scope":"coding","max_calls":64,"max_seconds":600}
]
```

这是调用格式示例，不是训练或评测数据。`files/inspect` 是独立只读工具任务；`coding` 使用当前的按需强模型规划、决策 RWKV 调度、局部执行 RWKV 与公开检查闭环，详见 [架构](ARCHITECTURE.zh-CN.md)。编码任务可按需调用配置好的强模型，并计入总调用和耗时；没有旧直接执行回退。

批次中的项目彼此独立，可以共享只读源目录，但各自在自己的副本内工作。并发参数控制项目进程数，每个项目内部当前只有一个写入执行器。项目内部任务依赖由 Planner 生成并由项目账本保存；主入口拒绝旧 `depends_on`、`on_stall` 和 `assistance` 任务模式。

单项目和恢复：

```bash
rwkv-lh --source-workspace /absolute/project --request '完成用户要求' \
  --output-dir /absolute/runs/project --max-calls 64 --max-seconds 600
rwkv-lh --resume /absolute/runs/project
```

恢复使用原目标、工作区、调用次数和总时间预算。未确认的操作必须核实，不能自动重放。恢复期间更换角色的模型/State/协议身份会被拒绝。

编码输出包括 `workspace/`、`INITIAL_TREE.json`、`SOURCE_COPY.json`、`DELIVERY.json` 和 `execution/`。执行记录包括 SQLite 账本、模型 trace、强模型原始提供方记录、工具原始回执和隔离检查副本。Web 导出会对 SQLite 做一致快照。

退出 0 表示提交；编码任务还通过了当前计划内检查，仍不代表外部 Strict 合格。`DELIVERY.json` 中的 `acceptance` 明确区分该边界。`model_calls` 记录账本预留，`generation_started` / `generation_returned` 记录已观察的开始／返回事件；未知计数保留 null。预留不等于实际生成，更不等于提供方计费次数，原始 usage 以强模型 trace 为准。Project 的 `trace_complete` 要求事件身份与顺序配对、预留与实际开始一致、返回与发布证据对应且没有 pending；不证明 State 数值、训练资格或外部验收通过。

队列等待和整个批次的总用时单列；项目准备、模型执行、工具与验证均有协作式墙钟约束。清理/持久化可能略超时，不能把 Python 信号上限当成系统硬配额。源目录复制前后身份检测也不等于对外部并发写入提供文件系统原子快照。
