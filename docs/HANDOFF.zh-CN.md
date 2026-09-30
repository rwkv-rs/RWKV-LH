# 第一轮：当前状态与下一步

当前入口为 `data/experiments/ROUND_01/`。本页报告已完成的当前能力复核，不沿用此前累计编号，也不合并旧批次成绩。原始调用身份、失败、产物和 SHA 保留本地；历史只查 Git。

## 当前验证结果

三类前端任务、两个新种子、六次固定预算运行：**Strict 0/6、completed 0/6、mutation 1、独立整体验收 0/6**。两次耗尽 40 次调用、四次耗尽 4096 token 输出额度。只有一份作品集生成 index.html，独立 Chromium **18/19，唯一失败项为缺 README**；其余五次没有入口。已证明能生成基础静态展示页，尚未证明稳定交付、自主完成或交互应用可用。

| 能力 | 当前证据 | 限制 |
|---|---|---|
| 静态展示页 | 实际桌面 1280×800、手机 390×844 可运行；三张作品卡片、具体技能、导航锚点及 mailto；无横向溢出和脚本错误 | 本次两次作品集运行仅一次写出页面，且遗漏 README |
| 看板与阅读清单 | 一次看板输出已进入 CRUD/localStorage 的 JavaScript，其他三次在 CSS 内重复 | 四次首次写入均截断，调用未闭合、文件未写入；没有可运行交互产物 |
| 自主验证与收尾 | 作品集主动绑定检查并执行三次验证 | 未修复 README；检查误判、重复验证及替换失败后耗尽预算 |

新作品集第 2 次调用写入页面、第 3 次就 submitted。强模型检查把四部分内容误限定为至少四个 `main section`，忽略介绍可以位于 header，独立审查仍接受了它。第 19–21 次 Decision 连续 verify，均得到该误判和真实的 README 缺失；第 22 次重新 bind_checks，后续 16 次提交因检查 ID、替换关系或失败证据不符被拒，未再执行修复。另一作品集首次改写受保护 TASK.md 被拒，随后 38 次读取同一失败回执。

四次交互输出要分开诊断：三次是明确 CSS 循环或不断增长的伪类链；一次是实际 JavaScript 尚未写完。输入约 4295–4346 token，低于 24576 上下文；不能把单次 4096 输出触顶说成上下文耗尽，也不能把所有截断都归为重复。

88 次预留、开始和返回一致：Decision49 / Executor7 / Planner32。56 次 Native 全部约束开启，22,329 个原 token 独立 Guidance 审计通过；52 次完整参数合法、4 次截断未测量，测得缺必填 0。32 次官方 DeepSeek beta strict 请求、36 个原始工具参数合法。格式拒绝 0、Planner 安装语义拒绝 16 分开统计；没有缺失客户端返回或未匹配服务生成。格式正确不等于动作、正文或交付正确。

当前报告：`data/experiments/ROUND_01/CAPABILITY_CHECK/REPORT.zh-CN.md`，SHA-256 `a37295cbe74db66a6722176d50115365bcad19398c2ebd1960c816aa532c866c`。同目录 `CALL_INDEX.zh-CN.md` 索引全部 88 次原文；`VERIFICATION_CONTRACT_FINDING.json` 记录内部检查误判，`SEMANTIC_GUARD_AUDIT.json` 记录安装拒绝，`CAPABILITY_OBSERVATIONS.json` 区分截断形态。

页面入口为该目录 `RUNS/SW-PORTFOLIO-01-on-20260931/AGENT/workspace/index.html`；`frontend-portfolio-original.zip` 是未补写的原项目，截图在 `PREVIEWS/new-portfolio/`。作品卡片只是介绍文案，不表示已实现摄影、书店或笔记应用。

源码、通用脚本与测试文件集合/SHA 完全相同，沿用完整本地回归 **2910 通过、0 跳过、722.10 秒**，没有重复计算成本或声称本次重新跑过。Torch/State/必需 Chromium 未绕过。该测试对象含既存 owner 未提交源码，与公开纯提交源码分开；公开源码另做干净构建和入口检查，CI 不能代替完整回归。

## 当前架构

完整目标→Decision 基于证据选择直接执行或强模型规划→Executor 持续执行与局部修正→独立检查→Decision 判断目标满足→完成门。原目标、模型设计与可执行检查分开；Controller 只校验权限、真实回执、State 身份和完成条件，不代选动作。

唯一当前协议：Ledger v10、Goal v1、Plan v5、Assignment v6、Planner v14/chat v3、Decision v17、Executor v13；prompt v7、输入传输 v2、格式适配 v6。Planner 只读批次保留原参数、顺序和逐条回执；同次输入完整相同文字可逐字共享。Native exact-token 预填充与真实清理生命周期已验证，旧 State 不静默复用。所有新 RWKV 实验约束开启；继续 G1j 分支。细节只在[架构](ARCHITECTURE.zh-CN.md)维护。

## 当前缺陷与下一步

1. **验证后的事实与交接。** 区分实现遗漏、检查缺陷和安装拒绝。goal_checks_bound 后 boundary 仍落到 task_direction、bind_checks 仍可选；首次增加 checks 改变完整 contract_digest，步骤摘要可能把已有执行显示为未做。修事实投影与替换证据关联，动作仍由 RWKV 选择；不能认定这一处解释了所有停滞。
2. **检查编写与审查质量。** 内部检查不应把内容要求变成额外 DOM 限制；缺 README 要保留为真实失败。外部 about_skills_content 目前只验非空，尚不足以证明具体技能说明。修复需先失败再通过回归，验收覆盖调整另行预注册，不重算当前成绩。
3. **重复与单次输出组织。** Decision 在已知失败后重复取证或验证；Executor 有 CSS 循环，也有实际代码过长。拆分写入能力与输出额度分别受控验证，不由 Controller 自动补文件、换动作或拼接截断 JSON。
4. **Planner 预算与预留。** 实际 chat+tools 计量需统一并前置本地输入检查；已知路径可能在未发 HTTP 前留下 pending。本次没有触发未返回请求，但该缺陷未修。保留真实已发 UNKNOWN；同次输入重复原文共享尚待覆盖结构化 chat。
5. **服务稳定性与训练来源。** 本次 strict 原参数通过不代表既有官方 schema 违例或 Native 非有限 State 问题已根治，首个非有限算子仍待定位。正式角色训练行/可准入候选仍为 0；Decision StateTune 需真实生产来源、独立纠错审查和固定隔离回归，开发题不直接转为训练数据。

先完成交接与检查质量回归，再以冻结题目、预算、阈值进行新受控运行；输出额度实验单独登记。收益看 Agent 交付、完成、重复和总成本。本次仅完成能力复核，生产修改0、训练0、新 datasets0、Holdout0、OA0、远端 Git0。

## 发布与资源

公开分支：`chase/g1j-agent-improvement-public`；只发布允许的当前源码和文档，不带本地实验材料或未发布研发祖先，不改 main。源码发布边界见[发布规范](SOURCE_DISTRIBUTION.zh-CN.md)。

两个专用 Native 服务和隧道已停止，无待核实 UNKNOWN。当前复核目录保留 `SHUTDOWN.json`、源码清单与逐调用审计；文档提交和公开发布身份分别登记为 `COMMIT.json`、`PUBLICATION.json`，构建及 CI 记录与完整本地回归分开。
