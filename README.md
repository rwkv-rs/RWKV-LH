# RWKV-LH

当前状态（2026-09-09）：Planner / Stage Checker 已切到独立强模型配置，修复计划解析失败时原始 JSON 丢失、语义错误误报服务不可用及不同传输的完成判定差异。Agent 最新完整对比仍是历史 R7：A/B 各 Strict **0/12**、completed **0/12**、mutation **0**；当前链路 R3 由 owner 暂停，10 题有终止记录，动作与 mutation 均为 0，不能作为完整 12 题成绩。2.9B Selector 已部署并通过 Native 训练后端数值验证，正式 optimizer steps 仍为 0。证据与限制见 [当前交接](docs/HANDOFF.zh-CN.md) 和 [Planner 修复报告](data/experiments/PLANNER_STRONG_ROUTING_R1_20260909/REPORT.zh-CN.md)。

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

每个角色只保留一个协议模块，输入共用 `build_prompt_source()` 与该模块的 renderer。Selector 为 v5、Executor 为 v5、Step Auditor 为 v4、Finalizer 为 v2、Final Auditor 为 v3。所有旧模块、兼容角色输入、合成数据生成/评测链和旧数据已从工作树删除，不保留 stub 或本地归档。

StateTune 按 **Selector → Executor → Step Auditor → Finalizer → Final Auditor** 推进。当前角色的数据和预注册验证条件满足后训练，固定其 State，再收集下一角色的真实问题；后序角色未到达不阻止前序角色。Agent 低分是改进对象，正式保留组合仍须通过 Agent 验收。owner 已取消固定三轮上限，后续按指标、预算和实际训练 run 管理。

当前管线支持生产 trace 重建、冻结前序 State、语义复核与独立纠正目标、角色覆盖和固定回归审计；只输出候选文件。本轮未冻结正式角色数据或启动训练，当前优化器训练器仍需按实际 backend 接通和验证，见 [StateTune 现状](docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md)。模型升级复用同一架构，优先调整模型/词表/State/上下文/传输适配，不自动恢复旧协议或旧 State。

## 文档与记录

- [项目工作规范](AGENTS.md)
- [唯一协议、数据来源与验收规则](docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)
- [当前交接](docs/HANDOFF.zh-CN.md)
- [StateTune 数据生成管线源码、现状与经验](docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md)
- [生产 trace 数据管线使用说明](docs/ROLE_TRACE_DATASET.zh-CN.md)
- [本轮工程与 StateTune 入口整改](data/experiments/STATETUNE_ENTRY_REPAIR_R1_20260909/REPORT.zh-CN.md)
- [基线准备与可见题集审查](data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/READINESS_ANALYSIS.zh-CN.md)
- [服务器资源清理与当前部署记录](data/experiments/SERVER_RUNTIME_CLEANUP_R1_20260907/)
- [当前强模型 Planner 配置与解析修复](data/experiments/PLANNER_STRONG_ROUTING_R1_20260909/REPORT.zh-CN.md)
- [外部开源数据、RSI 与训练框架的适用范围](docs/OPEN_SOURCE_RESOURCE_ADOPTION.zh-CN.md)
- [新增 12 题开发基准与作者验证材料](data/datasets/rwkv_lh_real_project_dev_v1/)

`data/datasets/` 保留当前有效公共回归数据和隔离 Holdout；旧角色数据已删除。`data/experiments/` 只保留本轮及后续当前实验记录，历史查询 Git / GitHub。`data/acceptance/` 中的冻结 Holdout 材料只供最终一次验收。

## 运行与回归

项目逻辑只在 WSL `UbuntuRecovered` 中执行：

```bash
cd /home/chase/GitHub/RWKV-LH
uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q tests/
```

首次设置参考 `.env.example` 创建 `.env.local`；已有配置应保留。普通回归不执行 `acceptance_tests/`，不得把读取 Holdout 的验收测试加入默认套件。Torch / State 注入和必需的浏览器验证不能跳过。测试工件默认位于 `data/test_runs/pytest/`。CI 安装同样的两个 extra，并使用 `playwright install --with-deps chromium` 准备浏览器和系统依赖；同步完成后直接调用 `.venv/bin/`，避免默认依赖同步移除 extra。

Planner / Stage Checker 当前使用 owner 已配置的 `gpt-5.6-sol` 和 `openai-compatible` 传输，并在当前网关启用 `RWKV_LH_PLANNER_STREAM=true` 接收 SSE。所有默认入口统一读取 `.env.local`，进程环境显式设置优先；`.env.example` 不携带密钥，部署时填写实际服务地址。Planner 请求仍显式发送 `max_tokens=8192`，Stage Checker 为 `2400`，不是步骤数量限制；两个角色共用的读取超时为 240 秒。关闭计划缓存、留空 fallback，模型版本和响应方式通过配置替换。

模型返回必须自然 `stop`；流式输入还须完整结束，不能执行中间片段。完整 JSON 的合同错误保留原始对象及缺失/多余字段信息，交回同一 Planner 边界的一次纠错。截断输出不能当作完整计划；字段与根目录不由 Controller 补写。五个 RWKV 角色继续使用独立 State，13.3B 服务供既有 RWKV 角色使用。

服务器禁止使用 Git，所有 Git 版本管理和查询都在本地完成；源码仅通过 SSH 配合 rsync/SCP 从本地上传。部署时同时上传完整 engine 源码清单，包含相对路径与逐文件 SHA-256，并冻结 manifest 自身 SHA-256。服务须根据上传清单验证实际文件身份；启动、健康检查和 attestation 均不得执行 `git rev-parse`、`git status` 或其他 Git 命令。每次新部署与运行须绑定本轮核验记录，不能沿用旧冻结身份。

新开发套件的目录与验收合同可独立校验，该命令不调用模型：

```bash
.venv/bin/rwkv-lh-e2e --suite realprojectdevv1 --validate-only
```

配置模型服务并完成当前模型、State、协议与 decoder 身份校验后：

```bash
.venv/bin/rwkv-lh-stack status
.venv/bin/rwkv-lh-runtime-smoke
.venv/bin/rwkv-lh start --request "创建并验证 result.json" --workspace /tmp/rwkv-lh-workspace
.venv/bin/rwkv-lh status RUN_ID
.venv/bin/rwkv-lh resume RUN_ID
.venv/bin/rwkv-lh-web
```

训练和正式角色数据版本按 owner 已有书面授权范围执行；固定三轮上限已取消，改按预注册指标、预算和实际 run 记录管理。封存 Holdout 未参与本轮开发、作者验证或基线准备。
