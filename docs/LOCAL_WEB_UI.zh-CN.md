# RWKV-LH 本地手工测试界面

## 定位

`rwkv-lh-web` 是当前唯一 Product Controller 的本机界面，不是第二个 Agent。页面只提交用户任务、展示持久状态和管理隔离 worker；它不生成、筛选、修复或改写 RWKV 的决定和最终输出。当前链路是 Strong Planner → 2.9B G1J Selector-Intent → 13.3B G1J Executor-Args → Harness → clean-State Step Auditor → Strong Stage Checker → Finalizer/Final Auditor；0.4B Shadow 和旧 Contract Graph 已退出产品入口。

## 当前可以测试什么

- 用户请求逐字保存为 immutable request，不经模型解析或重写。
- Strong Planner 只产生 rolling `GoalPlanPatch`，Strong Stage Checker 只读检查完成阶段；2.9B Selector 暂存一个非权威 operation；13.3B Executor 每个 action 从干净 State 启动，复核绑定后只生成参数。Final 由独立 Finalizer 产生并由 Final Auditor 审核。
- 在每个运行独立的 workspace 中读取、创建、修改、复制和删除 UTF-8/JSON 文件，或执行 Harness 允许的 scoped command。
- 查看从 CausalEvent 权威链投影出的 Action、Artifact，以及非权威 WKV checkpoint、
  Controller event 和每个模型请求的采样参数。
- 查看发给 RWKV 的精确角色 prompt、原始候选、commit/rollback 和 typed event。
- 可以停止计算进程并从 SQLite 恢复；这不把 Goal 标记为完成。普通 slice 保持 running；连续 action 协议拒绝达到硬预算后显示 blocked 并停止自动调用，修改模型/Head/配置后可人工恢复。导出包包含 workspace、trace、event 和一致 SQLite snapshot。
- 可按运行选择 `offline/auto_public/explicit_egress`；页面默认 `auto_public + stateful_goal`，
  联网结果冻结为可回定位 exact evidence。CLI/API 未显式选择时仍安全地默认 offline。

这不代表系统已经能稳定完成任意编程任务。能力结论以冻结 E2E 数据集的真实结果为准，手工成功不能代替正式分数。

当前能力事实以 2026-09-03 Ladder 为准：有效 20 个 case 为 `0/20`，Selector 1124 次只选择了 `list_directory` 和 `move_file`。旧 Head 已因训练/运行轨迹不一致被 runtime 拒绝；新 Head 完成前，页面连通不等于能力通过。

## 当前不能做什么

- 不能稳定完成任意长程任务或大型代码项目。
- 不能操作当前 run workspace 之外的文件；seed/file API 与 Harness 都会拒绝绝对路径和 `..` 逃逸。
- 没有浏览器自动化、MCP 写操作或任意私有服务访问；敏感出站值和来源扫描不完整的值由 Gate 拒绝。
- 不能用 Codex、Judge 或其他模型替 RWKV 选择工具、决定完成或修改答案。
- 模型输出不是一个 canonical call、参数不满足注册表或 lane 命令无效时会 rollback；同一 selection 只允许一次显式参数修复，不无限重采样。
- 不提供多用户认证或安全公网托管；默认只允许 loopback。
- 推理服务未声明完整 `rwkv-lh.native-state.v1` 时，Goal fail closed 并显示等待运行时恢复；不会回退 prompt replay。服务在线状态和端口必须在每次实验启动时重新验证。

## 启动

先在 `.env.local` 配置固定模型/profile 身份和凭证，然后在 WSL 项目根目录启动完整栈：

```bash
uv run rwkv-lh-stack up --web --worker
uv run rwkv-lh-stack status
```

浏览器打开 `http://127.0.0.1:8766`。正式静态资源为 `rwkv_lh/goal_web_assets`，数据目录为
`data/goal_ui_preview`。可用 `--port` 改端口、`--data-root` 改手工运行目录。服务拒绝非
loopback bind；`--allow-remote` 只解除绑定限制，不提供认证。

## 数据布局

```text
data/manual_runs/runs/<RUN_ID>/
├── metadata.json
├── request.json
├── model_trace.jsonl
├── result.json
├── worker.log
├── workspace/
├── retrieval_snapshots/
└── state/
    └── long_horizon.db
```

`request.json` 记录输入来源、数据版本和 seed file SHA-256。导出包包含完整状态 JSON、事件 JSON 和一致 SQLite snapshot。

## 不干预与单一协议

Trace 保存 input checkpoint、精确 transcript digest、raw candidate、commit/rollback 和 sampling。
Worker 直接写入 `ControllerResult.final_output`，并检查它是否与 RWKV 的
`final_answer.text` 逐字相等。

Parser 只读取本次候选字节并要求唯一调用。简单格式层可无损归一化常见 call envelope 与
Markdown JSON fence，但不补 operation 或参数，也不生成第二答案。

## 建议的第一次测试

初始文件：

```text
路径：input.txt
内容：alpha\nbeta\ngamma
```

任务（保留页面默认的 Stateful Goal；本例可把联网策略改为 offline）：

```text
读取 input.txt，在工作区创建 summary.json，包含非空行数量和按原顺序排列的 lines 数组，然后验证写入结果。
```

失败时按时间顺序查看 Action checkpoint → committed direct call → `action_started` → Harness
结果 → `action_finished` → clean Executor 的下一选择/参数调用，定位最早错误环节，不只看最终状态。
