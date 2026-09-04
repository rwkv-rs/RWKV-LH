# RWKV-LH

RWKV-LH 是以 RWKV 为核心的持久 Agent 运行时。当前唯一产品控制链是 `RWKV Stateful Goal Loop v3`：强 Planner 拆解目标，2.9B Selector 选择一个 operation，13.3B Executor 只填写参数，Harness 执行并记录事实，机械证据门和独立 Auditor 决定是否推进。

当前版本仍是实验候选，不能作为可靠 Agent 发布。确定性失控路径已经修复，但 Selector Head 的真实域外泛化、Executor 的完整事实输入遵循，以及 StateTune 训练/serving 字节一致性仍未通过门禁。

## 文档入口

- [交接、部署、缺陷与 StateTune 格式合同](docs/HANDOFF.zh-CN.md)
- [项目工作规范](AGENTS.md)

其他保留在 `data/datasets/` 和 `data/experiments/` 下的 Markdown 是数据来源说明、当前实验证据或脚本按路径/SHA依赖的机器合同，不是新的人工入口。历史文档保存在 Git 历史和归档分支。

## 本地运行

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

模型、Head、State、服务器、端口和启动方式不要从旧实验文档复制，以交接文档和 `.env.local` 的身份校验为准。
