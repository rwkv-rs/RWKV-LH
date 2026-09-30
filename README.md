# RWKV-LH

为状态驱动的 RWKV 续写模型构建专属 Harness 与 Code Agent。项目保存计划与事实，决策 RWKV 选择方向，执行 RWKV 完成局部委派；强模型负责按需规划、检查编写、独立审查与诊断。Harness 执行真实工具并记录证据。

在相同交付质量下降低总成本、缩短交付时间、提高吞吐是产品的优化目标，当前不预设这些收益已经成立。

当前编码项目执行闭环：

```text
完整用户目标 → 决策 RWKV → 按需规划或局部执行 RWKV ⇄ 真实工具回执
                  ↑                       ↓
               项目账本 ← 局部报告与独立检查 → 目标满足判断 → 完成门 → 外部验收
```

决策与执行使用隔离 State，执行器在一个委派内续写；工作单元让出后可沿原 State 继续，独立方向判断从各自边界输入开始。新角色默认 zero，不自动复用旧直接执行 State。工具调用与参数仍由执行 RWKV 决定，决策依据只用于审计。检查成功与目标满足判断分开，计划内完成仍不等于外部验收通过；预算耗尽如实中断，不补写答案。完整推进步骤与限制见[当前架构](docs/ARCHITECTURE.zh-CN.md)。`files/inspect` 仍是独立的只读工具任务。

## 当前架构与统一入口

[当前架构和职责](docs/ARCHITECTURE.zh-CN.md) · [独立任务批量运行](docs/AGENT_BATCH.zh-CN.md)。统一入口 `rwkv-lh` 执行 `scripts/run_rwkv_agent.py`：单题用 `--source-workspace`，批量用 `--jobs`。离线数据管线入口为 `rwkv-lh-data`；不自动合并并行修改。

配置并核验 RWKV 和强模型规划服务后，给出源工作区和一句任务：

```bash
.venv/bin/rwkv-lh \
  --source-workspace /absolute/path/to/project \
  --output-dir /absolute/path/to/new-run \
  --request "检查项目中的问题，修复后运行相关测试并说明结果" \
  --max-calls 64 --max-seconds 600
```

输出目录必须尚不存在，且不能与源工作区重叠。Agent 在输出目录的 `workspace/` 副本中工作；原项目不会被覆盖。正常结束后检查 `DELIVERY.json`、修改产物和 `execution/` 中的真实调用记录。异常或预算中断应检查已写入的执行记录，不能假定一定存在完整交付文件。退出码 0 表示模型提交回答，**不表示产物已经通过外部验收**。工作区副本用于隔离文件变更，命令仍使用现有工具权限，不能将其视为任意命令的安全沙箱。

强模型不逐次审核工具调用。当前闭环已完成工程机制验证，真实模型的重复调用、错误诊断、遗漏修改和无依据回答尚未证明解决。StateTune 候选只有经过固定回归和任务级对照验证后才可作为推荐配置。项目可用 `rwkv-lh --resume /absolute/path/to/new-run` 沿原预算恢复；未确认操作不能自动重放。

## 前端演示

在 WSL 中启动一次：

```bash
cd /home/chase/GitHub/RWKV-LH
.venv/bin/python scripts/run_web_ui.py --port 8766 --data-root data/frontend_runs
```

浏览器打开 **http://localhost:8766**。点击“阅读健康检查脚本”或“运行递归扫描测试”，检查自动填入的任务和原始文件，再点击“开始执行”。之后在任务记录里查看原始回答、真实工具结果与完整审计，并可下载审计包。

演示按钮会调用真实 RWKV，页面展示实际返回和审计。是否完成任务须查看独立验收，能打开演示界面不证明项目交付稳定。

当前支持指定文件问答、只读搜索/测试，以及修改隔离副本（实验性）。编码任务使用当前按需规划、决策与执行闭环，可查看计划、验证记录并续跑；历史编码记录不能用新协议恢复。模型仍可能重复读取、错误诊断或无回答终止。

## 文档与记录

- [项目工作规范](AGENTS.md)
- [当前架构与唯一角色输入](docs/ARCHITECTURE.zh-CN.md)
- [当前交接及未解决问题](docs/HANDOFF.zh-CN.md)
- [Project 数据入口与训练准入](docs/PROJECT_ROLE_DATA_PIPELINE.zh-CN.md)
- [可复用的经验](docs/LESSONS.zh-CN.md)
- [源码发布范围与本地验证](docs/SOURCE_DISTRIBUTION.zh-CN.md)

维护文档只保留当前状态，历史说明从 Git 查询。GitHub 只发布架构文档、项目源码和必要构建配置。测试、基准、实验、训练数据、State、日志和生成产物保留本地；新 clone 不包含这些材料。本地完整回归需要 owner 单独交接测试与必要夹具，冻结 Holdout 仍只供最终一次验收。历史提交未改写。

## 运行与回归

项目逻辑只在 WSL `UbuntuRecovered` 中执行。下面的完整回归命令用于已接收本地测试材料的维护环境：

```bash
cd /home/chase/GitHub/RWKV-LH
uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q tests/
```

首次设置参考 `.env.example` 创建 `.env.local`；已有配置应保留。普通回归不执行 `acceptance_tests/`，不得把读取 Holdout 的验收测试加入默认套件。Torch / State 注入和必需的浏览器验证不能跳过。测试工件默认位于 `data/test_runs/pytest/`。公开 CI 仅安装基本运行依赖、检查源码范围、编译、验证命令入口和构建；不运行本地测试、不调用模型、不上传实验产物。CI 通过不代表完整回归或 Agent 能力通过。

当前执行入口读取 `.env.local`，进程环境显式设置优先；配置文件不应提交密钥。项目角色配置使用 `RWKV_LH_PROJECT_EXECUTOR_*` 和 `RWKV_LH_PROJECT_DECISION_*`，未配置各自 State 时从 zero 开始。强模型沿用 Supervisor 配置，负责决策请求的规划、诊断、检查编写和独立审查；当前项目闭环尚未接入强模型直接接管。配置与限制见架构和批量运行文档。

服务器禁止使用 Git，所有 Git 版本管理和查询都在本地完成；源码仅通过 SSH 配合 rsync/SCP 从本地上传。部署时同时上传完整 engine 源码清单，包含相对路径与逐文件 SHA-256，并冻结 manifest 自身 SHA-256。服务须根据上传清单验证实际文件身份；启动、健康检查和 attestation 均不得执行 `git rev-parse`、`git status` 或其他 Git 命令。每次新部署与运行须绑定本轮核验记录，不能沿用旧冻结身份。

本地另行接收评测脚本及开发套件后，可校验目录与验收合同，该命令不调用模型：

```bash
.venv/bin/python -m scripts.run_rwkv_e2e_benchmark --suite realprojectdevv1 --validate-only
```

配置模型服务并完成当前模型、State、协议与 decoder 身份校验后：

```bash
.venv/bin/rwkv-lh-stack status
.venv/bin/rwkv-lh-runtime-smoke
.venv/bin/rwkv-lh --help
```

训练和正式角色数据版本按 owner 已有书面授权范围执行；按预注册指标、预算和实际 run 记录管理，不设固定轮次上限。封存 Holdout 不参与开发迭代。
