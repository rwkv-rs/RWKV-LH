# RWKV-LH 当前交接

更新时间：2026-09-07。基线准备与执行记录：`ZERO_STATE_AGENT_BASELINE_R1_20260907`；R2 已冻结并执行完整 A 臂，B 臂尚未启动。服务器清理轮次：`SERVER_RUNTIME_CLEANUP_R1_20260907`。上一轮协议整改为 `PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907`。

当前阶段：服务器上传部署与完整源码清单核验已完成，本地生产提交 `eab0a699`。R2 A 的 12 题全部以 `strong_planner_unavailable` 停止，正在按 owner 要求排查 Planner 上游请求格式及转发故障；B 臂暂未启动，没有有效双零能力基线。作者参考自验、整体 bubblewrap 验证和完整 pytest 均须与模型结果分开报告。

## 1. Agent 级状态

R2 A 已执行完整 12 题：Strict **0/12**、completed **0/12**、mutation **0**；12 题终止原因均为 `strong_planner_unavailable`，operation-target invalid **2**。状态库最终大小与预算门通过，mutation 和目标拒绝门未通过。11 题没有发生 RWKV 生成，不能把这次受上游故障影响的结果当作纯 RWKV 能力基线、噪声估计或训练来源；详见 [R2_A_RUN_REPORT.zh-CN.md](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/R2_A_RUN_REPORT.zh-CN.md)。R2 B 尚未启动，没有双零差值。

首次 `real_project_zero_a` 因 owner 的服务器禁用 Git 约束而中止，仍按 [INVALID_ATTEMPT_01.json](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/INVALID_ATTEMPT_01.json) 保留原始无效记录，与 R2 A 分开。本轮没有启动训练，也未重评分历史 confirmation。旧成绩对应旧代码，不作为当前基线。

Planner 与 Stage Checker 当前统一使用 `chat/completions` + JSON mode。已重建的 Planner user payload 与原 trace SHA 完全匹配；同一个最小 JSON-mode 请求先 500 后 200，完整请求保留或删除 `response_format` 均 500，增加 `stream=true` 后也在任何 SSE 之前返回 500。已有 200 响应都通过当前 decoder，不能凭此删字段、改为流式或判定请求格式是根因。结论与六次独立诊断见 [PLANNER_UPSTREAM_DIAGNOSIS_R1.zh-CN.md](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/PLANNER_UPSTREAM_DIAGNOSIS_R1.zh-CN.md)，SHA-256 `9424950c36c67d64d31a552b81a2b4216bdc21160fad115df80f3c2a4676dc35`。所有诊断调用排除在 Agent 分数和角色数据之外；具体内部原因仍需中转后台按请求ID核实。

单元回归仅证明代码合同与恢复路径，不证明 Agent 增益。最终发布仍须满足统一规范和 AGENTS §7。

## 2. 生产架构与 State

```text
Strong Planner 提供 active step
  -> Controller 编译 eligible operations、typed targets、execution state
  -> Selector 2.9B（三菜单 fresh State，冻结 vocab logits + suffix trie）
  -> Executor 13.3B 只填写已选 operation 的参数
  -> Controller 校验 operation / target / scope
  -> Harness 执行并持久化 action / evidence
  -> Mechanical Evidence Gate
  -> Step Auditor 13.3B
  -> Strong Stage Checker（stage 完成边界）
  -> Finalizer 13.3B
  -> Final Auditor 13.3B
  -> completed / repair / blocked / yield
```

入口为 `product_runtime.build_product_controller()`，架构常量为 `stateful_goal_loop.STATEFUL_GOAL_LOOP_ARCHITECTURE`（v7）。Controller 不读取隐藏 acceptance、不重写 Final。

