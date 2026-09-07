# R2 A 臂运行报告

记录时间：2026-09-07T04:43:02.202968+00:00。这是 12 道开发题的一次完成运行记录；B 臂尚未开始。

## Agent 结果与解释边界

Strict **0/12**，agent_completed **0/12**，成功且工作区摘要发生变化的 mutation **0**。12 题记录的终止原因为 `strong_planner_unavailable`；目标契约无效事件共 **2**，均在 RP-API-01。全臂共记录 3 个 action，均为 `search_text`；成功 `run_command` 为 0。

11 题没有任何 RWKV generation 记录。RP-API-01 有 6 次 RWKV 逻辑生成请求、3 次成功搜索和 2 次执行前目标契约拒绝，仍未产生工作区修改。该臂主要暴露 Strong Planner 请求链的可用性阻断，不能据此把 0/12 归因为纯 RWKV 能力不足，也不能作为完整的 RWKV 项目能力基线或角色 StateTune 训练来源。

12 题都记录了 `goal_plan` 阶段的 HTTP 500 失败。已有 trace 只支持“Planner 请求未正常完成、运行因此未完成”的观测；HTTP 500 的最终根因仍由独立 `PLANNER_*` 诊断核验。本报告不据此判定是请求格式、模型别名、路由或上游服务哪一层的最终责任。

## 预注册门槛

| 门槛 | A 臂观测 | 结论 |
| --- | --- | --- |
| 全臂 mutation > 0 | 0 | 未通过 |
| operation_target_invalid = 0 | 2 | 未通过 |
| 每题最终 DB 主文件 + 现存 WAL/SHM ≤ 100,000,000 bytes | 12/12 在限额内，最大 2,564,096 bytes | 通过 |
| 全事件 controller_slice_exhausted = 0，且预算未耗尽 | 0 次；12 题均未记录预算耗尽 | 通过 |
| 固定题集完整，无漏题、重复或额外题 | 12/12，顺序与冻结清单一致 | 通过 |

全部门槛联合结果为 **未通过**。预算门和数据库门通过不能抵消 mutation 与目标契约门失败，也不代表 Agent 能完成项目。数据库数字引用冻结采集器的文件 stat；报告未打开 SQLite，未测量运行峰值、内存或显存。

## 逐题记录

所有题的终止原因均为 `strong_planner_unavailable`。下表“预算消耗”为 runner 导出的 transition 消耗，“RWKV 请求”为已记录的 generation start 逻辑请求，不能等同于底层 HTTP 重试次数。

| 题目 | Strict | completed | mutation | target invalid | 预算消耗 | 最终 DB bytes | RWKV 请求 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RP-API-01 | 0 | 0 | 0 | 2 | 9 | 2564096 | 6 |
| RP-API-02 | 0 | 0 | 0 | 0 | 1 | 81920 | 0 |
| RP-MAINT-01 | 0 | 0 | 0 | 0 | 1 | 81920 | 0 |
| RP-MAINT-02 | 0 | 0 | 0 | 0 | 1 | 81920 | 0 |
| RP-CLI-01 | 0 | 0 | 0 | 0 | 1 | 81920 | 0 |
| RP-CLI-02 | 0 | 0 | 0 | 0 | 1 | 81920 | 0 |
| RP-DATA-01 | 0 | 0 | 0 | 0 | 1 | 81920 | 0 |
| RP-DATA-02 | 0 | 0 | 0 | 0 | 1 | 81920 | 0 |
| RP-FULL-01 | 0 | 0 | 0 | 0 | 1 | 90112 | 0 |
| RP-FULL-02 | 0 | 0 | 0 | 0 | 1 | 86016 | 0 |
| RP-WEB-01 | 0 | 0 | 0 | 0 | 1 | 90112 | 0 |
| RP-WEB-02 | 0 | 0 | 0 | 0 | 1 | 90112 | 0 |

