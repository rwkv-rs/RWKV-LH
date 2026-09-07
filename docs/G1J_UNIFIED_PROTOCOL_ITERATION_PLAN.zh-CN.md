# G1J 分角色 Agent：唯一协议、数据来源与验收规范

更新日期：2026-09-07。适用于生产运行、未来生产 trace 数据抽取、评测和测试。与 HANDOFF 冲突时以本规范为准；owner 最新指令优先。

## 1. 唯一协议

每个角色只保留一个协议模块，拥有唯一 `build_prompt_source()` 和 renderer。嵌套的机械进度、目标合同和 gap catalog 也必须调用同模块共享函数。生产、数据抽取和验收不得自行拼接协议字典或保留兼容输入链。

| 角色 | 唯一模块 | schema 后缀 | 构造与渲染 |
|---|---|---|---|
| Selector 2.9B | `selector_intent_v4.py` | selector-intent.v4 | `build_current_progress()` → `build_prompt_source()` → `render_prompt()` |
| Executor 13.3B | `executor_args_v4.py` | executor-args.v4 | `build_target_contract()` / `build_execution_state()` → `build_prompt_source()` → `render_generation_prompt()` |
| Step Auditor 13.3B | `auditor_step_v3.py` | auditor-step.v3 | `build_prompt_source()`（内建 gap catalog）→ `render_prompt()` |
| Finalizer 13.3B | `finalizer_answer.py` | finalizer-answer.v1 | `build_prompt_source()` → `render_prompt()` |
| Final Auditor 13.3B | `auditor_final.py` | auditor-final.v2 | `build_prompt_source()`（内建 gap catalog）→ `render_prompt()` |

模块均位于 `rwkv_lh/goal_state_protocols/`。schema 完整前缀为 `rwkv-lh.g1j-per-stage-state-tuning.`，运行时引用模块的 `INPUT_SCHEMA_VERSION`，不得在调用方拼出身份标签。Executor `render_prompt()` 是相同输入的前缀正文，`render_generation_prompt()` 仅追加同一调用边界，不是另一套输入协议。

角色协议目录不保留旧模块或 identity stub。旧版、未知 schema 和旧独立 Executor 披露/重试格式一律拒绝；历史只能查 Git / GitHub。升级前删除旧模块及其可执行字节码，不允许 vN/vN+1 并存。

### 1.1 Selector 输入

current_progress 精确字段与顺序：

```text
assigned_action_count, successful_action_count, failed_action_count,
last_action, missing_read_roots, missing_write_roots,
workspace_targets, completion_preconditions_satisfied
```

last_action 精确字段与顺序：

```text
operation, status, arguments, error_type, error_message,
result_metadata, observed_roots, mutated_roots
```

- arguments 最多 8 个键，每值最多 160 字符；结构化值仅保留 object/array 大小描述。
- 失败时 error_type/error_message 必填，message 最多 240 字符；成功时为 null。失败不覆盖 observed/mutated root。
- metadata 白名单按顺序为 outcome_type、exit_code、target_kind、entry_count、match_count、byte_count、size_bytes、truncated、changed_path_count。
- workspace_targets 最多 32 条；类型取 `operation_contracts.WORKSPACE_TARGET_KINDS`。
- 网络封装 NetworkSelectorInput 使用 v5，只接受角色 v4。endpoint、menu/role/prompt/target prefix 全部引用角色模块常量。decoder manifest 与运行 attestation 必须匹配当前源码。

### 1.2 强制一致性检查

1. 协议 identity 测试必须枚举目录中的所有角色协议，恰好只有表中五个模块；仅检查一个手工列表的常量不算覆盖。
2. 生产角色输入、单元测试、未来数据抽取只能用共享 builder。scripts/、tests/、temp/ 不得手写 current_progress / execution_state / gap_catalog 等协议结构；负例从有效 builder 结果定点修改。
3. 生产、脚本、测试不导入 temp Python 模块，不依赖旧生成器或旧数据；旧源码与字节码都不得残留为可执行入口。
4. 每行数据的 prompt 必须能由该行绑定的 durable action / boundary 事实通过当前 builder+renderer 逐字节重算；不一致整批拒绝。
5. 运行身份绑定模型、State、协议与 decoder 源码 SHA；引用当前常量，不能只校验同名字符串。

## 2. 数据来源与清理规则

旧合成角色数据链已删除，不保留本地归档或 stub，也不得恢复旧生成器以继续训练。旧实验只查 Git / GitHub；当前工作树只保存当前有效数据、隔离验收材料和本轮及后续证据。

### 2.1 唯一未来流水线