owner 已确认推理服务器为 `rwkv-8222`；当前 Strong Planner 与 Strong Stage Checker 均为 `gpt-5.6-sol`。服务器旧服务/缓存清理与当前源码部署的路径、删除清单及运行身份见 [服务器清理轮记录](../data/experiments/SERVER_RUNTIME_CLEANUP_R1_20260907/)。最初本地端口预检只是历史准备证据，不能替代部署后的 attestation。

owner 新硬约束：所有 Git 版本管理与查询只能在本地执行，服务器不运行任何 Git 命令，包括启动或 attestation 中的 `git rev-parse` / `git status`。本地冻结源码后通过 SSH 配合 rsync/SCP 上传；engine 同时上传完整源码 manifest，登记文件相对路径、逐文件 SHA-256 与 manifest 自身 SHA-256，服务按清单核验实际文件。部署证据将本地提交与上传清单绑定，服务器无需 Git 仓库；清单缺失或不一致时不得退回远端 Git。运行时清单配置已上传，两项服务重启后通过完整文件核验和健康检查；本地完整回归 697 项通过。证据见本轮 `UPLOAD_ONLY_REPORT.zh-CN.md`，这不代表已获得模型基线成绩。

durable causal ledger 是全局事实权威。各角色 session 独立；Executor State 范围是单次 selected action，新动作通常重新 bootstrap；跨动作事实从 ledger 投影。Auditor / Finalizer 从各自初始 State 开始，不继承 Executor WKV。Selector 三次菜单求值也不共享递推 State。这些调用属于当前登记架构，不能据角色分数单独声称 RWKV 长程能力提高。

## 3. 当前唯一协议

| 角色 | 模块（`rwkv_lh/goal_state_protocols/` 下） | 输入版本 | 共享构造入口 |
|---|---|---|---|
| Selector | `selector_intent_v4.py` | selector-intent.v4 | `build_current_progress()` → `build_prompt_source()` |
| Executor | `executor_args_v4.py` | executor-args.v4 | `build_target_contract()` / `build_execution_state()` → `build_prompt_source()` |
| Step Auditor | `auditor_step_v3.py` | auditor-step.v3 | `build_prompt_source()` 内调用 `build_gap_catalog()` |
| Finalizer | `finalizer_answer.py` | finalizer-answer.v1 | `build_prompt_source()` |
| Final Auditor | `auditor_final.py` | auditor-final.v2 | `build_prompt_source()` 内调用 `build_gap_catalog()` |

每模块拥有其 schema / prompt prefix；Selector 同时拥有菜单、角色、目标后缀及 endpoint 常量。生产和测试通过共享构造入口再调用 renderer，禁止另造同名角色协议。独立 Executor 没有旧披露/重试兼容分支；预算估算与实际披露使用同一份当前输入。

旧模块、stub、旧合成生成器、旧角色评测脚本及其测试/字节码已删除。旧角色数据、旧实验与临时驱动也已直接删除，没有本地 retired/archive。当前只保留本轮路径/SHA/验证记录；历史内容查询 Git / GitHub，未跟踪旧文件不具备远端历史保证。

## 4. State 与轮次边界

- Selector 已用完三轮，现有 State 的旧输入适配尚未在当前链路验证，不得再训。
- Executor / Step Auditor 曾被登记为“剩一轮”，但存在 Round3 / final-round / replacement-Round3 记录。累计次数必须由 owner 对账，不能把版本更换或回退初始化视为新的额度。
- Finalizer 当前使用 zero，没有独立训练授权。
- Final Auditor 最多三轮；历史 confirmation 改口径结果不作为当前有效门槛。
- owner 已单独授权 12 题项目开发数据集 `rwkv_lh_real_project_dev_v1`；该授权不包括新增角色训练额度。本轮没有复测、选择或发布新 State。

## 5. 环境与验收隔离

工作区：`/home/chase/GitHub/RWKV-LH`；仅在 WSL `UbuntuRecovered` 执行。

```bash
uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q tests/
```

