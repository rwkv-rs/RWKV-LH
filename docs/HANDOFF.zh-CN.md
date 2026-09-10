# 当前交接

更新日期：2026-09-10。最新完整开发采集 [REALPROJECT R1](../data/experiments/REALPROJECT_HANDOFF_COLLECTION_R1_20260910/REPORT.zh-CN.md)：**Strict 0/12、completed 0/12、mutation 0、动作 0**；10 题 Planner 网关 HTTP 500，2 题 Executor 参数重试前 Native State 边界错误。另一次 [UltraData R4](../data/experiments/ULTRADATA_COLLECTION_R4_20260910/REPORT.zh-CN.md)：**Strict 0/3、completed 0/3、mutation 0、动作 1**。两轮全部结束并封存，optimizer steps 仍为 **0**。

## 当前整改与验证状态

[交接结构整改 R1](../data/experiments/ROLE_CHAIN_ROOT_REPAIR_R1_20260910/REPORT.zh-CN.md) 已提交 `82319f95`：原始需求贯穿 Executor / Step Auditor，参数拒绝由同一步的 Selector / Executor 接收，路径资格和执行权限共用参数合同，逻辑交接及事实提交与 Native 缓存物化分开。完整回归 1321 passed、0 skipped；随后真实采集暴露新的数值边界缺陷，因此不能将工程通过称作完整交接验收通过。

两道实际失败题中，首次生成后服务器 processed_token_count + 1 比返回 token 的完整历史长度多 2；后续 append 原样继承偏差。错误起点是把终止输出时捕获的 worker 当前 State 当作该输出对应的 State。原始数值证据见 REALPROJECT R1 `NATIVE_TOKEN_EVIDENCE_FAILURE.json`；该轮报告 SHA-256 `6bbd6c78a7a2333fa09482f68857834a73fa45b4c73aac4910186b65cfbe1cc4`。

当前 [数值边界整改 R2](../data/experiments/NATIVE_BOUNDARY_REPAIR_R2_20260910/REGISTRATION.json)：候选缓存仅从已核验父 State 与实际返回 token 物化后发布，采样工作区不直接作为交接 State；单次角色采样与确定性缓存工作分别计量。Native / Selector 共用 State profile loader；Supervisor 在协议解析前保留原始 SSE 行，缺少生成停止原因不再伪造 stop。完整测试 **1341 passed、0 skipped、231.41 秒**；新源码已上传并验证完整项目 / engine 清单，真实 GPU 停止符、重试与重启验证已通过，State 张量与精确前缀最大绝对差为 0。R2 已封存，尚无新 Agent 成绩。

[StateTune 入口整合 R2](../data/experiments/STATETUNE_DRIVER_INTEGRATION_R2_20260910/REPORT.zh-CN.md) 已接通生产 trace 数据冻结、State-only 优化器登记/导出、Selector 固定回归比较。专项 50 passed，完整回归 **1390 passed、0 skipped、225.13 秒**；源码已冻结上传。服务器系统包更新使 12 个共享库与旧清单不同；已核对 dpkg 更新及文件验证，数值兼容检查按新依赖重新登记，首次拒绝与复验分别留证；8 项全词表比较精确相等，1/17/128/16384 反向均通过。实际角色优化器尚未运行。

## 唯一架构与服务配置

产品入口 `rwkv-stateful-goal-loop.v7`，保持五个训练角色：Selector → Executor → Step Auditor → Finalizer → Final Auditor。各角色只使用唯一 builder：前三者 v6、Finalizer v2、Final Auditor v4。步骤未完成与参数失败留在当前步骤；计划调整必须有阶段或目标缺口依据。任务、阶段和步骤数量不设固定上限，资源耗尽只能中断或阻塞。详见 [链路契约](CONTROLLER_ROLE_LINK_CONTRACT.zh-CN.md) 和 [唯一规范](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)。

- Planner / Stage Checker：独立强模型 `deepseek-v4-pro`，唯一配置 `.env.local`，stream=true；本次切换预注册输出上限分别 32768 / 16384，读取预算 600 秒（本次已完成探针为 240 秒）。owner 已切换官方 `https://api.deepseek.com`，模型列表鉴权 HTTP 200，实际完整计划请求已通过，一次 HTTP 尝试、自然 stop、4 阶段 6 步，200.37 秒；此前第三方网关 `https://next-token.cc/v1` 多次返回 `new_api_error/do_request_failed`。不能据此推断模型生成了错误计划；UltraData R4 另有一次 HTTP 200 后流协议拒绝，旧轮未保留原始 SSE，具体事件原因仍未知。
- Selector：已部署 2.9B，GPU 2，`rwkv-lh-selector-current.service`，本地端口 29621。32 层、40×64 State 已通过既有至 16384 tokens 的 Native 前向与反向机制验证；优化器未运行。
- Executor / 两个 Auditor / Finalizer：13.3B，`rwkv-lh-native-current.service`，GPU 0，本地 29613 → 服务器 18234。独立角色 zero，不复用未验证的旧 State。
- 当前部署根 `/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910`；项目 131 文件 manifest SHA `d8952c5dab4248a93db339720f37dd4e7657fa175882e8fc23b5a1613b8241e6`，engine 6393 文件 manifest SHA `4327197e8305f2a79ed750128df4ec689df16e2bd234b438d634bbd9d7fa395d`。服务器没有使用 Git；当前服务仅导入上传的唯一项目实现。Native build 身份为 `f4160292923d32c2a7b4c029a6ae0442b8490a673d4eb424de977c613d3f7bf8`。

## StateTune 的真实进度与下一步

Owner 已授权逐角色推进并取消固定三轮上限，按预注册指标、预算和实际 optimizer steps 管理；授权持续有效，不重复询问。Agent 低分和后序角色未到达不构成首轮训练禁令。

当前角色是 Selector。UltraData R4 有 1 次交接 / 3 菜单求值，3 条自动候选均 train；REALPROJECT R1 有 2 次交接 / 6 菜单求值，6 条均待独立复核。两轮没有足够的 mutate / execute / missing-target 证据，尚未满足原预注册 30 条验证菜单、10 个不同边界及固定 train/dev/confirmation 非空条件。没有合格正式数据集，不把错误参数或协议通过直接标成正确工具选择。

R2 实际数值边界验收已封存；正式数据/训练/Selector 回归入口已接通并冻结。下一步使用官方 DeepSeek Planner 在当前源码上完成固定 3+12 题的新采集。当前角色来源和覆盖合格后执行已授权 StateTune；合格前序 State 固定后采集下一角色。不得为凑样本修改家族身份、降低门槛或合成角色场景。训练须记录模型/数据/训练器身份、初始化及输出 State、预算、实际 steps 和验收结果；历史次数未知保持 unknown。

已封存结果不续跑或重评分。Real Agent Holdout V2 保持隔离，未读取，仅最终验收一次使用。Owner 负责 push；本地已提交 R4 `70f5ae0a`、REALPROJECT R1 `f9a37498`，各轮完整 SHA 清单位于实验目录的 `EVIDENCE_SHA256.json`。

历史回查：UltraData R2/R3 可核对的 22 次已提交生成全部已存在 +2 token 偏移，另 9 次未证明；见 [历史审计](../data/experiments/NATIVE_BOUNDARY_HISTORY_AUDIT_R1_20260910/REPORT.zh-CN.md)。官方切换的请求、预算和脚本局限见 [DeepSeek 验证](../data/experiments/DEEPSEEK_OFFICIAL_PLANNER_R1_20260910/REPORT.zh-CN.md)。
