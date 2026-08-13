# Round28 预注册协议：单一 post-observation criterion proof

> 状态：`preregistered_implementation_in_progress_not_run`。冻结依据仅为 Round27 两次固定 E2E-B02 canary
> 的完整事件链；本协议写入前未发出 Round28 RWKV 请求。

预注册日期：2026-08-13。唯一结构变量为
`single_post_observation_criterion_proof.v1`。

## 因果证据

Round27 两次 canary 中，RWKV 均完成 `read_file(input.txt) → write_json(report.json) →
read_json(report.json)`，生成的 `report.json` 均通过隔离外部验收。第二次在透明 action wrapper 修复后，3/3 Task、
3/3 Attempt 均完成，但 Strict E2E 仍失败：Task criterion 后绑定过度声明后，在线 progressive witness 分支执行
`witness_expected_mode → witness_selection → witness binding`，没有生成一条 verified CriterionEvidence；随后
Goal extension 回显旧/无关结构并被阻断。主体 action 链正确，完成证明层是终端根因。

## 唯一变量

- 在线 criterion proof 只保留一条 post-observation 路径：RWKV 在真实 action result、确定性 verifier 结果和
  task-local dependency memory 可见后，提交 criterion assertion；运行时执行既有 typed proof evaluator。
- 停用并删除在线 `select_witness_sources`、`witness_expected_mode`、progressive opaque source catalog、witness
  binding revision，以及未被调用的 pre-action witness intent 状态机。
- 仍保留实际值与期望值来源独立性检查；同一 model-written workspace lineage 不能同时作为 actual 与 expected。
- Controller 不生成 criterion、断言、read operator、参数、期望值或答案，不修写 RWKV 输出。协议错误保留 raw
  output 并 fail closed。
- Task batch、G1i action、读取分页、并行前沿和 Goal immutable state 全部保持 Round27 冻结状态。

## 验证

- 完整 pytest、LH-Control-30、E2E-90 validate-only。
- 证明只有一个在线入口；旧 witness 方法不存在或不可达；实际/期望同源回归继续拒绝。
- 固定 E2E-B02 复验：外部验收、Task/Attempt、criterion evidence、请求类型和 Strict E2E 全部记录。
- 若该单路径仍因协议复杂度失败，先逐请求归因，不用外部验收结果补 evidence，不修改 RWKV 最终输出。
