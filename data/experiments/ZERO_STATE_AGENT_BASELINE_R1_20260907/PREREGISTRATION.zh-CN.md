# 新真实项目开发集：双零基线预注册

轮次：`ZERO_STATE_AGENT_BASELINE_R1_20260907`。日期：2026-09-07。

状态：**PENDING / 未开跑；最终题集、评分程序、源码、配置和运行服务 SHA 待 root 冻结。不得据本草稿宣称已经通过任何 Agent 门槛。**

owner 最新书面选择是“先补真实项目任务和验收，再全面测”，并已授权新建开发评测集 `data/datasets/rwkv_lh_real_project_dev_v1/`。本轮直接对 `realprojectdevv1` 的 12 题跑两遍 all-zero，**不先跑 Ladder，不跑 E2E-90**。这一顺序来自 owner 最新授权，覆盖旧规范中先 Ladder 的本轮安排；不修改旧题集、旧评分，也不改最终 Holdout 纪律。

新增题的来源是 owner-authorized authored development benchmark，是作者构造的可运行项目，不冒称生产真实用户请求或生产 trace。授权范围为开发评测任务、行为验收及后续双零；角色 StateTune 数据集、角色回归集和训练仍需对应权限与合法轮次，不在这里自动授权。

本轮尚无 Strict / completed / mutation / 终止原因结果。参考实现自验及错误变异被拒绝只是验证评分器，不能当作 RWKV Agent 能力成绩。

## 1. 固定任务与两臂

suite key：`realprojectdevv1`。固定分母每遍 12，不使用 `--case`、`--max-cases` 或失败子集替换。执行顺序按 freezer 对源组路径的排序及 compiled tasks 固定如下；最终 manifest 与顺序 SHA 仍由 root 登记：

```text
RP-API-01, RP-API-02, RP-MAINT-01, RP-MAINT-02,
RP-CLI-01, RP-CLI-02, RP-DATA-01, RP-DATA-02,
RP-FULL-01, RP-FULL-02, RP-WEB-01, RP-WEB-02
```

两臂 `zero_a`、`zero_b` 都使用同一题集、初始文件、私有验收、顺序、源码及参数；各臂每题新建 workspace、LongHorizonStore 和角色 session，不继承上一题/上一遍的 WKV。五个角色 Selector / Executor / Step Auditor / Finalizer / Final Auditor 均从 zero 初始 State 开始；zero 不等于关闭当前架构内允许的 RWKV 递推、Harness 执行或机械证据门。

拟用绝对输出目录：

- `/home/chase/GitHub/RWKV-LH/data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/real_project_zero_a`
- `/home/chase/GitHub/RWKV-LH/data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/real_project_zero_b`

缺题、进程异常、服务错误仍占原分母，并显式标记未完成。不能从 12 中删除失败题，不能换题或只重跑失败题取最好结果。身份变化或必要源码修复使受影响双零比较 INVALID，保留原始事实，重新冻结后重跑两遍。

## 2. 已固定的运行设置

主 runner 为 `scripts/run_rwkv_e2e_benchmark.py`，采用 `--suite realprojectdevv1 --stateful-goal --independent-selector --supervisor openai --supervisor-strategy goal_stages --tool-disclosure-mode progressive --max-transitions 200 --concurrency 1 --supervisor-pending-resume-attempts 0`。root 冻结时登记完整绝对 argv 和脱敏配置；当前这段参数不是启动记录。

