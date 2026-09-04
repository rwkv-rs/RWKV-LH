# Stateful Goal 重复动作闭环整改预注册

日期：2026-09-04（Asia/Shanghai）

## 冻结基线

- 源码起点：`e69543cd`，Selector Head v2 文件 SHA-256 为 `49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a`。
- 固定 canary：`AGENT-LADDER-L1-FIX01`，zero State、progressive disclosure、Strong `goal_stages`、最大 240 transitions。
- 原始结果 SHA-256：`8c395ea7e866597d0d6b04073d28ebc081e1230ed04d09208794562ed0db0075`；原始 audit SHA-256：`9f16f3226999c22c5d2c5afe8d5ac32cbb20d6c026e65fbd7ebca2125d6e9f81`；原始 SQLite SHA-256：`eb73e4948d9836c106fa2633a9acddf5347697af577fa2b57d5ef95b1441c4c7`。
- 基线事实：120 个 action 全部绑定 `S1@1`，0 次协议拒绝，0 个完成 step；54 次连续完全相同的失败 `read_json(pricing.py)`；Selector 单根 State 链达到 120 步和 token position 137,412；SQLite 为 489 MiB。

## 根因和固定整改

- `StatefulGoalLoopController` 在机械证据不完整时会记录 gap 并继续，但没有应用父 Controller 已冻结的相同失败预算与只读零进展预算；因此同一失败/无关成功可一直消耗 transition。
- 不改变 Planner、Selector、Executor 或 Auditor 的职责，不增加模型调用，不改变工具菜单、Head、State profile、评价口径或阈值。
- 在 Harness action 已持久化并绑定 Planner step 后、打开下一审计边界前，复用现有全局常量：第五个完全相同失败以 `identical_failure_budget_exhausted` 阻断；第三个完全相同的成功只读且 workspace 无变化结果以 `identical_success_budget_exhausted` 阻断。
- 阻断使用既有 `run_blocked`、`resumable=true` 和显式人工恢复语义；不得伪造完成、不得自动改 Planner step、不得自动切换工具。

## 固定验证

- 新增两个回归：相同失败恰好在第 5 次阻断；相同只读零进展成功恰好在第 3 次阻断。两者都必须没有悬空 audit boundary、没有额外 Selector/Executor 调用。
- 运行 `tests/test_stateful_goal_loop.py`、Selector/状态相关测试和完整测试集。
- 使用同一 fixed canary 复跑；只比较是否在固定预算处停止、action/State/SQLite 放大是否消失。能力成败仍按原 verifier 报告，不因本整改改变 Head 或数据。
