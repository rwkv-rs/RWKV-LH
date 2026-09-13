# 编程任务入口

入口 `scripts/run_rwkv_coding_agent.py` 接收一个目标和已有工作区，复制到输出目录的 `workspace/`，由 RWKV 自主读取、修改、运行真实命令并提交原始回答。复用生产 Controller、工具、协议与输入构造函数，连续调用保持同一任务的 State。不会自动把改动合入源目录。

```bash
.venv/bin/python scripts/run_rwkv_coding_agent.py \
  --source-workspace /absolute/path/to/project \
  --output-dir /absolute/path/to/new-run \
  --request '修复指定缺陷，运行相关测试，如实说明改动和结果。' \
  --base-url http://127.0.0.1:29613/v1 \
  --model rwkv7-g1j-13.3b-zero-state-capability-ctx16384 \
  --model-sha256 559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65
```

默认使用独立 zero State、native-required 传输，最多 12 次生成、600 秒执行预算。复制源目录在执行计时前完成，工具快照在执行计时内；这不是包含准备过程的总资源上限。服务必须支持所登记的模型和 State 能力。

交付在 `DELIVERY.json`，包括模型原始回答、终止原因、改变的文件与最终文件 SHA。`execution/` 保留真实生成 trace、State 快照、工具观察与每次执行前后文件快照。完整逻辑输入 token 不等于 native State 模式下实际增量 prefill 或计费 token。

`submitted` 和进程退出 0 仅表示提交了回答；`acceptance` 默认 `not_evaluated`。预算、异常和无回答单列。调用命令时 `success=true` 也可能只是退出码符合模型指定的预期，测试是否通过应看真实退出码及测试输出。用户或外部验收必须检查交付物，不根据工具路径或答案措辞判定成败。

当前适用于小型普通文件工作区：源目录符号链接及特殊文件拒绝；复制时排除 `.git`，包括 worktree 指针。输出目录必须不存在且不能与源目录重叠。工作区复制是交付物隔离，不是独立虚拟机，命令仍受现有生产工具权限与环境约束。完整快照的磁盘成本会随文件规模与调用次数增长，尚不适合未经评估的大仓库或含依赖缓存的目录。

本入口没有新增强模型逐步审核、业务补参或答案改写。现有 Controller 的重复操作与结束规则仍生效，实际轨迹中若触发强制结束需单列，不能算自然完成。独立只读并发继续使用 [只读入口](READ_ONLY_AGENT.zh-CN.md)；共享文件并行修改与最终集成尚未验证。

新结果字段 `termination_reason` 与 `termination_evidence` 给出精确终止边界，避免粗分类 budget 混淆调用上限、Controller transition 上限与重复失败边界。`command_executions` 保留实际退出码和 `exited` / `not_started` / `unconfirmed`；这些字段不判断业务测试通过。续接诊断的完整命令台账包含父历史，新增次数应按 continuation.historical_actions 切分。

同父 State 的可写续修目前通过实验编排验证私有挂载隔离；公共 CLI 仍是新任务入口。现有固定同类失败计数会跨续接保留，因此旧错误可能让续修提前停止。见 [续修诊断](../data/experiments/RWKV_CODING_RECOVERY_R1_20260913/REPORT.zh-CN.md)，不能据此承诺通用断点续修已经可用。