| 项目 | 冻结值 / 依据 |
|---|---|
| 架构 | 当前 `STATEFUL_GOAL_LOOP_ARCHITECTURE`，检查时为 `rwkv-stateful-goal-loop.v7`；最终 attestation 引用常量 |
| 每题总 transitions | 200；runner 正常 Goal continuation 共用该总预算，不能每次重新获得 200 |
| 题间并发 | 1 |
| supervisor pending 恢复次数 | 0 |
| 人工/选择性失败重跑 | 0；基础设施失败记原始结果，不用成功补跑替换 |
| 四个 Goal 生成角色的实际采样 | Executor / Step Auditor / Finalizer / Final Auditor：temperature=0.1, top_p=1.0, top_k=0, presence_penalty=0.0, frequency_penalty=0.0, penalty_decay=0.996；来自 `LongHorizonModel._SAMPLING` |
| 通用 session 缺省采样 | `SessionSampling.temperature=0.05` 仅在调用方未传 sampling 时生效；本轮上述四个 Goal 角色显式传入 `_SAMPLING`，不使用这个缺省值 |
| 默认输出 token 上限 | Executor 1800；Step Auditor 400；Finalizer 1400；Final Auditor 400；实际运行 trace 必须匹配冻结配置 |
| 上下文目标 | max_model_len=16384，context_safety_margin=32，bos_token_count=1；逐角色服务 capability 与 settings 最终核实 |
| Selector | 当前原生 LM head eligible suffix trie argmax、三个固定菜单顺序及固定投票，不擅改为额外模型调用 |
| seed | SessionSampling 未暴露 seed；不编造随机种子能力，记录服务实际能力与双零波动 |
| Strong Planner / Stage Checker | 保持生产角色职责；模型版本、token 上限、reasoning/请求参数、超时重试等待 root 脱敏配置冻结；不注入接口不支持的 temperature |
| 内部传输重试 | 等待实际 settings 快照；pending 恢复=0 不表示客户端内部 retry/backoff=0，不得混淆 |

采样代码依据：`rwkv_lh/model.py:141` 定义 `_SAMPLING`，Finalizer（:844）、两个 Auditor（:1128）和 Executor（:2747）均在 generate 调用中显式传入；`rwkv_lh/model_session.py:1296` 优先采用该传入值，并把同一 `selected.to_dict()` 写入 generation_started 及发送给 native `state_generate`。当前 runner 的运行元数据也从 `LongHorizonModel._SAMPLING` 读取实际值。早期 `PUBLIC_CONFIG_FROZEN_PROPOSED.json` 的 semantic_sampling=0.05 是已识别的报告失真，不能用作本轮有效参数；最终以 root 新生成并核对 trace 的 `PUBLIC_CONFIG_FROZEN.json` 为准。此次修正只使报告与既有实际采样一致，实际生成 temperature 始终是 0.1。Selector 采用上表的原生 argmax 路径，不套用四个生成角色的随机采样；Strong Planner / Stage Checker 客户端未显式传 temperature，按最终冻结的模型与提供方默认行为单独记录。

执行环境必须为 WSL `UbuntuRecovered`，依赖按 `uv sync --frozen --extra selector-runtime --group dev`；完整 `tests/` 全绿且无 Torch / State 注入跳过。服务器由 owner 指定为 `rwkv-8222`；需要记录新服务、engine、模型、State、协议、decoder 和当前源码 SHA，不把“发现服务器/已启动端口”当作身份通过。

## 3. 指标口径

机器可读定义见同目录 `METRIC_DEFINITIONS.json`。最终 collector 必须在开跑前实现、验证并冻结 SHA；当前 runner 没有直接导出 mutation_count / operation_target_invalid_count / state_database_bytes，这些不能填造为 0。

