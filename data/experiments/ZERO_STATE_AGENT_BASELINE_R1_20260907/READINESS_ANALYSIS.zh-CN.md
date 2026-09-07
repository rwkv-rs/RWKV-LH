# Zero-State 基线准备与可见题集审计结论

日期：2026-09-07。轮次：`ZERO_STATE_AGENT_BASELINE_R1_20260907`。

Agent 级：本轮尚未运行模型基线，因此没有新增 Strict / completed / mutation / 终止原因结果；也没有可报告的角色增益。当前完成的是可见任务、公开验证器、生产 trace 源码和服务器环境审查，**不能声称 zero-state 基线已通过**。

## 1. 当前可以推进到哪里

owner 已确认推理服务器为 `rwkv-8222`。主代理正在清理旧服务与运行缓存并准备当前协议 zero-state 部署；引擎与当前 G1J 2.9B / 13.3B 模型保留，实际服务 attestation 尚需记录。旧协议服务存在、进程存活或端口可访问都不能证明当前五角色输入与源码身份一致。

`RUNTIME_READINESS.json` 是最初本地预检：默认 13.3B `localhost:29613` 不可用、Selector 旧 input 被当前 v4 拒绝、remote/launcher 没有配置。后续 owner 指明服务器解决了目标主机问题；该旧快照不代表清理部署后的状态。新的健康检查、源码/协议/模型/State/decoder SHA 和 all-zero 注入证明完成之前，预注册继续为 DRAFT/PENDING。

服务通过后，可先冻结当前 Ladder-10 双零，作为有限的小项目/接口闭环基线。要回答“创建项目、实现功能并检查交付”的全面能力，需要先补齐项目范围与真实行为验收设计；E2E-90 不能直接代替这一步。

## 2. 开发题集实际覆盖

审计仅基于开发可见 tasks 及其中的公开 verifier；未读取隐藏 acceptance、confirmation、Holdout 或封存内容，也未修改题集或评分。以下分类是能力范围审计，不是新的评分口径。

| 集合 | 可见主要任务 | 能支持的结论 |
|---|---|---|
| Ladder-10 | 5 个新建、4 个修复/扩展、1 个数据任务 | 小项目文件交付、局部接口、CLI、持久化和固定工作流的初始闭环回归 |
| Agentv1 | 网页记账项目 | 与 Ladder L4 Ledger 同一项目族，不能作为独立泛化项目或跨 split 独立样本 |
| E2E-90 | 2 个迷你项目补全、13 个修复/扩展、34 个多步工作流/故障场景、41 个孤立文件/工具任务 | 受控机制、工具使用与恢复诊断；从空仓库创建完整产品为 0 |

E2E-90 最接近项目交付的 E2E-LH12 与 E2E-H15 都已有模块 scaffold、需求和公开测试；其余 88 题不能称为 88 个真实项目。部分题公开完整 expected 工件或明确阶段、文件列表、返回码，这可用于机制开发诊断，但弱化了未知输入泛化、自主设计和规划的证据。

可见 E2E-LH09 明确要求 `mock_api`，当前生产 independent-selector 菜单没有该操作；runner 源码遇到该组合会拒绝。审计没有读取其隐藏 runner_control，不能声称确认了隐藏配置，但可见要求已足以证明“全 90 题直接适配当前生产”的前提不成立。保留原题集、评分和分母；不能为了运行成功删掉该题，也不能给生产模型临时补 fixture 特判后声称同一架构结果。

## 3. 公开验证器不能证明什么

Ladder 与 Agentv1 的公开验证器包含真实 Python 函数调用、CLI 子进程、JSON 持久化和 JavaScript 纯函数检查，对接口回归有价值。四道 Web 题没有启动浏览器，Node 明确使用 `global.document=undefined`，绕过真实 DOM、事件和用户交互。

CSS 字符数、关键词、固定 id、源码 token、URL 前缀不能代替浏览器操作和界面质量；公开 Packaging 检查也未实际构建 wheel、安装或验证安装后的入口。这些题不能单独证明网页可用性、HTTP 后端生命周期、数据库事务、认证授权、并发、大仓库交付或长程 Agent 行为。

L4 Ledger 与 Agentv1 账本同族，未来 train/dev/confirmation 必须按 family 隔离，不能靠两个 task id 视作独立项目。局部持久化软件通过测试，也不能反推 Agent 跨动作 WKV 状态保持能力。

## 4. 下一步范围与比较纪律