完整回归需要 Torch、Playwright 和 Chromium；不接受 State 注入或必需的浏览器验证跳过。CI 使用相同 extra，并安装 Chromium 的系统依赖。默认测试数据位于 `data/test_runs/pytest/`；生产运行缓存使用 `data/runtime/`，不依赖 `temp/` 分析脚本。

Real Agent Holdout V2 的题集/隐藏验收仍隔离于原 benchmark 和 dataset 目录。冻结登记与来源目录迁移到 `data/acceptance/`，未读取内容；相关测试位于 `acceptance_tests/`，不得在普通回归中执行。旧 Holdout 生成与相似度重算脚本已删除，避免重新生成冻结题集或调用已删除训练数据链。冻结相似度绑定仅与删除前记录的旧 source SHA 校验，不重新计算相似度。

## 6. 开发评测与下一步

新套件 `realprojectdevv1` 共 12 题，CLI、数据、HTTP API、已有项目维护、Web、全栈六类各 2 题；材料位于 `data/datasets/rwkv_lh_real_project_dev_v1/`。来源为 owner 授权编写的开发基准，不是采集的真实用户 trace，不直接充当角色训练样本。Agent 只接收公开任务、初始文件与生成器；私有黑盒程序、reference 和 mutant 都在其工作区之外。验收读取隔离的只读 snapshot，Web/全栈实际运行 Playwright，其他题以真实 CLI/HTTP/文件/重启行为检查。作者参考与错误变异的验证结果不能代替 Agent 运行。

可见审计确认：Ladder-10 包含 5 新建、4 修复/扩展、1 数据，Agentv1 账本与 L4 Ledger 同族；公开 Web 检查原先没有浏览器。E2E-90 为 2 迷你补全、13 修复扩展、34 工作流、41 孤立任务，0 从零产品；LH09 `mock_api` 与当前生产菜单冲突。原题集与评分保持原状，新项目套件另行冻结身份和比较参数。

1. 汇总新套件的 reference/mutant 隔离验收及最终完整代码回归，固定数据、评分和源码 SHA；从本地上传源码与完整 engine manifest，并核验当前服务的模型/State/协议/decoder 和文件身份，全程不在服务器使用 Git。
2. 保留 R1 原冻结注册与中断证据，新增 R2 执行注册并冻结配置/SHA后，用全新 workspace 和 State 重跑同 12 题的两遍 all-zero。按 owner 最新授权不先跑 Ladder、不跑 E2E-90，不接续中断 A，也不只补 B。要求 mutation > 0、operation-target invalid = 0、每题状态库 ≤100,000,000 bytes、无 controller_slice_exhausted；其他硬门以新的执行注册为准。独立记录两遍 Strict 差和逐题翻转，不复用无效尝试或其他题集噪声带。
3. 达标后实现 `role_trace_dataset_v1.py`，只从生产 durable trace 重建完整 checkpoint/State 输入链；native causal_ledger 的 input.prompt 仅是最后 delta，不能直接训练。唯一 builder 重算正文还需绑定 bootstrap、实际初态、rollover/fork 和原始 token IDs。冻结角色回归集和新建角色数据版本仍需 owner 书面确认。
4. 对现有 State 做同代码消融；扩大边界/异常/恢复/安全覆盖。E2E-90 保持机制回归定位，其生产适配冲突须显式处理，不能删题或改评分放行。
5. 训练需 owner 确认且先完成轮次对账；Holdout 仅在最后运行一次，结果不用于返工。

## 7. 本轮记录

`data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/` 中保存删除清单、先失败后通过日志、完整回归日志、当前源代码指纹及结论。该轮是代码/数据链清理，不是角色训练轮次。

本轮准备的题集/公开验证器/trace 审查与配置预检见 [基线准备记录](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/READINESS_ANALYSIS.zh-CN.md)；新开发题的作者验证在数据集各组目录，整体隔离验证与完整测试由本轮最终记录汇总。服务器清理记录独立保存，不把释放空间或服务健康当作 Agent 指标。