| 指标 | 当前可复核口径 |
|---|---|
| Strict | `results[].passed` / `audit.passed`。逐题等于 completed、外部验收通过、Final 非空、Final 与原 RWKV 输出逐字节绑定、无验收路径泄露、bwrap 验收隔离与 Agent 进程树已关闭等条件全部满足。报告通过数 / 12 |
| completed | `agent_completed`：run_state 存在且 status 为 completed。外部验收通过、基础设施执行完毕和业务 completed 分开报告 |
| action_count | Stateful Goal 下 len(state.actions)，包括失败/中断记录，不能当 mutation 数 |
| mutation_count | 按唯一 action_id，status=succeeded 且 before/after workspace digest 均为完整小写 64 位 SHA-256 且不同。只统计 Agent 执行产生的变化；初始化/私有验收写入/冻结 snapshot 已排除的缓存不算；成功 no-op 不算。另报失败动作有副作用数、已结束但 digest 缺失/无效数，缺失为 unknown 而非 0 |
| check/run 证据 | 单列成功 run_command 动作数及命令/输出；成功 echo 不自动证明完成了有效项目验证，实际检查依据 trace 审计 |
| operation-target invalid | 按唯一 causal record id，event_type=`protocol_rejection_recorded` 且 payload.error **以**精确标记 `[operation_target_contract]` 开头。标记来自 Controller `_validate_decision_target_contract` 的目标类型/路径根合同拒绝；任意日志里的引用不计。不能在多个导出副本中重复计数，也不能混入一般 parser/schema 拒绝；state/事件缺失为 unknown |
| protocol_rejection_count | runner 现有字段，来自 state.protocol_rejections；与目标 invalid 分开 |
| 终止原因 | 报 `status`，并从 causal_order 找最后一个 run_completed/run_blocked/run_yielded/run_interrupted/run_failed，保留 event id/type 与 payload.reason；run_completed 无 reason 时规范化为 completed，其他无 reason 用事件类型。缺 state 用 runner failure/not_created。所有预算 blocked、协议 blocked、基础设施 yield 必须明确区分 |
| 状态库字节 | 每题收尾时，Controller/客户端关闭并导出 trace 后、任何清理/VACUUM/压缩前，对 `<case>/state/long_horizon.db` 加仍存在的 `-wal`、`-shm` 使用 stat.st_size 求和，记录各组件。100 MB 定义为 **100,000,000 bytes**。缺主 DB 为 unknown。该门是本地 SQLite 最终大小，不是峰值磁盘/RAM/VRAM；不含 workspace、导出 JSON/gzip、模型权重和远端 WKV 缓存 |

目标 invalid 的数值只代表上述固定拒绝边界，不证明所有工具错误/安全路径均无问题；其他异常保留原始统计与首错分析。本轮新 12 题没有 runner 定义的 FN，不把 E2E-90 的 FN 指标拼入或声称已达标。

角色调用在 Agent 数字之后报告：四个 13.3B 角色使用 model_trace 的 generation_started 按 model_role 分组；Selector 用 exact_tool_selection_staged 中保存的 lane_selections 统计已记录完成 lane 与 handoff。Selector 失败请求可能在 handoff 前缺失，因此存在这类失败时实际总调用数为 unknown，不能把已记录成功 lane 下界冒称全部调用数。

## 4. 双零硬门与噪声

每遍按完整 12 题汇报。已预注册的运行质量硬门为：总 mutation > 0、operation-target invalid=0、每题已知状态库大小 ≤100,000,000 bytes、没有任何 `controller_slice_exhausted` 因果事件且 `goal_transition_budget_exhausted` 不为 true。逐题仍须审计项目是否有实际修改和有效 check/run，不能靠一题写很多文件掩盖其余题未行动。度量缺失不能按通过处理。

Strict 基线用于观察当前能力，此处不凭空设置或声称新集合已达到一个 Strict 最低分。failed、blocked、yield 与 completed 按原始事实保留。预算耗尽造成的 blocked 不能当成主动合法成功终止。任一硬门失败都先保存全量事实并定位结构性原因，不进入训练或候选增益结论，也不改门槛放行。

双零噪声带 `N=abs(Strict_zero_a - Strict_zero_b)`，单位为通过题数；同时保存逐题翻转矩阵、动作/mutation 差异和终止原因分布。项目已有约 ±3 的波动提示与实际双零分开呈现；N=0 不证明完全确定。未来候选增益必须严格超过对应集合实际噪声带，并保持 zero 已过题不退化、协议/安全失败不增加；候选聚合公式在候选轮启动前另行冻结，不看分数挑公式。

