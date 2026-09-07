# RWKV-LH

RWKV-LH 是使用 RWKV 分角色推理与持久化因果记录的 Agent 运行时。产品入口只有 `rwkv-stateful-goal-loop.v7` 一条控制链。

```text
Strong Planner
  -> Controller：操作范围、目标类型与机械事实
  -> Selector 2.9B
  -> Executor 13.3B
  -> Harness
  -> Mechanical Evidence Gate
  -> Step Auditor 13.3B
  -> Strong Stage Checker
  -> Finalizer 13.3B
  -> Final Auditor 13.3B
```

全局权威状态是 append-only causal ledger。各角色使用独立 ModelSession；Selector 三种菜单顺序分别从 fresh initial State 求值，Executor 新动作重新初始化，Auditor / Finalizer 按边界初始化。跨动作事实由 ledger 有界投影回输入，WKV 是角色局部的派生缓存。

每个角色只保留一个协议模块，输入共用 `build_prompt_source()` 与该模块的 renderer。Selector 为 v4、Executor 为 v4、Step Auditor 为 v3、Finalizer 为 v1、Final Auditor 为 v2。所有旧模块、兼容角色输入、合成数据生成/评测链和旧数据已从工作树删除，不保留 stub 或本地归档。

当前仍不能作为可靠 Agent 发布：统一协议下的两遍 all-zero Ladder-10 基线、现有 State 消融与 Agent 验收尚待执行。新的生产 trace 数据流水线尚未实现；协议清理和单元回归不代表 Agent 指标改善。

## 文档与记录

- [项目工作规范](AGENTS.md)
- [唯一协议、数据来源与验收规则](docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)
- [当前交接](docs/HANDOFF.zh-CN.md)
- [本轮清理与验证记录](data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROUND_ANALYSIS.zh-CN.md)

`data/datasets/` 保留当前有效公共回归数据和隔离 Holdout；旧角色数据已删除。`data/experiments/` 只保留本轮及后续当前实验记录，历史查询 Git / GitHub。`data/acceptance/` 中的冻结 Holdout 材料只供最终一次验收。

## 运行与回归

项目逻辑只在 WSL `UbuntuRecovered` 中执行：

```bash
cd /home/chase/GitHub/RWKV-LH
uv sync --frozen --extra selector-runtime --group dev
cp .env.example .env.local
.venv/bin/python -m pytest -q tests/
```

普通回归不执行 `acceptance_tests/`，不得把读取 Holdout 的验收测试加入默认套件。Torch / State 注入测试不能跳过。测试工件默认位于 `data/test_runs/pytest/`。

配置模型服务并完成当前模型、State、协议与 decoder 身份校验后：

```bash
.venv/bin/rwkv-lh-stack status
.venv/bin/rwkv-lh-runtime-smoke
.venv/bin/rwkv-lh start --request "创建并验证 result.json" --workspace /tmp/rwkv-lh-workspace
.venv/bin/rwkv-lh status RUN_ID
.venv/bin/rwkv-lh resume RUN_ID
.venv/bin/rwkv-lh-web
```

训练和新建角色数据集版本目录都需要 owner 书面确认。远端部署、基线和 Holdout 没有在本轮清理中执行。
