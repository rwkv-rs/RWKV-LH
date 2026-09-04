# E5 生产链路 R5 反事实结果

日期：2026-09-04（Asia/Shanghai）

## 结果

R5 未通过预注册门槛，不重跑。

- 第一次动作：`read_file(pricing.py)`，成功。
- 第二次动作：`read_file(pricing.py)`，成功但重复已完成路径。
- 期望第二次动作：`read_file(verify_project.py)`。
- 协议拒绝：0。
- Selector 请求：2；两次均由固定诊断 Selector 返回 `read_file`。
- Controller 在 `max_transitions=4` 后按边界中断。

结果文件：`r5_controller_counterfactual/RESULT.json`，SHA-256 `582af5b76ecf045526dc5fc4f822fe8fc62127c05139a0aad337f75e5d55178e`。

## 第二次真实输入复核

- 总输入：725 tokens。
- 最终 payload：709 tokens。
- `execution_state` 起始位置：token 584。
- `current_question` 起始位置：token 668。
- `supporting_facts` 中上一次读取的完整输出：952 characters。
- `execution_state.completed_actions` 明确包含 `read_file(pricing.py)`。
- `execution_state.remaining_read_roots` 明确且仅包含 `verify_project.py`。
- 不含 `recent_exact_action_records`、`executor_history` 或 `goal_frontier_assignment` 事件副本。

## 结论

状态传递的结构性重复已经消除，但完整历史事实仍会改变 zero-State 13.3B 的参数选择。E4 的短事实输入可 18/18 遵循 remaining root，E5 的短跨类输入可 33/42，而生产完整事实输入仍重复旧路径。因此 E5 适合作为后续 StateTune 的当前最佳数据布局，但没有达到生产替换条件。

本轮不增加 E6，不用规则删除括号、修复 Python 字面量或重写函数名，也不保留未通过的生产协议改动。后续 StateTune 数据至少必须覆盖：

- 长 supporting fact 后仍服从尾部 remaining state；
- `check_command` / `run_command` 必须保持已提交 operation identity；
- `replace_text` 必须输出严格 JSON，而不是 Python dict 字面量；
- completed action 与 remaining action 的对比样本；
- 中文/英文、路径顺序和工具类别交叉。