## 5. 验收与 trace 隔离

Agent 仅获得 task.json 的自然请求、公开接口合同、初始文件与授权环境。`reference/`、private_verify.py、作者负例和评分绑定不进入 Agent workspace；私有程序在 Agent 进程树关闭后，由外部隔离验证器对只读交付目录运行，验证过程在自己的临时目录操作数据。Controller、Planner、Selector、Executor、Auditor 均不读取私有验收来选择动作或生成标签。

本轮允许对新作者开发题做参考自验和评分器隔离验证，不读取已有 Real Agent Holdout V2、封存来源/结果或 `acceptance_tests/`；最终 Holdout 仍只在最终验收使用一次，结果不用于返工。

保留每题完整 SQLite、model_states/checkpoint chain、state timeline、原始 model_trace/token IDs、event log、causal ledger 和评分/隔离输出，并散列所有当前工件。native `causal_ledger.input.prompt` 只是最后 delta，不能直接当完整训练输入；重建须识别 bootstrap、实际 State 重置/rollover/fork 与 stop 裁剪，不能盲拼 parent transcript。Selector 失败请求、case 硬退出造成的缺失必须单列，不能补造。

分析固定按 Planner → Controller eligibility → Selector → Executor → Harness → evidence → Auditor → 下一步/终止查首错，并排查全部成功/失败题及相关同类路径。非唯一可归因项记 `unattributed_failure`。架构、协议、状态注入或通用逻辑的缺陷先修根因，配先红后绿测试，不用训练 State、额外调用、外置 Head 或路径特判掩盖。

对比期间 rwkv_lh/、评分/parser/stop boundary、runner 和参数保持冻结。必要修复后原始结果保留并标 INVALID，两遍基线在新快照重跑；禁止只重算有利一臂或读取 confirmation 后改评分重打分。

## 6. 未来角色数据与训练权限

本次新 datasets 授权仅是项目开发评测集。未来角色数据仍只能从真实生产 trace 与当前共享 builder 抽取，逐行重算 100%；不能将本组作者 reference 或私有正确答案转为角色训练标签，不能恢复旧合成数据链。

未来 source manifest 需登记生产 run/trace SHA、抽取器 SHA、协议 SHA、project family 切分、UTF-8 byte 5-gram cosine 与 0.95 阈值、覆盖审计。每角色唯一冻结回归集，之后只新增 train；合法标签仅按现行规范 executed_fixture/planner_contract/human_double_review。`role_trace_dataset_v1.py` 尚未完成，不把静态可重建分析当作已有合法训练集。

训练次数按实际训练累计，任何角色禁止第 4 轮；Selector 已满 3 轮，Executor/Step Auditor 的 Round3 额度冲突仍待 owner 对账，Final Auditor 实际轮次须核实，Finalizer 无独立授权。新增开发题不重置训练次数，当前不启动训练。

## 7. 最终冻结项与汇报

开跑前由 root 补齐：12 题与执行顺序 SHA、私有程序 SHA/隔离验证、最终 dataset manifest/相似度审计、完整源码/runner/lock 指纹、每角色与 engine 身份、实际脱敏 config/argv、派生指标 collector SHA 和普通测试、freeze 时间与本文件及 METRIC_DEFINITIONS 的最终 SHA。未补齐项保持 PENDING，不能把当前脚本里的观察时 SHA 当最终运行版本。

每轮先汇报 Agent Strict / completed / mutation / 终止原因，再角色数字；附状态库统计、硬门、首错证据、未知/缺失字段与 SHA。完成后按 AGENTS 跑完整 tests/，全绿且无 Torch/State 跳过，再本地提交本轮 id；push 依据 owner 授权处理。当前文件不记录任何已经启动或完成的模型运行。
