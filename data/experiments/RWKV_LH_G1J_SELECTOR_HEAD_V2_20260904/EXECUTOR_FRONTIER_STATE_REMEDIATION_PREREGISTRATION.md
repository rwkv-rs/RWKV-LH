# Executor 当前 Frontier 状态投影整改预注册

日期：2026-09-04（Asia/Shanghai）

## 冻结基线

- 使用同一 `AGENT-LADDER-L1-FIX01` 的 S1 和工作区，以诊断用确定性 Selector 连续选择 `read_file`，隔离真实 13.3B Executor 参数填写能力；该反事实不计入产品通过率。
- 原生推理结果：两次参数均为 `path=pricing.py,start_byte=0,max_tokens=4096`，均成功；第二次没有转向仍缺失证据的 `verify_project.py`。0 次协议拒绝。
- 第二次 Executor bootstrap 已包含第一次 `pricing.py` 的完整 action/result；因此不是全局 action fact 丢失。
- Controller 在第一次 action 后已持久化机械 gap `missing_read_roots=[verify_project.py]`，Selector frontier 能看到该 gap，但新一轮 Executor 的 `goal_frontier_assignment` 只含完整 step 和通用 instruction，没有投影当前机械覆盖状态。

## 根因和固定整改

- 全局权威状态（plan、action、audit gap）存在，但 Planner step 的当前机械证据覆盖没有进入 Executor 的局部执行事件。Executor 只能从完整 roots 与历史 action 自行重新推导剩余目标，造成已知局部状态在 Selector→Executor 交接处丢失。
- 在每次 `goal_frontier_assignment` 中加入 Controller 现有 `_step_mechanical_evidence_coverage` 的只读投影：assigned/successful action ids、missing read/write roots、completion precondition 与来源。
- 不替 Executor 选择 path，不修改 selected operation、Head、State profile、参数 schema 或 Harness；投影只传递 Controller 已持久化且可复核的事实。

## 固定验证

- 单元回归必须证明第二次同 step 的 Executor 输入包含 `missing_write_roots`/`missing_read_roots`，且 completion authority 仍为 false。
- 运行 Stateful Goal、Selector 相关测试和完整测试集。
- 以相同原生 13.3B、相同工作区、相同 deterministic `read_file` Selector 再跑反事实：记录第二次参数是否转向 `verify_project.py`，不因结果修改评价口径。
- 如果仍重复，归类为 13.3B zero-State Executor 能力缺陷；如果转向，归类为已修复的工程状态投影缺陷。无论结果如何，本轮不做 StateTune。