固定模块名 `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py`，当前尚未实现。它必须遵循：

1. 使用生产 Harness + all-zero 在已冻结的开发范围运行并落盘 LongHorizonStore；可包含 Ladder-10、owner 授权的 `realprojectdevv1` 及已确认生产适配的机制回归。E2E-90 的 LH09 `mock_api` 冲突必须显式处理，不得静默删题；不得读取 Holdout。
2. 遍历 causal_order，以各 assignment / audit boundary 当时之前的 durable facts 重建输入。Selector 调用 build_current_progress；Executor 使用持久化 execution state 及同一 builder；Auditor 从边界证据重建 catalog。保存完整 SQLite、model_states/checkpoint chain、state timeline 和原始 token IDs；native causal_ledger 的 input.prompt 只含最后 delta，不能当完整训练输入。按实际 transport、bootstrap、State 初始化、rollover/fork 与 stop suffix 处理重建完整上下文，再证明唯一 builder 生成的协议正文与该上下文绑定；缺失请求/响应明确排除，不补造事实。
3. 标签权威只允许 executed_fixture、planner_contract、human_double_review。前者必须真实成功且推进至少一个 missing root；第二种要求计划合同只允许一个 eligible 操作；双人复核仅用于失败恢复正例并记录数量。失败动作只作为下一帧负例上下文，没有合法替代标签则丢弃。
4. 按 project family 切分 train/dev/confirmation，同 family 不跨 split；固定 UTF-8 byte 5-gram cosine，阈值 0.95；算法和参数写入 manifest 后不得更改。
5. 训练前覆盖审计包括 failed last_action、非空 error_type、directory target、.py/.json/目录 root、mutate、execute、missing target；任一覆盖为 0 数据集无效。
6. manifest 必须记录源 run id、源 trace SHA、抽取脚本 SHA、协议模块 SHA、切分算法、相似度参数、覆盖审计、逐行重算通过数。

### 2.2 固定回归集与权限

每角色从首次合法 all-zero trace 冻结一份 `rwkv_lh_g1j_<role>_regression_v1` dev/confirmation；以后每轮只新增 train，回归集不变。未经 owner 书面确认，不启动训练、不新建 data/datasets/ 版本目录。

角色轮次按实际训练累计，任何角色不得第 4 轮；换版本或 replacement 不重置。Selector 已满 3 轮。Executor / Step Auditor 旧“各剩 1 轮”声明与 Round3 登记冲突，在 owner 对账前不允许自动消耗所谓剩余额度。Final Auditor 最多 3 轮。

### 2.3 Owner 授权的项目开发基准

2026-09-07 owner 授权新增 `data/datasets/rwkv_lh_real_project_dev_v1/`，运行器标识 `realprojectdevv1`，共 12 题：CLI、数据流水线、HTTP API、已有项目维护、Web、全栈各 2 题。来源必须记为 owner-authorized authored development benchmark，即按需求编写的开发任务，不得称作采集的真实用户 trace。此授权限定该开发基准及配套验证，不变更角色训练轮次或自动批准角色数据集版本。

公开任务描述功能、环境、接口与交付合同，只向 Agent 提供登记的初始 workspace。私有黑盒验收、作者 reference/mutant 和完整期望值不得进入 Agent workspace；最终行为验证在隔离进程内读取只读 snapshot。Web/全栈使用实际 Playwright 点击、输入、刷新、键盘与状态/服务行为，不能以 CSS 长度、关键词、源码 token 或 URL 前缀替代功能验收。其他任务通过真实 CLI、HTTP、数据、数据库、重启与失败恢复检查。

冻结前必须逐题确认参考实现通过、登记的语义错误变异被拒绝、公开合同与私有验证一致，并完成整体隔离检查。作者自验不是 Agent 基线，作者参考实现也不是合法 StateTune 样本；后续角色数据仍必须来自生产 Harness 实际运行 trace，并满足 §2.1 的来源和逐字节重建要求。

新套件保留 12 题完整分母，代码/题集/评分/参数/比较门槛在模型运行前冻结；不能读过结果后改题、删失败题或改验收再重评分。既有 Ladder-10 和 E2E-90 的身份及评分保持原样。可见审计显示 E2E-90 只有 2 个带脚手架的迷你项目，另有 13 修复、34 工作流、41 孤立任务，不能等同 90 个从零真实项目；Ladder 的 Web 公开验证器原先没有浏览器，项目级行为证据需要独立建立。

## 3. 迭代顺序与比较纪律

