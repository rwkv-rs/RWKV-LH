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

本轮原生适配没有运行新的 Agent 评测，没有新增 Strict / completed / mutation / 终止原因指标。按 owner 授权，Planner 与 Stage Checker 已配置为同一现有 13.3B 服务，使用 `vllm-rwkv-native` 的 `/completions` 和独立显式 zero State；Planner 输出预算为 8,192 tokens，共用读取超时为 240 秒，Stage Checker 仍为 2,400 tokens，其余角色预算与职责不变。生产 Planner 单次连接探针已得到 HTTP 200 和自然结束的合法 JSON，但 `GoalPlanPatch` 首先因额外顶层 `goal_digest` 拒绝；完整原文的独立检查还发现 `success_evidence` 类型等合同问题。因此尚不能启动全面基线或宣称接入问题全部解决，详见 [本轮原生适配报告](data/experiments/VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/REPORT.zh-CN.md)。

最新强模型复测仍未达到开跑门槛：next-token.cc 的认证模型目录正常，但当前完整 `gpt-5.6-sol` Planner 请求在 32.8 秒后返回 HTTP 500 / `do_request_failed`。固定矩阵首错停止，0 通过、1 失败、9 未运行；没有切换配置或启动新的双零基线。RWKV 服务器与文件身份核验均通过，见 [稳定性复测记录](data/experiments/STRONG_UPSTREAM_STABILITY_R1_20260907/REPORT.zh-CN.md)。

Planner 的步骤和阶段数量由任务决定，不设固定上限；提示词、schema、计划补丁、未完成计划及阶段检查入口完整保留计划。当前模型仍有 16,384-token 上下文上限，不能静默截断步骤或证据来适配窗口。依赖、职责、根路径与证据约束继续校验，任务结束仍由 RWKV 结合目标覆盖和执行证据判断，见 [数量限制整改](data/experiments/PLANNER_UNBOUNDED_PLAN_R1_20260907/REPORT.zh-CN.md)。旧输出与冻结报告不重评分，后续双零两臂均须重新冻结并完整运行。

owner 已授权新增 `realprojectdevv1`：CLI、数据流水线、HTTP API、已有项目维护、Web、全栈各 2 题，共 12 题。它是按需求编写的项目开发基准，包含新建和维护交付，**不是采集的真实用户 trace**。私有黑盒验证在隔离的只读 workspace snapshot 上执行，Web/全栈使用真实 Playwright 浏览器；参考实现和错误变异仅供作者验证，不进入 Agent 输入。完整隔离验收与本轮 pytest 结果以最终记录为准，尚无有效双零模型基线。

现有 Ladder-10 可用于有限的小项目/接口闭环；E2E-90 主要是文件、工具与恢复机制回归，含 2 个已有脚手架的迷你项目，不能称为 90 个真实项目。E2E-LH09 的 `mock_api` 与当前生产菜单仍存在适配冲突；不改旧题或分母来掩盖该问题。新的生产 trace 抽取器尚未实现。

## 文档与记录

- [项目工作规范](AGENTS.md)
- [唯一协议、数据来源与验收规则](docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)
- [当前交接](docs/HANDOFF.zh-CN.md)
- [StateTune 数据生成管线源码、现状与经验](docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md)
- [本轮清理与验证记录](data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROUND_ANALYSIS.zh-CN.md)
- [基线准备与可见题集审查](data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/READINESS_ANALYSIS.zh-CN.md)
- [服务器资源清理与当前部署记录](data/experiments/SERVER_RUNTIME_CLEANUP_R1_20260907/)
- [本轮 13.3B Supervisor 原生适配与连接验证](data/experiments/VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/REPORT.zh-CN.md)
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

本轮 Planner / Stage Checker 配置示例指向 `http://127.0.0.1:29613/v1`（转发服务器 `18234/v1`），两者模型 alias 为 `rwkv7-g1j-13.3b-zero-state-capability-ctx16384`。`RWKV_LH_PLANNER_BACKEND_PROFILE=vllm-rwkv-native`，关闭计划缓存、留空 fallback。原生请求保留 `System✿` / `User✿` / `Bot✿<think` 格式，不发送 `response_format`，避免当前部署缺少 `lmformatenforcer` 的约束生成路径。返回值必须自然 `stop` 且原文以 `>` 开始，仅合回本次实际发送的 `<think` 后交既有严格 JSON decoder；模型仍须自行输出合法字段，Controller 不补写计划内容。

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

训练和新建角色数据集版本目录仍需要 owner 书面确认；新增开发基准的授权不改变累计训练轮次。封存 Holdout 未参与本轮开发、作者验证或基线准备。
