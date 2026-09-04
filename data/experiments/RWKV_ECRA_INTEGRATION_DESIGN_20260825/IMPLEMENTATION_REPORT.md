# RWKV-ECRA Phase 0 / Phase 1 离线实现报告

> 历史阶段记录；当前工程与 R9 状态以 `IMPLEMENTATION_REPORT_R2.md` 为准。

状态：`OFFLINE_FOUNDATION_PASSED`；**不得标记为完整统合或产品默认**

执行日期：2026-08-25（Asia/Shanghai）

## 1. 本轮结论

本轮完成了 Phase 0，以及 Phase 1 中“不接真实网络”的工具/策略/证据主链：

1. 在路由实现前冻结了 120 条中英固定场景；
2. 把 capability、network、data boundary、side effect、result、cache、recovery 和 evidence 元数据并入
   唯一 `ActionDefinition`；
3. 实现 `external-evidence.v1`、内容寻址的 source/span/record/route、三种联网策略和逐字段出站 provenance；
4. 以 frozen backend 接入 `web_search`、`connector_lookup`、`calculator`、`date_diff`、`current_time`；
5. 保持 RWKV 为工具名与完整参数的唯一作者；策略只接受/拒绝原调用，不改写 query、不替换工具；
6. Controller 把 handler 结果绑定到 Controller 分配的 Action ID；损坏证据包使动作失败关闭；
7. progressive disclosure、typed policy rejection 后由 RWKV 重选、精确证据和既有全量回归均通过。

默认 `ActionHarness()` 仍保持现有本地工具面。联网扩展只有在调用者明确提供 backend、不可变网络策略和
provenance resolver 后才会注册。这是当前阶段的安全边界，不是缺省启用遗漏。

## 2. 实现文件

- `rwkv_lh/retrieval/contracts.py`：版本化、内容寻址且失败关闭的外部证据值对象；
- `rwkv_lh/retrieval/policy.py`：`offline / auto_public / explicit_egress` 和出站 provenance；
- `rwkv_lh/retrieval/actions.py`：五个工具、frozen provider、确定性计算；
- `rwkv_lh/harness.py`：权威 capability 元数据与 JSON Schema `enum` 校验；
- `rwkv_lh/controller.py`：证据信封与 Action ID 的唯一身份绑定；
- `scripts/generate_rwkv_ecra_route_dataset_v1.py`：固定路由集机械生成器；
- `data/datasets/rwkv_lh_ecra_route_v1/`：120 例数据、说明和摘要；
- `tests/test_retrieval_harness.py`：离线合同与端到端控制器测试。

没有把 ECRA/Scout 的 Orchestrator、Planner、Reviewer、Writer 或 `AgentState` 接入本项目，也没有让
RWKV-LH 运行时依赖相邻 checkout。

## 3. 固定数据集

`rwkv-lh-ecra-route.v1` 共 120 例：

| 类别 | 数量 |
|---|---:|
| local-only | 30 |
| public-web-required | 25 |
| structured-connector | 20 |
| deterministic-compute | 15 |
| mixed-local-online | 20 |
| privacy-policy-rejection | 10 |

数据内容 SHA-256：

- `cases.json`: `7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a`
- `README.md`: `932e39de9660d024c3ce557d2a5e330a8e56cbd6cfa7ffb376f2290316db430c`
- generator: `bef58d304f829a9d864306c7dcf78bf9e008900d0c7c6ec9497357e5ccc602f9`

重新运行生成器后摘要未变化。

## 4. 验证结果

环境：WSL2 Linux `6.18.33.1-microsoft-standard-WSL2`，Python `3.13.11`，RWKV-LH HEAD
`ca1c4c856d6a4616db8d3856966dfb8c0443922e`。执行前工作树已有大量用户修改；本轮未清理或覆盖它们。

| 命令 | 结果 |
|---|---:|
| `uv run pytest -q -s tests/test_retrieval_harness.py` | 12 passed |
| `uv run pytest -q -s tests/test_unified_controller.py tests/test_model_session.py tests/test_long_horizon_state.py tests/test_e2e_benchmark_fixture.py` | 62 passed |
| `uv run pytest -q -s` | 189 passed |
| `git diff --check -- <本轮相关路径>` | 通过 |

新增测试覆盖：

- route120 计数、类别、连续 ID 和生成器/数据摘要；
- ActionDefinition 权威元数据及模型可见 schema 单源投影；
- exact span 原文字节保留、snapshot SHA-256、record/route 内容 ID 防篡改；
- 三种策略的失败关闭、缺失/非法 provenance、secret 零出站和 Controller 零改写；
- frozen web result、connector enum 拒绝、计算器 AST 边界、日期与时区；
- progressive `select_tool -> web_search -> final_answer`；
- policy rejection 后 RWKV 自己重选 `final_answer`；
- Controller Action ID 与外部证据包绑定。

## 5. 尚未通过、尚未运行的门槛

下列项保持未完成，不能用本轮单测替代：

1. route120 尚未用真实 RWKV 跑 A/B，因此 network macro-F1、web/connector macro-F1、FPR/FNR 和调用序列
   相似度没有结果；
2. Contract Graph v2 尚未落地；Strong Planner 当前 v1 结构仍可输出 `allowed_operations`；
3. ECRA provider、connector、fetch、clean、chunk、Evidence Compiler 尚未提炼；
4. 原始 source snapshot 的不可变持久化、崩溃后从 snapshot 恢复、retrieval/evidence ledger projection 尚未实现；
5. Reviewer 对 freshness/source identity/evidence closure 的审核和 verified-ledger Finalizer 尚未实现；
6. live canary、Full90 A/B/C、确认复跑与全部预注册相似度门槛尚未执行；
7. UI/API 的 run-level policy 和四层事件展示尚未接入。

## 6. 对“距离全套主动 Harness”的更新判断

从“代码模块数”看，基础底座已从设计态进入可执行态；从“采纳门槛”看仍处于早期。当前大致完成：

- 工具执行与安全合同层：约 70%；
- 联网检索内核与恢复层：约 20%；
- Strong Planner / RWKV 工具权分离的 v2 调度层：约 25%；
- 主动闭环的评测、Reviewer、UI 与产品化：约 15%。

综合不是简单平均：全套主动 Harness 仍约完成 **35%–40%**。最大剩余风险已经从“能不能挂工具”转为
“Planner 不夺工具权、网络证据可恢复、RWKV 在 route120 上真能稳定选对，以及长程闭环是否过线”。

下一阶段应先做 Contract Graph v2 capability projection 和 route120 B runner，再移植任何 live provider；否则
真实联网只会放大当前 v1 Planner 工具权和不可恢复 snapshot 两个架构缺口。
