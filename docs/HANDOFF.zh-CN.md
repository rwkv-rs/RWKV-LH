# RWKV-LH 当前交接

更新时间：2026-09-07。整改轮次：`PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907`。

当前阶段：统一协议与旧链清理；远端 attestation、两遍 all-zero 基线和 Agent 验收待执行。完整验证结果以本轮 `ROUND_ANALYSIS.zh-CN.md` 和 `MANIFEST.json` 为准。

## 1. Agent 级状态

当前代码没有新的 Strict / completed / mutation / 终止原因评测结果。本轮不训练、不重评分历史 confirmation、不运行真实模型 benchmark。旧成绩对应旧代码，已经从当前状态页面和本地实验目录移除，不作为当前基线。

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
- 本轮没有授予训练或新数据集版本目录权限，也没有复测、选择或发布新 State。

## 5. 环境与验收隔离

工作区：`/home/chase/GitHub/RWKV-LH`；仅在 WSL `UbuntuRecovered` 执行。

```bash
uv sync --frozen --extra selector-runtime --group dev
.venv/bin/python -m pytest -q tests/
```

完整回归需要 Torch；不接受 State 注入测试跳过。默认测试数据位于 `data/test_runs/pytest/`；生产运行缓存使用 `data/runtime/`，不依赖 `temp/` 分析脚本。

Real Agent Holdout V2 的题集/隐藏验收仍隔离于原 benchmark 和 dataset 目录。冻结登记与来源目录迁移到 `data/acceptance/`，未读取内容；相关测试位于 `acceptance_tests/`，不得在普通回归中执行。旧 Holdout 生成与相似度重算脚本已删除，避免重新生成冻结题集或调用已删除训练数据链。冻结相似度绑定仅与删除前记录的旧 source SHA 校验，不重新计算相似度。

## 6. 下一步

1. 当前代码完整回归通过后，以当前协议常量及源码 SHA 重新部署/attestation Selector 和各角色运行身份；端口、PID、旧 manifest 不视为现状。
2. 固定代码和参数，all-zero 两遍 Ladder-10；mutation > 0、operation-target invalid = 0、无状态库 > 100 MB、无 controller_slice_exhausted。两遍 Strict 差建立噪声带。
3. 达标后实现 `role_trace_dataset_v1.py`，只从生产 durable trace 抽取并逐字节重算 prompt。冻结回归集和新建数据版本目录仍需 owner 书面确认。
4. 对现有 State 做同代码消融；达到超噪声带 Agent 门后进入 E2E-90 和边界回归。
5. 训练需 owner 确认且先完成轮次对账；Holdout 仅在最后运行一次，结果不用于返工。

## 7. 本轮记录

`data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/` 中保存删除清单、先失败后通过日志、完整回归日志、当前源代码指纹及结论。该轮是代码/数据链清理，不是角色训练轮次。
