# R3 本地 13.3B 双零开发基线预注册

本轮为 owner 于 2026-09-07 明确要求“那就换回 g1j-13.3，然后开始测”“之后强模型恢复了再说”后的新执行登记。按这一授权，使用当前本地 13.3B Planner 和 Stage Checker 运行已有 12 题，各独立执行 A、B 两遍 all-zero；已知模型输出合同、length 和 context 问题作为本轮观测，不再等待强模型上游恢复或要求额外生成探针。本文登记本轮执行纪律，不表示已经运行或通过能力门槛。

R1、R2 原始记录及冻结文件保持不变；R2 不与本轮拼臂。当前父提交为本地 `eb861256c8edf2e3f0361027a68ed0fc35cddcf5`；主代理已核对它相对 `90e08a58` 仅增加另一任务的审计数据，生产、测试、runner、依赖文件无变化。完整提交、源码、配置、依赖、评分与服务身份由 `FROZEN_EXECUTION_MANIFEST_R3.json` 最终绑定。正式冻结及模型执行由主代理完成，准备脚本不生成模型输出。

## 1. 固定范围与来源

题集为 `realprojectdevv1`，开发题来源是 owner 授权后按需求编写的项目基准，CLI、数据、HTTP API、维护、Web、全栈各 2 题，不是采集的真实用户 trace。任务、参考实现、私有评分和阈值均沿用 R2，不创建新 datasets，不使用 Ladder、E2E-90、Real Agent Holdout V2 或 `data/acceptance/`。

冻结题序为 RP-API-01、RP-API-02、RP-MAINT-01、RP-MAINT-02、RP-CLI-01、RP-CLI-02、RP-DATA-01、RP-DATA-02、RP-FULL-01、RP-FULL-02、RP-WEB-01、RP-WEB-02。每臂分母固定 12，题目各恰一次。A 写 `real_project_zero_a_r3/`，B 写 `real_project_zero_b_r3/`。禁止挑题重试、补考拼臂、缩小分母或把 R2 结果补入本轮。

Agent 仅获得公开自然需求和初始 workspace。reference、mutant、private_verify 不进入 Agent workspace；沿用私有黑盒验收、真实 Playwright 与 bubblewrap 对只读交付 snapshot 的隔离评分。任何题目通过均须由现有 Strict 评分确定；连接探针、作者 reference 自验和模型 JSON 可解析都不替代 Agent 成绩。

## 2. 固定执行配置

| 项目 | 本轮值 |
|---|---|
| Supervisor CLI / 策略 | openai / goal_stages，生产原生适配器 |
| Planner / Stage Checker | 同一 rwkv7-g1j-13.3b-zero-state-capability-ctx16384，http://127.0.0.1:29613/v1，远端 18234/v1 |
| Supervisor transport | 生产 vllm-rwkv-native / completions，当前 canonical builder 不改 |
| Planner / Stage Checker 输出预算 | 8192 / 2400 tokens，read timeout 240 秒 |
| Supervisor State / cache / fallback | 每次显式 zero / plan cache false / fallback 空 |
| Selector | rwkv7-g1j-2.9b-vllm-v1，127.0.0.1:29621，远端 18239，当前 v4 identity 和 decoder |
| Executor / Step Auditor / Finalizer / Final Auditor | 当前 13.3B，native_required，zero profile，zero SHA，request delivery |
| 角色输出预算 | Executor 1800，Step Auditor 400，Finalizer 1400，Final Auditor 400；不改其他角色预算 |
| 生成采样 | temperature 0.1 / top_p 1 / top_k 0 / presence 和 frequency penalty 0 / decay 0.996；Selector 保持原生 argmax |
| Controller | stateful-goal、independent-selector、progressive，max-transitions 200，concurrency 1 |
| 重试与 State | supervisor-pending-resume-attempts 0，禁止选择性补考；保留既有内部 transport retry/backoff 并冻结公开配置；跨题不复用 State |
| 物理 context | 16384；角色既有 safety margin/BOS 行为不变 |

Planner 不设固定步骤或阶段数量上限，任务完成由既有 RWKV 目标覆盖和执行证据判断；步骤数无限制不等于物理上下文无限。资源不足必须保留为阻塞或中断。Stage Checker 保持检查职责和 2400 输出预算，不截断输入或临时减预算绕过模型失败。

native wire 使用生产 System✿ / User✿ / Bot✿<think 包装，保留思考；原始输出的 `>` 接回实际发出的 `<think` 后仍须严格 JSON 解码及原合同校验。stop、token IDs、zero 标记、协议版本全部从生产模块/构造函数引用，脚本不发明协议字典。`.env` 与 `.env.local` 由生产 loader 只读加载；配置驱动仅在进程内显式覆盖本轮身份，不读取强模型候选文件，不修改 env 或输出密钥。

## 3. 已知观测与新授权

