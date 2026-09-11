from pathlib import Path
root=Path('/home/chase/GitHub/RWKV-LH')
for relative in ('rwkv_lh/goal_state_protocols/selector_intent_v7.py','rwkv_lh/goal_state_protocols/executor_args_v7.py','rwkv_lh/goal_state_protocols/auditor_step_v7.py','rwkv_lh/exact_tool_selector/input_protocol.py','rwkv_lh/exact_tool_selector/native_network_service.py'):
    p=root/relative
    p.write_text(p.read_text().replace('V6','V7').replace('v6','v7'))
p=root/'rwkv_lh/exact_tool_selector/network_protocol.py'
p.write_text(p.read_text().replace('failure-aware v4 validator','current role validator'))
p=root/'docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md'
s=p.read_text()
for before,after in [('selector_intent_v6','selector_intent_v7'),('executor_args_v6','executor_args_v7'),('auditor_step_v6','auditor_step_v7'),('selector-intent.v6','selector-intent.v7'),('executor-args.v6','executor-args.v7'),('auditor-step.v6','auditor-step.v7'),('finalizer-answer.v2','finalizer-answer.v3'),('auditor-final.v4','auditor-final.v5'),('只接受角色 v6','只接受角色 v7')]:
    s=s.replace(before,after)
s=s.replace('workspace_targets, completion_preconditions_satisfied, feedback, target_discovery_complete','workspace_targets, mechanical_preconditions_satisfied, completion_authority,\nevidence_records, feedback, target_discovery_complete, recent_rejections, operation_targets')
s=s.replace('result_metadata, observed_roots, mutated_roots','result_metadata, observed_roots, mutated_roots, observation')
s=s.replace('2026-09-09 当前实现统一使用 `role-feedback.v1`','2026-09-11 当前实现统一使用 `role-feedback.v2`')
marker='### 1.2 强制一致性检查'
s=s.replace(marker,'''Selector 的 observation 与 evidence_records 通过共享 Harness 投影携带实际结果内容及显式投影完整性。mechanical_preconditions_satisfied 只表示机械前置条件，completion_authority 固定为 false。Selector / Executor / Step Auditor 的事实范围共用 `goal_step_evidence_action_ids`：当前步骤当前版本的全部动作，加已完成依赖及传递依赖的提交证据，不按最近 N 条截断。依赖用于理解和比较，不能替代当前步骤的成功动作，也不能消除当前步骤的机械缺口。

审计 reason 保留 RWKV 对观察结果、未满足条件或缺少证据的具体诊断，通过 feedback.diagnosis 传递；原 criterion 保持独立。协议重试携带对应 request_id / audit_boundary_id 下的原始生成。Planner 默认事实、Executor 初始化与恢复不丢弃必需事实以适配预算，超预算记录并中断/阻塞，不得判完成。单条结果仍使用有完整性标记的内容投影，保留全部引用不等于保留全部原始字节。

'''+marker)
p.write_text(s)
