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

服务器 `rwkv-8222` 已按本地上传方式部署。R2 A 已运行 12 题：Strict **0/12**、completed **0/12**、mutation **0**，12 题均因 `strong_planner_unavailable` 停止，11 题没有 RWKV 生成；B 臂未启动，不能计算双零噪声或进入训练，详见 [A 臂报告](data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/R2_A_RUN_REPORT.zh-CN.md)。此前中断的 R1 尝试仍按 [INVALID_ATTEMPT_01](data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/INVALID_ATTEMPT_01.json) 保留。

owner 已要求绕开所有中转，先检查现有 13.3B 的 Planner 输出；角色职责保持原样。完整诊断证实模型在思考后返回合法 JSON，但服务 JSON mode 缺依赖、思考前缀传递及计划字段/依赖合同尚未通过接入验证，详见 [13.3B 输出检查](data/experiments/LOCAL_13B_SUPERVISOR_CONNECTION_R1_20260907/REPORT.zh-CN.md)。正式后端切换和新双零运行尚未完成。按后续明确授权，Planner 的步骤和阶段数量由任务决定，已删除提示词、schema、计划补丁、未完成计划及阶段检查入口的数量上限；依赖、职责、根路径与证据约束继续校验，见 [数量限制整改](data/experiments/PLANNER_UNBOUNDED_PLAN_R1_20260907/REPORT.zh-CN.md)。旧输出不重评分，后续运行重新冻结。

owner 已授权新增 `realprojectdevv1`：CLI、数据流水线、HTTP API、已有项目维护、Web、全栈各 2 题，共 12 题。它是按需求编写的项目开发基准，包含新建和维护交付，**不是采集的真实用户 trace**。私有黑盒验证在隔离的只读 workspace snapshot 上执行，Web/全栈使用真实 Playwright 浏览器；参考实现和错误变异仅供作者验证，不进入 Agent 输入。完整隔离验收与本轮 pytest 结果以最终记录为准，尚无有效双零模型基线。

现有 Ladder-10 可用于有限的小项目/接口闭环；E2E-90 主要是文件、工具与恢复机制回归，含 2 个已有脚手架的迷你项目，不能称为 90 个真实项目。E2E-LH09 的 `mock_api` 与当前生产菜单仍存在适配冲突；不改旧题或分母来掩盖该问题。新的生产 trace 抽取器尚未实现。

## 文档与记录

- [项目工作规范](AGENTS.md)
- [唯一协议、数据来源与验收规则](docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)
- [当前交接](docs/HANDOFF.zh-CN.md)
- [本轮清理与验证记录](data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROUND_ANALYSIS.zh-CN.md)
- [基线准备与可见题集审查](data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/READINESS_ANALYSIS.zh-CN.md)
- [服务器资源清理与当前部署记录](data/experiments/SERVER_RUNTIME_CLEANUP_R1_20260907/)
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

服务器禁止使用 Git，所有 Git 版本管理和查询都在本地完成；源码仅通过 SSH 配合 rsync/SCP 从本地上传。部署时同时上传完整 engine 源码清单，包含相对路径与逐文件 SHA-256，并冻结 manifest 自身 SHA-256。服务须根据上传清单验证实际文件身份；启动、健康检查和 attestation 均不得执行 `git rev-parse`、`git status` 或其他 Git 命令。该部署方式及最终身份仍须完成验证，不因写入文档视为已通过。

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

训练和新建角色数据集版本目录仍需要 owner 书面确认；新增开发基准的授权不改变累计训练轮次。封存 Holdout 未参与本轮开发、作者验证或基线准备。
