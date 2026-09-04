# RWKV-LH

RWKV-LH 是以 RWKV recurrent State 为核心的持久 Agent 运行时。当前产品结构只有一条控制链：`rwkv-stateful-goal-loop.v3`。

```text
Strong Planner
  -> 2.9B Selector
  -> 13.3B Executor
  -> Harness
  -> Mechanical Evidence Gate
  -> Step Auditor
  -> Strong Stage Checker
  -> Finalizer
  -> Final Auditor
```

这些名称表示同一条链中的职责边界，不是多套架构。全局权威状态始终是 append-only causal ledger；各模型角色使用独立 WKV，避免角色间状态污染。

当前尚不能发布为可靠 Agent：13.3B 推理服务和 native recurrent State 健康，但 Selector 服务身份未与本地配置对齐，Selector Head 的真实 frontier 泛化、Executor 的显式状态遵循、以及训练输入与线上完整输入的一致性仍需通过固定门禁。

## 文档

- [当前结构、部署、输入输出和训练合同](docs/HANDOFF.zh-CN.md)
- [项目工作规范](AGENTS.md)

`data/datasets/` 只保存已纳入 Git 的数据说明与合同，`data/experiments/` 只保存已纳入 Git 的可复核证据。当前工作树不保留未跟踪实验产物。

## 运行

项目逻辑只在 WSL `UbuntuRecovered` 中执行：

```bash
cd /home/chase/GitHub/RWKV-LH
uv sync --frozen --dev
cp .env.example .env.local
uv run rwkv-lh-stack status
uv run rwkv-lh-runtime-smoke
```

创建、查询和恢复任务：

```bash
uv run rwkv-lh start --request "创建并验证 result.json" --workspace /tmp/rwkv-lh-workspace
uv run rwkv-lh status RUN_ID
uv run rwkv-lh resume RUN_ID
```

本地界面：

```bash
uv run rwkv-lh-web
```

完整验证：

```bash
uv run pytest -q
uv run rwkv-lh-runtime-smoke
uv run rwkv-lh-e2e --suite all --validate-only
```

模型、Head、State、协议和工具表必须作为同一个发布身份校验；具体字段以交接文档和当前代码为准。
