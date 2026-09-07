# StateTune 数据管线源码、现状与项目经验

更新日期：2026-09-07。文档轮次：`STATETUNE_PIPELINE_STATUS_R1_20260907`。

本轮 Agent 级 Strict、completed、mutation 数及终止原因均无新增测量；角色级也无新增训练或评测指标。本轮只核实并整理已有源码与报告，没有运行训练、生成角色数据集或执行最终验收。

## 1. 当前结论

**当前工作树没有可直接执行的五角色 StateTune 数据生成管线。** 旧合成生成器、组装和角色评测链已删除；规划中的生产 trace 抽取模块 `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py` 尚未实现。现在已有共享协议构造器和生产运行记录基础，尚未形成经过逐行重建、标签审查、切分及覆盖验收的数据产出链。

这一区分已在 [协议与旧数据链清理结论](../data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROUND_ANALYSIS.zh-CN.md) 和 [统一规范 §2.1](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md#21-唯一未来流水线) 中明确登记。本页整理当前状态；执行顺序、权限和最新运行状态以 [统一规范](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md) 与 [HANDOFF](HANDOFF.zh-CN.md) 为准。

| 组成部分 | 当前状态 | 可核查位置 |
|---|---|---|
| 旧合成角色数据生成、组装与评测入口 | 已从工作树删除，不保留兼容入口、本地归档或 stub | [清理报告](../data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROUND_ANALYSIS.zh-CN.md) |
| 当前五角色输入协议 | 已有唯一模块和共享 `build_prompt_source()` | 下表及 [角色构造器分析](../data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROLE_BUILDERS_ANALYSIS.zh-CN.md) |
| 生产运行事实、checkpoint 与 State 链 | 已有持久化与导出基础；失败请求存在记录缺口，尚未完成实际数据逐行重建验收 | [trace 可用性审查](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/TRACE_READINESS.zh-CN.md) |
| 当前协议下的角色 trace 抽取器 | 尚未实现 | [统一规范 §2.1](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md#21-唯一未来流水线) |
| 当前五角色固定回归集及新角色训练数据版本 | 尚待合法生产 trace、抽取器和 owner 对应确认，不能视为现成可用 | [HANDOFF 后续顺序](HANDOFF.zh-CN.md)、[统一规范 §2.2](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md#22-固定回归集与权限) |

## 2. 已有的代码基础

五个角色均已统一生产输入构造入口。后续数据抽取与评测必须复用这些入口，不能在脚本中另外手写协议字典。

| 角色 | 当前协议模块 | 输入入口 |
|---|---|---|
| Selector | [selector_intent_v4.py](../rwkv_lh/goal_state_protocols/selector_intent_v4.py) | `build_prompt_source()`，进度由 `build_current_progress()` 构造 |
| Executor | [executor_args_v4.py](../rwkv_lh/goal_state_protocols/executor_args_v4.py) | `build_prompt_source()` |
| Step Auditor | [auditor_step_v3.py](../rwkv_lh/goal_state_protocols/auditor_step_v3.py) | `build_prompt_source()` |
| Finalizer | [finalizer_answer.py](../rwkv_lh/goal_state_protocols/finalizer_answer.py) | `build_prompt_source()` |
| Final Auditor | [auditor_final.py](../rwkv_lh/goal_state_protocols/auditor_final.py) | `build_prompt_source()` |

[LongHorizonStore](../rwkv_lh/store.py) 提供运行状态保存和 checkpoint 查询；[模型会话](../rwkv_lh/model_session.py) 管理 bootstrap、append、generate、rollover 与 fork；[benchmark runner](../scripts/run_rwkv_e2e_benchmark.py) 保留 SQLite 并导出 model trace、event log、state timeline 和 causal ledger。这些是未来抽取器的来源基础，不能把“已有日志”直接等同于“已有训练数据”。

现有 [trace 可用性审查](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/TRACE_READINESS.zh-CN.md) 基于成功调用路径的源码分析，尚未用合法基线逐行重算验证所有样本。native Selector 的失败请求和异常硬退出等情况可能缺少完整输入或输出，必须显式登记并排除，不能补造记录。

### 2.1 GitHub 中已保存的历史生成管线源码

旧版五角色 G1J v1 生成管线源码保存在提交 `3f23a6a6fe3e048e3142f43aae4938f92ea5db2c`，可以直接从 GitHub 阅读。以下入口、核心实现、旧协议模块与 tokenizer 共 15 个源文件已逐一通过 GitHub API 核对文件存在、大小及 Git blob OID，均与本地历史一致；SHA-256 和核查记录见 [HISTORICAL_GITHUB_SOURCES.json](../data/experiments/STATETUNE_PIPELINE_STATUS_R1_20260907/HISTORICAL_GITHUB_SOURCES.json)。它们已经存于远端历史，本轮增加完整源码导航，不把旧生成链恢复为当前生产入口。

| 历史组件 | GitHub 源码 | 职责 |
|---|---|---|
| Selector 数据入口 | [generate_g1j_selector_intent_state_tuning_v1.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/scripts/generate_g1j_selector_intent_state_tuning_v1.py) | 调用共享生成器并指定 Selector 角色 |
| Executor 数据入口 | [generate_g1j_executor_args_state_tuning_v1.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/scripts/generate_g1j_executor_args_state_tuning_v1.py) | 指定 Executor 角色 |
| Step Auditor 数据入口 | [generate_g1j_auditor_step_state_tuning_v1.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/scripts/generate_g1j_auditor_step_state_tuning_v1.py) | 指定步骤审计角色 |
| Finalizer 数据入口 | [generate_g1j_finalizer_answer_state_tuning_v1.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/scripts/generate_g1j_finalizer_answer_state_tuning_v1.py) | 指定最终回答角色 |
| Final Auditor 数据入口 | [generate_g1j_auditor_final_state_tuning_v1.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/scripts/generate_g1j_auditor_final_state_tuning_v1.py) | 指定最终审计角色 |
| 共享数据生成与验证实现 | [dataset_contract.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/rwkv_lh/goal_state_protocols/dataset_contract.py) | family 切分、相似度检查、prompt/target 构造、token 核算、manifest 和已有产物校验 |
| 标签与语义验证 | [dataset_verifiers.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/rwkv_lh/goal_state_protocols/dataset_verifiers.py) | 历史 fixture、角色语义与执行验证 |
| 来源登记生成 | [freeze_g1j_state_tuning_source_registries_v1.py](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/scripts/freeze_g1j_state_tuning_source_registries_v1.py) | 构造和冻结历史来源登记，包含合成逻辑，不是当前要求的生产 trace 抽取器 |

五个入口各自只是调用 `generator_main()` 的短脚本。阅读或核对历史实现时还需要同一提交的 [协议目录](https://github.com/rwkv-rs/RWKV-LH/tree/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/rwkv_lh/goal_state_protocols)、[tokenizer](https://github.com/rwkv-rs/RWKV-LH/blob/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c/rwkv_lh/tokenizer.py) 及其词表、Harness、schema、retrieval 和网络协议依赖；完整版本可从 [同提交源码树](https://github.com/rwkv-rs/RWKV-LH/tree/3f23a6a6fe3e048e3142f43aae4938f92ea5db2c) 查看。本轮仅核查源码可访问性，没有执行旧链、读取旧数据或证明其现在能端到端运行；旧协议与来源规则不能用于当前训练。

**较新旧脚本仍有源码保存缺口。** [旧入口删除清单](../data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/LEGACY_ROLE_ENTRYPOINT_REMOVAL_MANIFEST.json) 中的 10 个入口，包括 Executor v4/v5/v6、Step Auditor v3/v4、Final Auditor v2/v3 及组装/验证脚本，在本次已抓取的全部本地可达 Git refs 中按原路径未找到源码历史。当前有路径、大小与 SHA，不能据此声称这些版本的源码也已上传；其他位置是否有副本未确认。删除清单只能证明身份，不能恢复文件内容，清理前必须确认源码已提交且可从远端取回。

## 3. 下一条数据管线应如何工作

以下是 [已登记的实现要求](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md#21-唯一未来流水线)，不是已完成能力：

1. **先取得合格生产运行。** 按最新 HANDOFF 冻结源码、服务身份、题集、参数和门槛，以全新 workspace/State 完整运行授权开发范围的两遍 all-zero。先修复上游阻断并满足基线硬门，再进入数据阶段。
2. **保留完整源工件。** 保存每题 SQLite、model states/checkpoint 链、state timeline、原始请求与响应/token IDs，以及源码、协议、模型、State、decoder 和参数身份。缺输入、缺输出或无法重建的边界明确排除。
3. **按实际因果边界重建输入。** 遍历 `causal_order`，只使用当时之前的 durable facts；通过所属角色 builder 重算协议正文，并绑定实际 transport、bootstrap、初始 State、rollover/fork 与 stop suffix。native ledger 的最后 delta 不能直接充当完整训练输入。
4. **只接受有权威依据的标签。** `executed_fixture` 要求真实成功且推进至少一个 missing root；`planner_contract` 要求计划合同只有一个 eligible 操作；`human_double_review` 仅用于有记录的失败恢复正例。失败动作作为下一帧负例上下文，没有合法替代标签则丢弃。
5. **固定切分与覆盖审计。** 按 project family 切分 train/dev/confirmation，同 family 不跨 split；固定 UTF-8 byte 5-gram cosine 和 0.95 阈值。检查 failed last_action、非空 error_type、directory target、`.py`/`.json`/目录 root、mutate、execute 和 missing target；任一规定覆盖为 0，数据集无效。
6. **完成逐行验证及 manifest 后冻结。** manifest 记录源 run、源 trace SHA、抽取脚本与协议模块 SHA、切分与相似度参数、覆盖结果和逐行重算通过数。每角色首次合法 trace 冻结一份不变的 dev/confirmation，以后候选只新增 train。新角色数据版本与训练仍需对应 owner 书面确认。

owner 已授权的 `realprojectdevv1` 是按需求编写的 12 题开发基准，不能称为采集的真实用户 trace，也不能把作者参考实现直接转成角色训练样本。角色数据仍须来自生产 Harness 的实际执行，并满足上述重建与标签条件；详见 [开发基准来源边界](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md#23-owner-授权的项目开发基准)。

## 4. 已有证据支持的六条经验

### 4.1 输入协议必须只有一个权威来源

已发现的问题是角色输入曾在协议、生产调用方、测试与身份校验中分别构造或硬编码，Executor 还存在绕过当前协议的并行路径。清理轮统一了五角色 builder、renderer 与身份常量，并留下先失败后通过的回归记录。后续生成数据必须调用同一构造入口，否则训练和实际运行可能接收不同输入。证据见 [清理根因与整改](../data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROUND_ANALYSIS.zh-CN.md) 和 [角色构造器验证](../data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROLE_BUILDERS_ANALYSIS.zh-CN.md)。

### 4.2 StateTune 的上下文包含真实 State 生命周期

源码审查确认 native checkpoint 的 transcript 可能只是 suffix，ledger 却将它导出为 `input.prompt`；角色 renderer 正文也不包含全部 session bootstrap。只拿最后 prompt 或盲目拼接 parent transcript 都可能改变 WKV 上下文，因为 rollover 会从 fresh State 重建并保留历史 parent。抽取器需要恢复实际重置点、fork 延续、原始 token IDs 与 stop 边界。这个风险已经识别，但完整重建器尚未实现，见 [trace 缺口 1、3、5](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/TRACE_READINESS.zh-CN.md)。

### 4.3 日志完整性和标签合法性要逐条证明

已识别 native Selector 某些失败请求在成功响应前没有完整持久化输入，benchmark JSON trace 也可能在硬退出时丢失尚未写出的记录。因此不能根据已有字段补猜缺失响应，更不能自行发明“正确动作”。排除规则已有审查依据；标签权威、family 切分、覆盖审计和 manifest 是后续管线必须实现的质量门。见 [失败记录缺口](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/TRACE_READINESS.zh-CN.md) 与 [数据要求](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md#21-唯一未来流水线)。

### 4.4 上游没有正常执行，低分就不能归因于角色能力

历史 R2 A 的 Agent 结果为 Strict **0/12**、completed **0/12**、mutation **0**；12 题均终止于 `strong_planner_unavailable`，11 题没有 RWKV generation。这证明该次运行主要受 Planner 请求链阻断，不能作为纯 RWKV 能力基线或 StateTune 来源，也不能靠对未调用角色训练来解释修复。该记录不是本轮新增成绩，见 [R2 A 原始报告](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/R2_A_RUN_REPORT.zh-CN.md)。

### 4.5 测试通过与角色分数不能替代 Agent 增益

协议清理轮的完整回归为 **666 passed、0 skipped**，但没有运行真实 Agent benchmark，报告明确不据此声称能力提升。项目据此区分代码正确性、角色门与 Agent 门：候选须在固定回归集、同代码同参数下对照 zero，再用 Agent 结果和消融验证收益。双零噪声、confirmation 不回调评分、改代码两臂重跑等是比较要求，当前没有合格的双零结果可据此报告训练增益。见 [清理结论边界](../data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/ROUND_ANALYSIS.zh-CN.md)、[比较纪律与验收门](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md#3-迭代顺序与比较纪律)。

### 4.6 训练轮次必须对应实际执行身份

本地历史对账找到了旧 G1i 的 27 个 WKV 训练族的已提交盘点，但未补齐当前 G1J 各角色逐 run 的完成证据，不能把两个模型阶段的数字直接相加，也不能借换版本、replacement 命名或 zero 初始化重置累计次数。Selector 已满三轮；Executor/Step Auditor 的 Round3 与“剩一轮”冲突待 owner 对账；Final Auditor“最多三轮”不表示还剩三轮；Finalizer 没有独立训练授权。实际计数应绑定模型、run、日志、更新 step、初始化/输出 State、数据 manifest 与训练器 SHA，见 [训练轮次对账报告](../data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/TRAINING_ROUND_ACCOUNTING_REVIEW.zh-CN.md)。

## 5. 当前可执行的后续顺序

按最新 HANDOFF，先完成当前 Planner/Stage Checker 接入及源码身份核验，重新冻结并取得合格的项目开发集双零；达标后实现生产 trace 抽取器，再经 owner 确认冻结角色回归集。只有发现可归因、可通过对应角色 State 解除的残差，且完成训练轮次对账并获得对应书面授权，才能进入训练。

本页更新不会恢复旧生成器、创建新角色数据版本或授予训练额度。最终 Holdout 仍只在最终验收运行一次，不能作为数据生成来源或返工依据。
