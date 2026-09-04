# Selector scoped-Harness subset remediation R3 结果

日期：2026-08-30

## 结论

原始缺陷已修复并通过真实 canary 完整性裁定。

- 根因：`LongHorizonModel.__init__` 错误要求每个 scoped Harness 的活动操作集合等于全局冻结的 25 类 Selector 可执行集合。contract-graph atom 按最小权限只暴露子集，因此在任何 Selector/Executor 请求前失败。
- 系统性修复：活动 Harness 允许是冻结 25 类菜单的子集；活动 Harness 出现全局菜单外操作仍 fail closed。全局 25 类顺序、描述、menu digest、MLP head、raw logits 和 raw argmax 均未改变。
- 未授权 raw argmax：保留完整原始 selection，记录 `exact_tool_selection_rejected` / `operation_not_authorized_by_active_harness` / `action_executed=false`；不 mask、不 remap、不 rerank、不替代执行。

## 验证

单元与相关路径回归：

- `uv run pytest --capture=no -q tests/test_independent_network_selector_integration.py tests/test_network_exact_tool_selector_client.py tests/test_network_exact_tool_selector_protocol.py tests/test_rwkv_e2e_suite.py`：38 passed。
- `uv run pytest --capture=no -q tests/test_*selector*.py tests/test_exact_tool_selection_handoff.py tests/test_contract_graph.py tests/test_parallel_atoms.py tests/test_retrieval_harness.py`：193 passed in 66.27s。
- `compileall` 与 `git diff --check`：通过。

真实固定 canary：

- 案例：E2E-B01、E2E-B02、E2E-B04。
- 24 个独立 atom state；107 个 Executor request/decision/raw generation；82 个 2.9B Selector raw 25-logit 输出；22 个 Harness action。
- 旧异常 `menu differs from the active Harness`：0。
- 79 个已提交/消费 selection；3 个未授权 selection 正确 fail closed；未授权 action：0。
- Planner/Reviewer 工具执行：0；`controller_rewritten=false`；RWKV action authority 保持。
- 只读直接 atom-state validator：16/16 gates passed；冻结源证据前后 SHA-256 完全相同；新增模型/Harness 请求 0。

完整性报告：

- `run_selector_scoped_harness_remediation_r3_canary/CANARY_B01_B02_B04/CONTRACT_GRAPH_ATOM_STATE_INTEGRITY_R3.json`
- SHA-256：`1d350790b8e8e0dcd107a6e856000c2b728b6fdba677f85df04769d22e86df6e`
- `run_selector_scoped_harness_remediation_r3_canary/READONLY_DIRECT_ATOM_STATE_VALIDATOR_R3_RESULT.json`

## 能力结果与下一步

本轮不是能力通过：B01/B02/B04 严格 Agent 结果仍为 0/3，external verifier 仅 1/3。修复后暴露的真实问题包括 finalizer 过早选择 `final_answer`、读取/写入选择与目标不一致、协议重试和跨 atom 修正不稳定。这些失败保持原样，作为独立真实 Agent 能力阶梯和约 2K old-capability state-tuning 数据的直接来源。
