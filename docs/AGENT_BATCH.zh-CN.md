# 独立任务批量入口

在WSL中运行：

```bash
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/run_rwkv_agent.py --jobs /absolute/path/jobs.json --concurrency 2
```

任务清单是JSON数组，每项含task_id、request、workspace、output_dir、tool_scope（files/inspect/coding），可指定max_calls、max_seconds。各output_dir必须尚不存在且互不重叠，不能与任一workspace重叠。

```json
[
  {"task_id":"read","request":"阅读说明文件并总结主要内容。","workspace":"/absolute/source","output_dir":"/absolute/runs/read","tool_scope":"files","max_calls":6,"max_seconds":300},
  {"task_id":"fix","request":"修复已描述的问题，运行测试并如实报告。","workspace":"/absolute/project","output_dir":"/absolute/runs/fix","tool_scope":"coding","max_calls":12,"max_seconds":600}
]
```

这是调用格式示例，不是训练/评测数据。任务必须已独立，不能把互相依赖的修改放入同批并认为调度器会集成。

stdout返回每项原始结果；可用shell重定向保存批次汇总。每项执行目录保留真实trace和State，coding目录还含workspace、DELIVERY.json及前后快照。异常启动不会令另一项被误记成功，失败结果包含异常类型和信息；进程池故障按future记录，已完成结果和已保存任务证据保留，无法确认的调用数记为null。

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

## RWKV优先的完整任务入口

coding任务可以显式设置`on_stall: "takeover"`及`rwkv_max_calls`。例如：

```json
[{"task_id":"fix","request":"修复查询问题，运行已有测试并如实报告。","workspace":"/absolute/project","output_dir":"/absolute/new-run","tool_scope":"coding","on_stall":"takeover","rwkv_max_calls":24,"max_calls":32,"max_seconds":1200}]
```

这是调用示例，不是新增评测数据。RWKV先运行；只有完整trace、无回答、生成/transition/重复成功预算停滞且仍有预算时，才最多接管一次。普通coding任务未设置on_stall时仍只使用RWKV。已有回答直接交外部验收，系统不把每个步骤交strong审核，也不自动判断回答语义是否合格；基础设施故障、墙钟耗尽和未知中断不触发接管。

max_calls是两种模型合计的生成上限；rwkv_max_calls是RWKV可用上限，现有重复保护可能让其提前结束。max_seconds按已用时间扣减后分给接管；复制/清理可能超时，DELIVERY中的workflow记录完整端到端elapsed及是否超出，不是主机进程硬截止保证。provider错误时未知调用数用null保留，不记零成本。

输出包含rwkv/原运行、可选takeover/续跑、POLICY.json、ROUTING.json和DELIVERY.json。最终文本/工作区引用来自实际执行者；workflow.id是外层任务ID，结果id保留实际子运行身份。输入的一句话目标保持不变，不给模型指定正确补丁或工具顺序。

## 显式依赖与保守集成（2026-09-14 工程整改）

仍使用 `scripts/run_rwkv_agent.py --jobs /absolute/jobs.json --concurrency 2`。
JSON任务可增加 `"depends_on": ["前置任务ID"]`。调用方声明依赖，程序不拆解用户目标。

- 无依赖任务照常并发；有依赖的任务当前只支持普通 coding 任务，不隐式开启strong。
- 单前置任务：核对交付清单，将真实工作区复制为后续任务输入；后续任务是明确声明的新任务，使用独立State。
- 多前置任务：要求相同初始文件清单，只合并不冲突的文件内容变化。修改/删除冲突、文件/目录冲突、基线不同或产物被改动均拒绝，记录blocked/error，不自动猜修法。
- 后续任务的用户要求可以是测试、检查或继续修改；仍由RWKV选择工具和参数。依赖提交只表示有材料可继续，不等于外部验收通过。
- 多父集成针对文件内容；空目录、纯权限变化和一般Git语义合并不属于当前支持范围。显式冲突解决、任意分叉基线重建仍是后续能力。
- 普通调度异常、进程池故障和依赖阻塞记录到任务输出目录的 `BATCH_ERROR.json`。未知调用数为null，不伪造零成本或RWKV独立完成。

编码、协助和整目标入口的准备阶段纳入同一协作式wall deadline，内层不得续出更长预算。取消协助worker会清理其进程组。清理/落盘可能超时，`end_to_end_seconds`和`wall_allowance_exceeded`如实记录；这不是操作系统硬资源配额。

`trace_complete`现在要求日志无写入错误且生成请求/返回配对；`trace_persistence_ok`仅说明日志写入，`unresolved_request_ids`列出未收到返回的请求。它仍不等于native张量正确或所有token可重放，后者由专用验证器检查。

工作区复制现在核对复制前源目录、复制后源目录和副本三份身份，保存`SOURCE_COPY.json`。身份包含文件SHA、路径类型、权限和目录；发现变化即停止，不启动模型。它是变化检测，不是对外部并发写入的文件系统原子快照保证。

coding/assisted保存`INITIAL_TREE.json`，交付包含`final_tree`；`changed_files`也包含权限和目录变化。旧`INITIAL_FILES.json`/`final_files`仍用于文件内容审计。依赖交付缺少树身份即拒绝，不补造历史证据。多父集成支持包含文件的目录移动，纯权限或空目录变化显式拒绝，不再静默丢弃。旧只读建议入口与协助入口共享父生成记录配对检查。

GPU限制应设置在实际推理服务进程上；CLI的环境变量仅约束本地进程及其子进程，不会改变已经启动的远端服务。
