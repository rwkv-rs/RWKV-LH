# RWKV-LH 本地手工测试界面

## 定位

`rwkv-lh-web` 是当前唯一 Controller 的本机界面，不是第二个 Agent。页面只提交用户任务、展示持久状态和管理隔离 worker；它不生成、筛选、修复或改写 RWKV 的决定和最终输出。

## 当前可以测试什么

- 用户请求逐字保存为 immutable request，不经模型解析或重写。
- RWKV 在唯一 Action session 中直接选择注册工具、接收真实 Observation，并用
  `final_answer` 决定何时回答；没有 Task DAG、selector 或 reviewer。
- 在每个运行独立的 workspace 中读取、创建、修改、复制和删除 UTF-8/JSON 文件，或执行 Harness 允许的 scoped command。
- 查看从 CausalEvent 权威链投影出的 Action、Artifact、ModelSession checkpoint、
  Controller event 和每个模型请求的采样参数。
- 查看发给 RWKV 的精确 G1i transcript、原始候选、commit/rollback 和 typed event。
- 停止 worker，从 SQLite 恢复 interrupted/stopped run，并导出包含 workspace、trace、event 和一致 SQLite snapshot 的 ZIP。

这不代表系统已经能稳定完成任意编程任务。能力结论以冻结 E2E 数据集的真实结果为准，手工成功不能代替正式分数。

## 当前不能做什么

- 不能稳定完成任意长程任务或大型代码项目。
- 不能操作当前 run workspace 之外的文件；seed/file API 与 Harness 都会拒绝绝对路径和 `..` 逃逸。
- 当前没有联网检索 Action，也没有 MCP 或外部服务插件。
- 不能用 Codex、Judge 或其他模型替 RWKV 选择工具、决定完成或修改答案。
- 模型输出不是一个 canonical G1i call、参数不满足注册表或 lane 命令无效时会 rollback 并 fail closed，不重新采样语义。
- 不提供多用户认证或安全公网托管；默认只允许 loopback。
- 推理服务未声明完整 recurrent-state create/resume/fork/commit/rollback/export/import 时，模型上下文使用可审计 prompt replay。

## 启动

先在 `.env.local` 配置 RWKV endpoint、模型和凭证，然后在 WSL 项目根目录运行：

```bash
uv run rwkv-lh-web
```

浏览器打开 `http://127.0.0.1:8765`。可用 `--port` 改端口、`--data-root` 改手工运行目录。服务拒绝非 loopback bind；`--allow-remote` 只解除绑定限制，不提供认证。

## 数据布局

```text
data/manual_runs/runs/<RUN_ID>/
├── metadata.json
├── request.json
├── model_trace.jsonl
├── result.json
├── worker.log
├── workspace/
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

任务：

```text
读取 input.txt，在工作区创建 summary.json，包含非空行数量和按原顺序排列的 lines 数组，然后验证写入结果。
```

失败时按时间顺序查看 Action checkpoint → committed direct call → `action_started` → Harness
结果 → `action_finished` → 同一 session 的下一命令，定位最早错误环节，不只看最终状态。
