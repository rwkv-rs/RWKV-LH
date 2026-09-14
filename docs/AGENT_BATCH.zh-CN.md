# 独立任务批量入口

在WSL中运行：

```bash
.venv/bin/python scripts/run_rwkv_agent.py --jobs /absolute/path/jobs.json --concurrency 2
```

任务清单是JSON数组，每项含task_id、request、workspace、output_dir、tool_scope（files/inspect/coding），可指定max_calls、max_seconds。各output_dir必须尚不存在且互不重叠，不能与任一workspace重叠。

```json
[
  {"task_id":"read","request":"阅读说明文件并总结主要内容。","workspace":"/absolute/source","output_dir":"/absolute/runs/read","tool_scope":"files","max_calls":6,"max_seconds":300},
  {"task_id":"fix","request":"修复已描述的问题，运行测试并如实报告。","workspace":"/absolute/project","output_dir":"/absolute/runs/fix","tool_scope":"coding","max_calls":12,"max_seconds":600}
]
```

这是调用格式示例，不是训练/评测数据。任务必须已独立，不能把互相依赖的修改放入同批并认为调度器会集成。

stdout返回每项原始结果；可用shell重定向保存批次汇总。每项执行目录保留真实trace和State，coding目录还含workspace、DELIVERY.json及前后快照。异常启动不会令另一项被误记成功，失败结果包含异常类型和信息；进程池整体崩溃仍会作为批次异常抛出，已保存任务证据保留。

退出0只代表所有任务提交了回答，acceptance仍需外部检查；不要把submitted当验收通过。每任务预算从其执行入口计时，排队、复制和批次总时间需另算。并发数是进程上限，不是服务吞吐承诺。模型、tokenizer、State形状与传输沿当前配置，当前CLI从zero/native_required启动。

强模型协助已支持显式任务类型；普通任务不会自动调用强模型。当前架构与待办见[架构](ARCHITECTURE.zh-CN.md)。

## 显式建议或接管

```json
[
  {"task_id":"assisted","parent_run":"/absolute/previous/execution","output_dir":"/absolute/runs/assisted","assistance":"advice","max_calls":6,"max_seconds":600,"advice_max_tokens":1800}
]
```

只读父运行的`parent_run`直接指向包含`RESULT.json`、`state_snapshot.json`和`state/`的目录；coding/assisted父运行指向其`execution/`。`assistance`可改成`takeover`，由强模型直接执行。目标、工作区、权限继承父任务，不再填写request/workspace/tool_scope。配置使用现有RWKV与Supervisor环境变量；建议模式要求原native State仍可访问且兼容，接管使用独立文本State。

每项使用独立WSL mount namespace和复制工作区；父记录及源目录保留。结果在`DELIVERY.json`，原始轨迹在`execution/`，建议提供方记录在`ADVICE_PROVIDER_TRACE.jsonl`，接管记录在`execution/strong_trace.jsonl`。缺少依赖、提供方错误和不完整父记录会失败，不自动降级为普通任务。