此前本地 Planner 一次真实完整请求自然 stop，JSON 语法通过，但生产首先因额外顶层 `goal_digest` 拒绝 GoalPlanPatch；完整原文另查发现 success_evidence 类型及其他字段合同问题。小 Stage Checker 连接 fixture 曾输出至 2400 length，被严格拒绝。19 步连接 fixture 的 15067 输入 + 2400 输出超过 16384，预检未生成。连接 fixture 的 accepted audits 是明确 mock，不能作为生产能力或训练证据。

强模型上游新复测中模型目录可用，但第一条完整 Planner Chat 请求 HTTP 500，按当时登记停止。这些记录见 `VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/REPORT.zh-CN.md` 和 `STRONG_UPSTREAM_STABILITY_R1_20260907/`；它们解释 owner 为何选择直接观测本地组合，不构成本轮分数预判。

上述缺陷不再阻止本轮启动，也不因 A 的质量门失败而取消 B。两臂期间不得为改善结果修改 parser、评分、stop、提示、角色预算、State、源码或参数。只有执行身份不一致、fatal 或缺题才使完整双臂可比性不成立；模型失败仍按现有流程照实记录。

## 4. 指标与硬门

机器定义 `METRIC_DEFINITIONS_R3.json` 的 metrics、aggregation、题序与 R2 完全一致；仅更新本轮身份及配置说明。只读 collector 从 results、导出 audit/model_trace 和 DB 文件 stat 派生；不打开 SQLite、不清理/VACUUM，不改评分。

先汇报 Agent Strict / 12、completed / 12、成功动作完整 before/after SHA 不同的 mutation 数及终止原因，再角色调用。operation_target_invalid 仅按唯一 causal event 的 protocol_rejection_recorded 且 error 以 `[operation_target_contract]` 开头计数，普通协议错误不混入。终止 reason 缺失为 unknown，只有 run_completed 按既有规则规范化 completed。缺事件、缺 DB、缺完整 digest、缺 model role 均不得填 0。

质量门仍为：每臂总 mutation > 0，operation-target invalid = 0，每题 DB 主文件 + 现存 WAL + SHM 的最终逻辑大小 ≤ 100,000,000 bytes，无 controller_slice_exhausted，goal_transition_budget_exhausted 不为 true。每题缺失度量门记 unknown。此为最终 SQLite 文件大小，不是峰值磁盘/RAM/VRAM。门失败保留完整基线事实，不能因此忽略低分题，也不进入训练或候选增益结论。

完整 12 题的 runner exit 2 表示存在失败题，仍保存为 COMPLETE_OBSERVATION。fatal、提前停止、结果缺题保持注册分母 12，未观测题为 unknown，不能把未运行当 0 分后声称完整基线，也不得选择性补跑。身份及源证据完整后比较两臂逐题 Strict 翻转、completed、mutation、终止分布与 `N=abs(Strict_A-Strict_B)`；unknown 不填 0，N=0 不证明确定性，不凭当前零基线自行设置候选增益新阈值。

## 5. 冻结、执行与分析

`temp/execute_frozen_real_project_baseline_r3_20260907.py --prepare` 只生成配置和准备登记，不生成模型输出；主代理审核后 `--freeze` 创建不可覆盖的执行清单。`--arm A`、`--arm B` 才调用现有 benchmark。正式指标使用清单 metric_argv 的显式 `--definitions`，比较使用清单 comparison_argv。

冻结范围继承 R2 并补充本开发题集实际文件：rwkv_lh、scripts、tests、pyproject/uv.lock、该开发 suite 的任务/评分、其 datasets 源、运行/采集/比较脚本、本预注册、指标定义、当前公开配置核验、完整依赖、远端 engine/source/模型/服务身份。README、HANDOFF 与一般计划文档可记录进度，不属于 immutable_files；两臂期间本地 HEAD 也不得改变，所以不能中途提交文档。

每臂前后核验冻结源码/评分/题集/配置/依赖及远端身份，完成记录明确这些证据和 12 题覆盖。远端仅通过已上传绝对路径 attestation 脚本核验完整文件清单和服务，不调用任何 Git；本地关联提交。远端权重完整 SHA 沿已有实测清单，并绑定 inode/size/mtime。只读身份一致不等于模型能力合格。

保留每题原始输出、token IDs、完整 checkpoint chain、audit、因果事件及评分工件；按 Planner → Controller → Selector → Executor → Harness → evidence → Auditor → 终止定位首错。未唯一归因记未知，不能把 causal_ledger 最后 delta 当完整训练输入。后续数据抽取需生产 full checkpoint chain、当前唯一 builder 和来源 SHA；本轮没有角色数据生成或训练授权，训练次数不重置。

结束后报告完整双臂事实、缺失/未知、限制与 SHA。若运行中必须修源码或评分，应保留旧结果标 INVALID，在新轮整体重跑两臂，不覆盖 R3 冻结。本文件不含后验模型成绩。
