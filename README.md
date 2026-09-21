# RWKV-LH

为 RWKV 构建专属 Harness 与 Code Agent。RWKV 是默认执行主体，自主选择工具、参数和下一步；Harness 执行真实工具、传递观察、延续 State、隔离任务并记录证据。强模型按需补足困难任务，成果归属单独记录。

在相同交付质量下降低总成本、缩短交付时间、提高吞吐是产品的优化目标，当前不预设这些收益已经成立。

当前读取、检查与修改共用生产执行闭环：

```text
用户任务与文件 → RWKV → 工具调用 → Harness → 真实观察与连续 State → RWKV → 原始回答
```

独立任务从 zero State 开始；工具由用户选定的权限范围限制，具体调用与参数仍由 RWKV 决定。模型提交回答不等于外部验收通过；预算耗尽如实中断，不补写答案。

## 当前架构与统一入口

[当前架构和职责](docs/ARCHITECTURE.zh-CN.md) · [独立任务批量运行](docs/AGENT_BATCH.zh-CN.md)。统一入口 `rwkv-lh` 执行 `scripts/run_rwkv_agent.py`：单题用 `--source-workspace`，批量用 `--jobs`。离线数据管线入口为 `rwkv-lh-data`；不自动合并并行修改。

配置并核验 RWKV 服务后，给出源工作区和一句任务：

```bash
.venv/bin/rwkv-lh \
  --source-workspace /absolute/path/to/project \
  --output-dir /absolute/path/to/new-run \
  --request "检查项目中的问题，修复后运行相关测试并说明结果" \
  --max-calls 12 --max-seconds 600
```

输出目录必须尚不存在，且不能与源工作区重叠。Agent 在输出目录的 `workspace/` 副本中工作；原项目不会被覆盖。正常结束后检查 `DELIVERY.json`、修改产物和 `execution/` 中的真实调用记录。异常或预算中断应检查已写入的执行记录，不能假定一定存在完整交付文件。退出码 0 表示模型提交回答，**不表示产物已经通过外部验收**。工作区副本用于隔离文件变更，命令仍使用现有工具权限，不能将其视为任意命令的安全沙箱。

默认执行主体是 RWKV，简单任务不经过强模型逐步审核。当前能力仍需按实际任务验证：重复调用、错误诊断、遗漏修改和无依据回答尚未证明全部解决。StateTune 候选只有经过固定回归和任务级对照验证后才可作为推荐配置。

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

当前执行入口读取 `.env.local`，进程环境显式设置优先；配置文件不应提交密钥。单任务由 RWKV 沿工具观察延续 State，独立任务隔离 State。模型和已验证 State 由运行配置决定；没有配置 State 时从 zero 开始。批量运行中的强模型建议或接管须显式启用，并分别记录成果归属，配置方式见批量运行文档。

服务器禁止使用 Git，所有 Git 版本管理和查询都在本地完成；源码仅通过 SSH 配合 rsync/SCP 从本地上传。部署时同时上传完整 engine 源码清单，包含相对路径与逐文件 SHA-256，并冻结 manifest 自身 SHA-256。服务须根据上传清单验证实际文件身份；启动、健康检查和 attestation 均不得执行 `git rev-parse`、`git status` 或其他 Git 命令。每次新部署与运行须绑定本轮核验记录，不能沿用旧冻结身份。

新开发套件的目录与验收合同可独立校验，该命令不调用模型：

```bash
.venv/bin/rwkv-lh-e2e --suite realprojectdevv1 --validate-only
```

配置模型服务并完成当前模型、State、协议与 decoder 身份校验后：

```bash
.venv/bin/rwkv-lh-stack status
.venv/bin/rwkv-lh-runtime-smoke
.venv/bin/rwkv-lh --help
```

训练和正式角色数据版本按 owner 已有书面授权范围执行；固定三轮上限已取消，改按预注册指标、预算和实际 run 记录管理。封存 Holdout 未参与本轮开发、作者验证或基线准备。