1. 唯一协议、旧链清理、新开发题整体隔离验收及完整单元回归；使用 `uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev` 和 `.venv/bin/python -m playwright install chromium` 准备环境；Torch / State 注入及必需浏览器验证不得跳过。
2. 当前服务 identity attestation 后，固定代码/题集/参数 all-zero 两遍 Ladder-10。要求 mutation > 0、operation-target invalid = 0、每题状态库不超过 100 MB、无 controller_slice_exhausted。两遍 Strict 差为噪声带；不达标修根因，禁止进入训练。
3. 实现生产 trace 抽取并在 owner 确认后冻结回归集。
4. 当前 State 同代码做 2⁴ 消融，或至少 all-zero/全开/四个单开；增益必须超过噪声带。
5. 只有有可归因残差、尚有合法轮次且 owner 书面确认时才训练。
6. Agent 回归先检查 Ladder-10 硬门，再按冻结的 `realprojectdevv1` 开发范围双零及候选比较，随后扩大边界/异常/恢复/安全和已确认适配的机制回归。每个集合独立报告分母、噪声带与逐题翻转；新项目分数不替代既有 E2E-90 结果。
7. 最终一次 Holdout；结果只报告，不用于返工。

对照两臂之间不得修改 rwkv_lh/；修改后两臂都重跑，旧比较标 INVALID。题集、参数、阈值、相似度算法预先冻结，运行后不得调整。读取 confirmation 后不修改评分/parser/stop boundary 并 rescore；发现缺陷记录后进入下一轮。单次 Strict 约 ±3 的波动不能直接作为改善，必须对照实际双零噪声带。

## 4. 验收门

角色门仅是 Agent 实验门票：同输入同参数，核心指标双跑最差值严格高于 zero 双跑最好值；结构、schema、operation preservation、路径安全、false-continue 不退化。跨分布回归只用符合当前输入合同的冻结集合；退役数据不能为此恢复重放，旧分布需从合法生产事实重新建立并登记等价覆盖。

Agent 门：Ladder-10 Strict 严格高于 all-zero 且超过噪声带，zero 已过题不回归，协议拒绝/安全失败不增加；本地编码题均有 mutation 与 check/run 证据；合法到达 final 或 blocked，不能靠预算耗尽。E2E-90 Strict 不低于 zero、FN ≤ 1、90/90 完成。并列取更少 State，每个保留 State 必须有去掉即掉分的消融证据。

上述 E2E-90 门槛不因新增项目集而降低；LH09 当前生产适配冲突属于待解决事项，不能把它包装为已完成全面基线。`realprojectdevv1` 的具体比较指标与阈值另在模型运行前预注册，必须包含全部 12 题、Agent 完成/变更/终止原因及真实行为验收，并与自身同代码双零比较。

最终完成条件见 AGENTS §7 的全部八条，另需协议目录/构造一致性检查通过、数据逐行重算 100%、从基线到最终组合每步都有两臂同代码 trace。

## 5. 分析、报告与提交

每轮按 Planner → Controller eligibility → Selector → Executor → Harness → evidence → Auditor → 下一步/终止定位首错；只有冻结合同、真实事实或安全边界可证明的偏离才能归因，不唯一记 unattributed_failure。记录首错后的放大链、逐题翻转矩阵、候选是否实际介入，以及动作/mutation/check-run/invalid/终止原因/状态库大小/分角色调用数。

对可归因首错用同输入只换一个角色 State 做反事实；能解除首错才有资格进入合法下一轮训练。不得靠外置 Head、额外调用或用例特判掩盖 RWKV 能力。

汇报先 Agent 级 Strict / completed / mutation / 终止原因，再角色数字。清理轮未跑 Agent 时明确无新指标。每轮过程、红绿回归和源码 SHA 保存于 data/experiments，完成后本地 git commit，提交信息含轮次 id；owner 负责 push。

## 6. 当前执行状态

上一轮已统一五角色 builder 并删除旧协议与数据链。本轮 owner 确认服务器 `rwkv-8222` 后执行旧资源清理与当前源码部署准备，同时授权并编写 12 题项目开发基准；完整隔离验收和本轮 pytest 最终结果仍以本轮记录为准。当前 Strong Planner 和 Strong Stage Checker 均配置为 `gpt-5.6-sol`，服务/协议身份须以当前 attestation 证明。

尚无本轮模型 Strict / completed / mutation / 终止原因结果，没有启动角色训练或读取 Holdout。服务器清理记录见 `data/experiments/SERVER_RUNTIME_CLEANUP_R1_20260907/`，基线准备与题集审查见 `data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/`；新增开发任务与作者自验不能被称为真实用户 trace 或 Agent 能力提升。
