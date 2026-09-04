# E5 生产链路 R5 反事实预注册

日期：2026-09-04（Asia/Shanghai）

## 目的

在生产 Controller、状态存储、Harness 与真实原生 13.3B Executor 链路中，验证 E5 单一状态 payload 是否让第二次 `read_file` 从已完成的 `pricing.py` 转向唯一 remaining root `verify_project.py`。Selector 固定返回 `read_file`，只隔离 Executor 和状态传递，不作为 Selector 性能结果。

## 固定条件

- StateTune：未使用；Executor 为 zero State。
- Executor 模型 SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`。
- `pricing.py` SHA-256：`34bb21b4f1e0c9c4dec7b100ed25cb8b92e49fb220a821be78697e6442ca3204`。
- `verify_project.py` SHA-256：`3da7c7f94a1b5e6afa9ef1e457e9cb8a967a5f93d270cef560a1a8247f5b9301`。
- `rwkv_lh/model.py` SHA-256：`dccffac0ad0c991d85ec284e1a3ee42f8254d3fc54f1eef02eaacab3b7caaec3`。
- `rwkv_lh/stateful_goal_loop.py` SHA-256：`14405cccb745d774d0c0dfd0a0d020a33f784f7544c39ee325382401575b82ba`。
- `rwkv_lh/goal_state_protocols/executor_args.py` SHA-256：`232db48f73e794164ecd80a7a4c8e7fe5b860384db5bdbb93ef2740fd85fa986`。
- 固定 Planner step：依次建立两个文件的读取证据。
- 固定 Selector：每次选择 `read_file`；不调用 2.9B Head。
- Controller `max_transitions=4`；不执行任何临时重试或结果筛选。

## 门槛

- 前两次成功动作必须依次为 `read_file(pricing.py)`、`read_file(verify_project.py)`。
- 第二次 Executor 输入只允许一个 `remaining_read_roots` 状态字段，不含 `recent_exact_action_records` 或 `executor_history`。
- 协议拒绝为 0。
- 若不满足，生产接入不视为完成；不追加新提示版本。
