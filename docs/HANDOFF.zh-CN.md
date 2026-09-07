# RWKV-LH 当前交接

更新时间：2026-09-07。当前准备轮次：`ZERO_STATE_AGENT_BASELINE_R1_20260907`；服务器清理轮次：`SERVER_RUNTIME_CLEANUP_R1_20260907`。上一轮协议整改为 `PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907`。

当前阶段：服务器旧资源清理、当前源码部署与身份核验、新增 12 题项目开发基准及隔离验收集成。双零模型基线和 Agent 验收尚未执行；作者参考自验、整体 bubblewrap 验证和完整 pytest 应分开报告，最终结果以本轮记录为准。

## 1. Agent 级状态

当前代码没有新的 Strict / completed / mutation / 终止原因评测结果。本轮尚未训练或运行真实模型 benchmark，也未重评分历史 confirmation。旧成绩对应旧代码，不作为当前基线。

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

1. 完成新套件的全部 reference/mutant 隔离验收与完整代码回归，固定数据、评分和源码 SHA；完成当前服务的模型/State/协议/decoder attestation。
2. 固定代码和参数运行双零，先检查 Ladder-10 硬门，再按预注册的新 12 题项目开发范围进行比较。要求 mutation > 0、operation-target invalid = 0、无状态库 > 100 MB、无 controller_slice_exhausted；各题集独立记录两遍 Strict 差和逐题翻转，不复用其他题集噪声带。
3. 达标后实现 `role_trace_dataset_v1.py`，只从生产 durable trace 重建完整 checkpoint/State 输入链；native causal_ledger 的 input.prompt 仅是最后 delta，不能直接训练。唯一 builder 重算正文还需绑定 bootstrap、实际初态、rollover/fork 和原始 token IDs。冻结角色回归集和新建角色数据版本仍需 owner 书面确认。
4. 对现有 State 做同代码消融；扩大边界/异常/恢复/安全覆盖。E2E-90 保持机制回归定位，其生产适配冲突须显式处理，不能删题或改评分放行。
5. 训练需 owner 确认且先完成轮次对账；Holdout 仅在最后运行一次，结果不用于返工。

## 7. 本轮记录

`data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/` 中保存删除清单、先失败后通过日志、完整回归日志、当前源代码指纹及结论。该轮是代码/数据链清理，不是角色训练轮次。

本轮准备的题集/公开验证器/trace 审查与配置预检见 [基线准备记录](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/READINESS_ANALYSIS.zh-CN.md)；新开发题的作者验证在数据集各组目录，整体隔离验证与完整测试由本轮最终记录汇总。服务器清理记录独立保存，不把释放空间或服务健康当作 Agent 指标。
