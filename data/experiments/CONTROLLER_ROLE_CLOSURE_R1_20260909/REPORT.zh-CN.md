# Controller 角色链路闭环整改

轮次：`CONTROLLER_ROLE_CLOSURE_R1_20260909`，日期：2026-09-09。

## Agent 与角色实测边界

最新生产模型成绩仍为历史 R7：A/B 各 Strict **0/12**、completed **0/12**、mutation **0**；各 12 次成功目录观察，终止 `strong_planner_unavailable` / `fixed_plan_exhausted`。本轮没有新增 Agent 成绩，不重评分旧运行，不读取最终 Holdout。

角色级历史仍为每臂 Selector 12 handoff / 36 菜单求值、Executor 12、Step Auditor 12；后续角色未到达。本轮测试使用显式 mock 模型与真实 Harness I/O，不能作为角色训练来源或能力百分比。训练 optimizer steps **0**。

## 根因与当前实现

| 全局问题 | 修复与上下游关系 | 回归证据 |
|---|---|---|
| Step Auditor 的缺口只留在日志/不透明 gap 编号中 | `role-feedback.v1` 从接受的审计 catalog 取原条件、范围、证据；同一步同一版本的 Selector 与 Executor 使用相同语义反馈 | `feedback_red.log` 原先失败；真实 Selector/Executor 输入差异及五角色重建测试 |
| Finalizer 重答看不到拒绝原因 | 回答缺口携带原候选与原条件进入唯一 Finalizer builder；自身格式错误单独保留 retry_feedback，不能覆盖语义缺口 | 原先两次输入相同；当前语义修复、协议重试及同时保留两份反馈均验证 |
| 审计协议错误释放边界，重复动作/重新生成答案 | 保留原动作/候选与审计边界，只向同一审计传递协议错误重试；达到原有资源预算阻塞 | Step 连续/恢复与 Final 同候选回归；1 次动作对应多次审计；预算不重规划 |
| 最终证据不足只触发 Finalizer 重答 | Final catalog 显式区分 answer/execution；execution 缺口携 accepted audit 与反馈进入现有 Planner patch；新执行步骤可观察/变更/检查补证 | 最终缺口→第二个 Planner 补丁→真实 readback→最终接受，连续与中断恢复一致 |
| Stage Checker 留下完整引用却只发最后 8 条动作，artifact/revision 引用丢失来源 | 去除阶段事实数量裁剪与 request 十二条限制；统一解析 action/artifact/revision 到生产动作；未知来源拒绝；审计工具声明也去除 8 条 evidence/gap 限制 | 同阶段 19 步对应 19 个动作事实；三种引用等价且不重复；缺失 producer 拒绝 |
| 后缀和有限目录发现被当成硬兼容判断 | 工具资格按文件/目录/缺失目标的结构前提；内容格式仅为提示，真实解析与编码结果留给 Harness；显式 root 全保留，有限发现/Selector 提示裁剪显式标记不完整 | 相同内容改名 .json/.data/无后缀；跨 256 项与显式 root 保留；目录/文件错误仍在执行前拒绝 |
| 旧计划协议和角色别名仍可进入当前链 | GoalPlanPatch 只收 v4，phase 必须显式；删除旧 flat/nested 重放、contract graph 投影、旧角色模块/字节码及旧临时生成入口；网络与 provenance 身份引用当前常量 | v1/v2/v3/未知版本拒绝；协议目录 inventory、唯一 builder、网络服务与来源绑定检查 |

上述是前轮链路报告中六类剩余断点及关联协议清理；不代表项目所有工程问题或所有任务能力均已解决。前轮已删除的工具/Executor/审计错误误转 Planner 三条分支保持回归。五角色和产品 Controller 架构未更换；未引入额外模型、Head、任务/路径/后缀特判。

当前协议：Selector v5、Executor v5、Step Auditor v4、Finalizer v2、Final Auditor v3。反馈是共享值合同及因果日志投影，不新增模型角色或完成权限。源码、协议、测试和过程文件 SHA 见 `MANIFEST.json`；删除项只记录路径/SHA，见 `DELETION_MANIFEST.json`。

## 验证记录

- 起始失败断言：feedback 6 failed；目录/改名/最终执行修复 5 failed / 1 passed；旧计划入口 4 failed / 1 passed；审计工具条数约束 2 failed。
- 全量初次有效结果：1056 passed / 2 failed；定位到旧 target-contract 常量与新版本被错列为负例，均修复；不是回避或跳过。
- 最终完整命令：`.venv/bin/python -m pytest -q tests/`，**1061 passed，0 skipped，194.99 秒**。Torch、State 与必需浏览器检查包含在内。
- `full_verified.log` SHA-256：`b8bdcc18e631acece252ba22bb9b197fe70f3746383d5995a176dfcae754bc9d`。
- 额外确认既有接受后恢复逻辑正确：审计结果落盘后进程丢失，恢复只提交原结果，不重新调用模型；这两项原本即通过，不冒称新修复。
- 一次完整尝试与一次定向尝试因我同时使用默认 basetemp 产生干扰，已明确 INVALID 并重跑，见 `VALIDATION_ATTEMPTS.json`。原始失败日志保留，不用于有效验收。
- 每次重建都从实际请求边界快照调用当前 builder，对照 checkpoint transcript/持久化 prompt SHA；五角色及 Finalizer 语义/协议同时存在的情形已覆盖。

## 仍需执行的已授权工作

2.9B 源权重存在，下一轮继续通用容器转换、完整上传身份核验、独立部署和 Native 训练后端形状/数值/梯度兼容验证。当前没有宣称 2.9B 服务已上线或正式训练已开始。

随后冻结新生产 trace，按 Selector→Executor→Step Auditor→Finalizer→Final Auditor 逐角色推进。只核验当前角色的数据来源、标签、覆盖、预注册预算与固定回归，不要求 Agent 先高分或后序角色先出现。当前生产能力、Planner 合同生成质量和后续编码/最终完成仍须新冻结运行实测；原 R7 不升级为本轮结果。E2E-LH09 的 mock_api 适配问题未由本轮验证关闭。
