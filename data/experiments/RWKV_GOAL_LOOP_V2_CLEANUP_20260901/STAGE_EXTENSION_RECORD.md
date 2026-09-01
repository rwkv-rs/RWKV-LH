# 嵌套阶段与阶段检查扩展记录

日期：2026-09-01

该扩展由用户在原角色隔离整改开始后追加，因此不伪装成原 `PREREGISTRATION.md` 的预注册项目。它不修改数据、阈值、标签或相似度口径，只增加确定性协议与回归测试。

## 追加要求

- Planner JSON 按阶段嵌套，阶段内步骤同级；
- 同阶段安全步骤未来可并发；
- 阶段完成后使用强模型做只读检查；
- 目标是先真实可用，而不是一次形成成熟 Agent Harness。

## 实现范围

- `GoalPlanPatch v2` 使用 `add_stages/replace_stages -> [{stage, steps[]}]`；
- v1 平面 committed event 只读回放兼容；
- 阶段屏障、跨阶段依赖和同阶段读写冲突验证；
- Strong Stage Checker 三字段输出和 Controller-bound provenance；
- repair feedback 的断点恢复关联；
- Stage Checker 的有界 Harness argument/result projection；
- UI 同时读取 v1 平面和 v2 嵌套事件。

## 明确未实现

同阶段运行时并发未实现。当前单 Executor State 和单 pending Audit boundary 不能安全共享线程。后续必须以每步隔离 State、独立 Audit boundary、只合并 Harness 事实的方式实现，不能复活旧 Atom Pool 作为捷径。

## 验证

- 阶段扩展当时相关定向：`63 passed`；
- 阶段扩展当时脏工作区全量：`774 passed, 1 warning`；其中后续提交完整性审核发现
  3 个测试依赖未提交旧 Contract Graph 源码，已从本次最新链提交中移除；最终脏工作区为
  `771 passed, 1 warning`，干净提交核心链为 `240 passed`。
- 固定模型数据与评价口径未改。