RP-API-01 的两次目标拒绝均由明确的 `[operation_target_contract]` 边界记录：第一次生成 `path='.'`，超出当时的 `README.md / server.py / verify_public.py` roots；第二次生成 `path='README.md'`，超出当时已缩小为 `server.py / verify_public.py` 的 roots。两次拒绝事件的 `action_executed` 均为 false。这是需要保留的独立目标一致性缺陷证据；两条 event/request/decision/selection 身份保存在 `R2_A_RUN_REPORT_EXPORT_AUDIT.json`。本报告未修改目标规则、评分或重算结果。

## 角色调用与覆盖范围

| 角色/记录 | 计数 |
| --- | ---: |
| RWKV Executor | 5 |
| RWKV Step Auditor | 1 |
| RWKV Finalizer | 0 |
| RWKV Final Auditor | 0 |
| Strong Planner | 13 |
| Strong Stage Checker | 0 |
| Selector 已记录 handoff | 3 |
| Selector 已完成 lane | 9 |
| Selector 实际总请求 | unknown；已记录下界 9 |

Planner 与 Stage Checker 配置均为 `gpt-5.6-sol`，这些计数来自已记录的逻辑请求；Planner 13 次不等于成功得到 13 份计划，也不等于 HTTP 尝试次数。Selector 的 9 条已完成 lane 是观测下界，实际请求总数仍为 unknown。Finalizer、Final Auditor 和 Stage Checker 的零调用说明本轮未覆盖这些完成阶段，不能用于评价它们的能力。

trace 模式审计未发现已观察 bootstrap 使用非零 State，也未发现已记录请求采样参数与冻结配置不一致。这只约束本轮实际发生的调用；11 题未到 RWKV 生成阶段，不能用缺失调用证明这些题上的行为。

## 身份证据与后续使用

`ARM_A_COMPLETION_R2.json` 在 2026-09-07T04:36:36.018104+00:00 记录 runner exit code 2、本地冻结文件未变、远端部署未变，并绑定冻结清单 SHA `aba256f3b419c53971174c77866fcb7349df96d241211f3124032b6527d38bba`。本次再次核对了 12 份 audit 导出 SHA 与 derived metrics、trace patterns 的来源 SHA 一致。身份保持与导出完整说明结果可追溯，**不等于能力基线合格**。

B 臂未开始，因此没有双臂 Strict 差异、逐题翻转或 `N = abs(Strict_A - Strict_B)`；不能填写 N=0，也不能报告噪声带或增益。本轮不生成角色训练样本、不启动训练，训练累计次数和可用额度不变。主代理另行处理上游请求诊断和后续运行决定。

上游诊断请查看本轮独立记录 `PLANNER_ENVELOPE_PROBE_R1_plain.json`、`PLANNER_ENVELOPE_PROBE_R1_json.json`、`PLANNER_ENVELOPE_PROBE_R2_json.json`、`PLANNER_FULL_WIRE_R1_plain.json`、`PLANNER_FULL_REQUEST_REPLAY_R1.json` 及后续 `PLANNER_*` 记录；它们不属于 A 臂冻结评分。本报告仅引用其记录位置，未重新发请求或据其结果判定最终根因。

## 可复核工件

- `ZERO_A_R2_DERIVED_METRICS.json`：Agent 指标、门槛、角色计数与源文件 SHA。
- `ZERO_A_R2_TRACE_PATTERNS.json`：12 题失败类型、调用与 zero bootstrap/采样观测。
- `ARM_A_COMPLETION_R2.json` 与 `FROZEN_EXECUTION_MANIFEST_R2.json`：运行身份闭包。
- `R2_A_RUN_REPORT_EXPORT_AUDIT.json`：本报告对 12 份 audit 的只读复核摘要与事件身份。
- `R2_A_RUN_REPORT_SHA256.json`：以上来源、报告和作者脚本的 SHA-256 清单。

未读取 SQLite、隐藏评分或任何封存题集；未修改冻结文件、生产代码、parser、stop boundary、评分或已有结果。