1. 完成当前服务部署及 attestation，显式登记各角色 zero 初态、模型与源码身份、固定参数和完整 trace 工件路径。
2. 冻结 Ladder-10 双零，遵守 mutation > 0、operation-target invalid = 0、单题状态库 ≤100 MB、无 controller_slice_exhausted 等既有硬门，记录全题结果和两遍翻转。尚未运行，不预判是否达标。
3. 新增真实项目开发题之前，明确项目族、用户功能目标、空仓库/已有仓库边界、依赖环境、运行方式、产物、浏览器/服务验收、异常恢复与安全范围，再冻结新题集身份。本报告不创建新 datasets，也不擅自改写现有任务或评分。
4. E2E-90 保持机制回归定位。当前 mock_api 适配冲突和规范中 90/90 完成要求必须在扩大运行前显式处理；不得悄悄替换题、删成 89 题、修改分母或通过运行后重评分改善结果。
5. 每个纳入比较的集合独立双零，冻结代码/题集/顺序/参数/评分。修生产源码后旧比较标 INVALID，两臂重跑；读取 confirmation 后不改 parser、stop boundary、评分再 rescore。

## 5. Trace 到 StateTune 的真实前提

当前 store 保留成功生成路径的完整 model_states、checkpoint 父链和原始事实，可以为后续抽取提供材料；但 `causal_ledger.requests[].input.prompt` 在 native 路径仅是最后一个 delta。直接拿它训练会丢失 bootstrap、workspace manifest、精确事实与实际 WKV 前缀，造成训练和生产输入不一致。

必须保存每题完整 SQLite store、state timeline、model trace、event log、causal ledger、原始 token IDs 和身份 SHA。未来抽取器按实际 State 生命周期重建完整 checkpoint chain，辨别 native delta 与 prompt_replay 完整串、rollover 重置点、fork 延续和 stop suffix 处理，再由当前唯一 builder+renderer 逐字节重算角色协议正文并绑定真实完整上下文。

Selector 失败请求可能未预先持久化，硬退出也可能丢失尚在内存的 JSON trace；这些缺失显式登记并排除，不能补造输入、响应或正确标签。静态“可重建”结论还未经过真实基线逐行验证。抽取器 `role_trace_dataset_v1.py` 尚未实现，当前没有可声称验收合格的新 StateTune 数据集。

标签来源仍限于 executed_fixture、planner_contract、human_double_review；覆盖、family split、相似度、逐行重算和固定回归集均按当前规范执行。分析先从 Planner → Controller → Selector → Executor → Harness → evidence → Auditor → 下一步/终止找首错，结构性缺陷先修根因，不把 StateTune 当作掩盖工具。

## 6. 训练权限与轮次

清理服务器、删除旧实验和更换协议不会重置实际训练次数。Selector 已满三轮；Executor / Step Auditor 的 Round3/replacement 等记录与“剩一轮”存在冲突，owner 对账前没有可自动使用额度；Final Auditor 最多三轮，实际已用次数需核实；Finalizer 未有独立训练授权。

先做当前协议兼容与已有 State 消融，证明某角色实际介入、解除可归因首错且带来超过双零噪声的 Agent 增益，再讨论有合法额度的残差训练。不能通过新版本、replacement 命名或 zero 初始化重新获得第四轮。本轮没有创建 datasets 版本或启动训练。

## 7. 可复核证据与 SHA-256

以下为本结论写入时已存在的审计工件；只读取和散列显式列出的当前实验文件，未读取封存材料。服务器清理与部署的最新证据由主代理在对应轮次登记，本报告不把盘点替代部署验收。

| 文件 | SHA-256 |
|---|---|
| `VISIBLE_PROJECT_TASK_INVENTORY.json` | `2432601b9386e8a1a5eda0e0dbad50500544360a3a98f431154de2ccbf418935` |
| `PROJECT_TASK_VERIFIER_AUDIT.zh-CN.md` | `edf6ef80671defae517754a42e9139e61ba0004201568eff720bf72498a331c5` |
| `E2E90_VISIBLE_TASK_CLASSIFICATION.json` | `e836e7dc4e2c6e67ce611340a5e69e09aa1359f114620ca7d443f3ec497c6cb6` |
| `E2E90_VISIBLE_TASK_AUDIT.zh-CN.md` | `1b71e95a978ec45d668e83ef4bc625dcf3e8fa45d4ec378b6d0fb2ff0ede2593` |
| `TRACE_READINESS.zh-CN.md` | `a48d552a9f15deb85f019eb0ba5b1fce1645cba54cfc0b5008219456ad2b6dca` |
| `RUNTIME_READINESS.json`（最初本地预检） | `31642b466cb44f1ee739f636d53a7d7332e4d328e9643194fa34be315bd233e5` |
