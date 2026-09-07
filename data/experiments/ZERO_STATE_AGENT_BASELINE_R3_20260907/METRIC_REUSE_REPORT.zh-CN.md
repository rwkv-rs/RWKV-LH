R3 指标工具复用已完成离线核验：采集器原 33 项、比较器原 24 项，以及本次 9 项身份绑定和等价检查全部通过。本子任务模型调用 0、SSH 调用 0；这些是人工指标记录测试，不是 Agent 能力成绩、生产角色 trace 或 StateTune 数据。

采集器只更新默认定义路径及帮助文案；比较器只更新轮次标签、冻结 revision 和输出 schema 的轮次身份。其余源码经允许替换清单逆向还原，与 R2 字节完全一致；R2 来源 SHA 分别匹配原冻结清单与原比较自测记录。旧文件未改。新定义中的 schema、suite、题数、题序、臂数、aggregation 和 metrics 与 R2 相同。

| 工具 | R3 路径 | SHA-256 |
| --- | --- | --- |
| 采集 | `/home/chase/GitHub/RWKV-LH/temp/collect_zero_project_metrics_r3_20260907.py` | `70615b3dcfaec19e6069932dfa0655959822562687eaa4e4c9d4e2807e401d9b` |
| 比较 | `/home/chase/GitHub/RWKV-LH/temp/compare_zero_project_arms_r3_20260907.py` | `ae523e321e4e373351bb50ba32add6f36de266bcfeaca21dfb396856677cdc1b` |
| 指标定义 | `/home/chase/GitHub/RWKV-LH/data/experiments/ZERO_STATE_AGENT_BASELINE_R3_20260907/METRIC_DEFINITIONS_R3.json` | `7556056e316b275dfb6ba3b7d102c473f5e029088840499315428a70ac294a4b` |

完整命令参数在 `METRIC_COMMANDS_R3.json`，执行时以最终 `FROZEN_EXECUTION_MANIFEST_R3.json` 绑定的命令为准。每臂使用完整 12 题固定题序，输出 `ZERO_A_R3_DERIVED_METRICS.json` 与 `ZERO_B_R3_DERIVED_METRICS.json`；比较输出 `ZERO_AB_COMPARISON_R3.json`。采集器仅读 results、RUN_PROTOCOL、每题 audit，并 stat 数据库主文件/WAL/SHM，不打开 SQLite。输出必须是新文件。

Agent 指标保持 Strict、completed、成功动作真实 workspace digest 变化次数、终止原因；随后报告角色指标。数据库门仍为主文件加 WAL 加 SHM ≤ 100000000 字节，mutation 总数 > 0、operation_target_invalid 为 0、无 controller slice exhaustion 的规则不变。缺失状态、事件、digest、终止原因或预算标志保持 unknown；未知不写成 false、0 或门槛已通过。Selector 实际请求数仍为 unknown，已记录完成 lane 数只能作为下界。

比较器验证 12 题分母、题序、每题与汇总一致性、两臂参数一致、freeze/completion、源码及采集来源 SHA、结果时间顺序。仅在完整证据有效且 Strict 已知时给 `N = abs(Strict_A - Strict_B)`；已知指标门失败会保留 Agent FAIL，未知指标门会保留 UNKNOWN。已知 native Planner / Stage 失败按实际原始结果记录，不能因开跑授权放宽评分、补齐未知或重试拼臂。历史字段键 `strong_planner` / `strong_stage_checker` 只是事件分组名称；实际模型身份由 R3 冻结配置决定，不能据键名声称调用强模型。

证据为 `METRIC_IDENTITY_COPY_VERIFICATION.json`、`METRIC_COLLECTOR_SELFTEST/SELFTEST_RESULT.json`、`COMPARE_SELFTEST_R3/SELFTEST_RESULT.json`、`METRIC_REUSE_VERIFICATION_R3/VERIFICATION.json`。来源与证据 SHA 列于 `METRIC_REUSE_SOURCES_SHA256.json`。本报告只证明工具复用和离线核验完成，不预报两臂成绩或生产运行成功。
