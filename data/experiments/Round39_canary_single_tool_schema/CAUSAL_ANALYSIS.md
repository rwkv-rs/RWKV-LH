# Round39 单工具 schema 五题定向分析

## 结果

- Strict：B14、B15、B25，`3/5`
- B21：External PASS、Agent blocked
- B30：External PASS、Agent blocked

## 机制命中

B25 的 T4 首次由 RWKV 明确选择 `write_json`，但参数混入 `create_parents/overwrite`。Harness 原样拒绝。第二次 system tool list 只包含 RWKV自己选的 `write_json`；RWKV 返回合法 `path + value`，事件记录：

- `path=rwkv_selected_single_schema_correction`
- `controller_selected_action=false`

最终 B25 Strict PASS。Controller 没有删除参数或选择工具。

B14、B15 本次所有 action 首次就合法，没有进入单 schema correction；其 Strict PASS 只能作为无回归样本，不能归因于纠正机制。

## 未解决问题

- B21 的 action 全部合法且 workspace 正确；后续 Task postcondition/replan 输出非 canonical Task batch，External PASS 但 blocked。
- B30 workspace 已正确修复且 External PASS；最后模型选择不存在的 `run_file`。由于第一次没有已注册工具 identity，Controller没有猜成 run_command，第二次仍 `run_file` 后 fail-closed。

## 结论

Round39 在已存在明确 RWKV工具选择时能减少参数跨 schema 混合，同时不改变工具 identity。它不处理未知工具名、规划冗余或 replan 格式问题。需运行 Basic30 判断净收益。
