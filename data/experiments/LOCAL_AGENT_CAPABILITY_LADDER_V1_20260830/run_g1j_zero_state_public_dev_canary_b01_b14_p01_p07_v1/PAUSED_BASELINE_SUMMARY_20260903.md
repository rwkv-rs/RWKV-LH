# G1J 全 zero State Agent 基线暂停总结

记录时间：2026-09-03 23:01:45（Asia/Shanghai）

## 当前边界

- 用户已明确要求停止测试；当前没有基线执行进程。
- 正式单轮分母原定为 21 个用例：B01-B14 与 P01-P07。
- 已形成 20 个有效、独立评分的正式记录：B01-B14 共 14 个，P01-P06 共 6 个。
- P07 在 222/240 个转换调用后由操作员中止，未生成正式 `RESULT.json` 或 `BASELINE_METRICS.json`，不得进入能力分母。
- 未进行 Head 训练或 StateTune。

## 已完成样本的能力结果

### B01-B14

- 有效记录：14/14。
- 完整任务成功：0/14。
- 请求：3345 次 RWKV、15 次强模型，共 3360 次转换。
- Executor 动作：790 次，其中 748 次 `list_directory`、42 次 `move_file`。
- 协议拒绝：Executor 1765 次、Step Auditor 226 次。
- 仅 B06 有 1 个步骤被接受；其余步骤均未完成；所有用例均无合法最终回答。
- Selector parent 绑定为 790/790，完整工具描述为 804/804，冻结 `**Tool Call:**` JSON 锚点为 3345/3345。

### P01-P06

- 有效记录：6/6。
- 完整任务成功：0/6。
- 每题均消耗完整 240 次转换，共 1434 次 RWKV 请求和 6 次有效强 Planner 请求。
- 强 Planner 每题均给出 5 个具有依赖关系的阶段，共 30 个步骤；完成步骤为 0。
- Executor 动作共 314 次：277 次成功 `list_directory`，37 次失败 `move_file`。
- 没有 `read_file`、写文件、补丁、命令执行或合法 `final_answer`。
- Executor 协议拒绝 806 次，Step Auditor 协议拒绝 16 次。
- 六个工程工作区均为空；独立验证总计 12/42，只通过了无越界和进程树关闭类检查。
- Selector parent 绑定为 314/314，完整工具描述为 320/320，冻结提示锚点为 1434/1434。

## P07 中止状态

- 数据库保留在 `strong_planner_projects/seed_20260903/cases/STRONG-PLANNER-P07-S20260903/state/long_horizon.db`。
- 中止快照为 222 个转换调用：33 个接受、156 个拒绝、33 个 Auditor session。
- 已记录 161 个协议拒绝、15 次成功目录查看和 18 次失败移动。
- 工作区为空，数据库状态仍为 `running`；这是人工中止后的持久状态，不是 Agent 完成状态。
- 详细分类见 `P07_OPERATOR_STOP_RECORD.json`。

## 强模型基础设施问题

- P 组共归档 22 个无效尝试：19 个 `goal_plan` 阶段 HTTP 500、2 个操作员中止、1 个套件终止。
- 19 个 HTTP 500 均发生在首个 RWKV 请求之前，错误为 `SupervisorTransportError: supervisor HTTP 500 during goal_plan`，不进入能力分母。
- P01-P06 随后都能在相同冻结身份下取得 GPT-5.6-Sol 计划，因此现有证据不支持“模型预算不足”或“提示词确定性拒绝”；更符合中转站或上游路由的间歇性失败。
- 当前持久 Trace 保存强模型身份、阶段、错误、请求/响应哈希和规范化计划，但不保存原始 HTTP 请求与响应正文，因此不能从现有记录进一步确认 500 的底层响应原因。

## 验证器污染

- P01-P06 的 `pytest` 黑盒项使用的 `/opt/verifier-python/bin/python3.13` 没有安装 pytest。
- B13 的一个嵌套验证脚本调用不存在的 `python` 命令。
- 两项会污染外部子检查通过率，但不会改变这些用例没有目标产物、没有完成步骤、没有最终回答的能力失败结论。

## 当前结论

当前只能报告 20 个有效样本的阶段性结果，不能声称 21 题完整基线完成。G1J 全 zero State 链路已经能稳定接收 next-state、parent State、工具描述和固定输出锚点，但行动策略退化为重复目录枚举及无效移动，尚不具备真实工程 Agent 的文件读取、修改、执行、验证与合法终止能力。
