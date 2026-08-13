# Round23运行前：Round22透明协议边界冻结回放

本回放不调用RWKV、不执行Harness、不读取标准答案或hidden acceptance；只把Round22全部90题的冻结raw plan/action响应逐条送入预注册normalizer。完整逐请求记录在相邻JSON中。

## 结果

- 冻结trace覆盖：`90/90`；其中`84`题含plan/action response，共`672`个request。
- 旧protocol error经注册边界变为可继续校验：`15`。
- accepted但source identity/arguments/task array未原样保留：`0`。
- semantic mutation：`0`。
- JSON manifest SHA-256：`29bcbb12d67f99ce37090d740172619211abbce40122c7589a1bc3d4dd99bf4c`。

## Outcome变化逐条索引

| Case | Request | Type | Task | Selected/source | Transformations |
|---|---|---|---|---|---|
| E2E-B05 | `MR-028371b65bb44dbb` | tool_action | T6 | `read_json` | `flat_typed_function_envelope_to_canonical` |
| E2E-H01 | `MR-21dd5d1abfde4d92` | tool_action | T5 | `run_command` | `action_type_alias_to_canonical` |
| E2E-H02 | `MR-cefe6d89770d4e94` | task_decomposition | PLAN | `plan_task_array` | `task_graph_tasks_to_canonical_tasks+registered_plan_envelope_implies_v2` |
| E2E-H02 | `MR-260081630b3a44a9` | task_decomposition | PLAN | `plan_task_array` | `task_graph_tasks_to_canonical_tasks+registered_plan_envelope_implies_v2` |
| E2E-H06 | `MR-78240b594c24419d` | tool_action | T7 | `read_json` | `action_type_alias_to_canonical` |
| E2E-H09 | `MR-199478a280524f35` | tool_action | T2 | `read_file` | `flat_typed_function_envelope_to_canonical` |
| E2E-H13 | `MR-a8d55a407597476d` | tool_action | T4 | `write_json` | `action_type_alias_to_canonical` |
| E2E-LH01 | `MR-f2e0364cdf694bba` | tool_action | T7 | `run_command` | `action_envelope_to_canonical` |
| E2E-LH02 | `MR-ab9c58440303468f` | tool_action | T3 | `write_json` | `action_envelope_to_canonical` |
| E2E-LH07 | `MR-d243d779c34541da` | task_decomposition | PLAN | `plan_task_array` | `task_graph_tasks_to_canonical_tasks+registered_plan_envelope_implies_v2` |
| E2E-LH07 | `MR-589eab633f304b11` | task_decomposition | PLAN | `plan_task_array` | `task_graph_tasks_to_canonical_tasks+registered_plan_envelope_implies_v2` |
| E2E-LH10 | `MR-cb58a3b8aeab469e` | tool_action | T4 | `run_command` | `action_envelope_to_canonical` |
| E2E-M09 | `MR-614c0e7291a743b9` | tool_action | T8 | `run_command` | `single_direct_tool_calls_envelope_to_canonical` |
| E2E-M12 | `MR-b18a2a8df5674433` | tool_action | T5 | `run_command` | `action_type_alias_to_canonical` |
| E2E-M22 | `MR-736bab8bf28e4a48` | tool_action | T6 | `write_json` | `action_envelope_to_canonical` |

## 解释边界

这里的accepted只表示wire envelope可以唯一、透明地转换为canonical view，不表示Task、参数、产物或答案正确。所有scope、argument contract、TaskGraph和后续业务验证仍须执行。被拒绝记录保留具体error，不能由回放脚本选择其他候选。
