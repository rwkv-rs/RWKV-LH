# GoalPlanPatch 有界语义修复预登记

日期：2026-09-01。目标是在不改变角色、PlanPatch schema、数据集和评价口径的前提下，修复
Strong Planner correction 一次状态语义错误就中断 Goal Loop、导致 Stage Checker 不可达的问题。

## 固定改动范围

1. `GoalPlanRequest` 可携带一次 controller 生成的 `local_validation_repair`；材料仍在前，修复要求
   位于续写尾部。
2. Controller 对 Strong Planner 返回值执行现有完整 `RollingGoalPlan.apply_goal_patch()` 校验。
3. 首次 `TypeError/ValueError` 只登记拒绝，不提交 patch；把精确错误、当前合法 active plan 和可用时
   的 rejected patch 回传同一 Planner，最多重试一次。
4. 第二次仍失败才 yield，reason 固定为 `strong_planner_semantic_invalid`；Transport/HTTP/服务异常仍
   使用 `strong_planner_unavailable`，不得混淆。
5. 不新增模型角色、不让 RWKV 规划、不放宽 add/replace/discard 内核规则、不引入 State profile 或
   State Tuning。

## 固定验证

- Controller 回归：第一次 Planner 语义错误、第二次返回合法 patch 后，运行继续完成 step，并真实调用
  Strong Stage Checker。
- Controller 回归：两次语义错误后只产生 bounded yield，不记为 Planner unavailable。
- Supervisor 回归：repair payload 位于模型输入最后，包含精确 validator error。
- 现有 `tests/test_stateful_goal_loop.py` 与 `tests/test_supervisor_openai.py` 全文件通过。
- `git diff --check` 通过。

## 后续真实运行 gate

代码回归通过后，使用原 `RWKV-LH-AGENT-CAPABILITY-LADDER-V1` 的同一 5 例、同一参数和同一顺序运行
R5；不修改验收口径。记录：初始/repair Planner 调用数、semantic rejection 数、Stage Checker 调用数、
动作数、Agent/External/Strict 结果。R5 仍必须标注 V7 compatibility，直到 G1J V8 匹配 Head 存在。

成功不要求 5 例全部完成；本次单点修复 gate 是：至少一条原本由 invalid correction 直接中断的路径
能够提交 repaired patch，且不存在无限 Planner retry。模型或 Selector/Auditor 的后续独立错误必须原样
保留，不得为通过 gate 修改任务或判断标准。
