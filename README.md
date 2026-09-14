# RWKV-LH

为 RWKV 构建专属 Harness 与 Code Agent。RWKV 是默认执行主体，自主选择工具、参数和下一步；Harness 执行真实工具、传递观察、延续 State、隔离任务并记录证据。强模型按需补足困难任务，成果归属单独记录。

在相同交付质量下降低总成本、缩短交付时间、提高吞吐是产品的优化目标，当前不预设这些收益已经成立。

当前前端接入已经用于读取、检查与修改诊断的共享执行闭环：

```text
用户任务与文件 → RWKV → 工具调用 → Harness → 真实观察与连续 State → RWKV → 原始回答
```

独立任务从 zero State 开始；工具由用户选定的权限范围限制，具体调用与参数仍由 RWKV 决定。模型提交回答不等于外部验收通过；预算耗尽如实中断，不补写答案。

## 前端演示

在 WSL 中启动一次：

```bash
cd /home/chase/GitHub/RWKV-LH
.venv/bin/python scripts/run_web_ui.py --port 8766 --data-root data/frontend_runs
```

浏览器打开 **http://localhost:8766**。点击“阅读健康检查脚本”或“运行递归扫描测试”，检查自动填入的任务和原始文件，再点击“开始执行”。之后在任务记录里查看原始回答、真实工具结果与完整审计，并可下载审计包。

演示按钮会重新调用真实 RWKV，不播放预制答案。指定测试曾连续两次执行并准确报告通过；这不证明通用 bug 诊断或项目交付稳定。本轮真实前端验证结果及调用说明见 [前端指南](docs/FRONTEND_DEMO.zh-CN.md)。

当前支持指定文件问答、只读搜索/测试，以及修改隔离副本（实验性）。新任务不经过旧 Planner/Selector/Auditor 多角色入口；前端尚未接入强模型协助及 State 续跑，旧记录保留供查阅。模型仍可能重复读取、错误诊断或无回答终止。

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
