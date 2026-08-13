# Round29 预注册协议：最小 provenance criterion commit

> 状态：`offline_implemented_real_canary_blocked_by_endpoint_unavailable`。冻结依据为 Round28 固定 E2E-B02
> canary；预注册写入后尚未发出 Round29 RWKV 请求，因为本地 `127.0.0.1:29610` 当前拒绝连接。

预注册日期：2026-08-13。唯一结构变量为 `minimal_provenance_criterion_commit.v1`。

## Round28 终端证据

主体链继续为 3/3 Task、3/3 Attempt 完成且隔离外部验收通过。停用 progressive witness 后，旧
`long-horizon.validation.v4` 在三个 Task 上分别因空 `subject_task_id`、输出旧 assertion 字段和重复 criterion intent
失败，0 条 CriterionEvidence。证明“保留另一套旧 proof”仍不是单一紧凑链路。

## 唯一变量

- Task 真实 action、确定性 verifier 与 postcondition commit 完成后，RWKV 仍先选择直接满足的 criterion ids。
- 对这些 ids 只再调用一个 G1i 工具 `commit_criterion_evidence`。参数只有顶层 `decision` 与 `bindings`；每个 binding
  恰好包含 `criterion_id`、`actual_ref`、`expected_ref`、`reason`。
- `actual_ref` 只能选择当前 Task 的真实 observation memory；`expected_ref` 只能选择 Immutable Goal 或已完成直接依赖的
  observation memory。提示中给出稳定 ID、owner Task、action、path lineage 和截断预览。
- Controller 只验证：criterion 覆盖、引用存在、owner/scope、Goal digest、当前与祖先关系，以及 actual/expected workspace
  path lineage 不相交。Controller 不生成 binding、值、reason、criterion、动作、摘要或答案。
- provenance commit 是 RWKV 的语义判断加可重放来源约束，不伪装成数值 exact-equality evaluator。状态和审计明确记录
  `rwkv_provenance_commit.v1`；最终恢复时重新校验引用 digest 与 lineage。
- 删除在线 progressive witness、pre-action intent 和 `validation.v4` criterion 路径；历史状态字段仅做 load migration，
  不成为在线第二状态机。

## 验证

- 完整 pytest、LH-Control-30、E2E-90 validate-only。
- 缺失/重复/越权引用、当前 Task 作为 expected、同路径 actual/expected、变更后的 digest 全部 fail closed。
- 固定 E2E-B02 记录 Strict/External、请求类型、criterion claims/evidence、FP/FN；不得用外部 acceptance 生成 evidence。

## 实施期预注册澄清

- 大型 fan-out 要求直接依赖显式携带证据来源；不再把任意传递祖先全部注入一个 criterion prompt。这样可在 16K 上下文内
  保持 source catalog 有界，并避免隐式跨层引用。需要原始输入的 Task 应把该读取 Task 声明为直接依赖。
- crash recovery 中若工具结果未持久化、但确定性后置条件观察到一个当前 Task 的工作区文件，则登记只读
  `workspace_recovery_observation`；它只包含 path/hash/截断预览，不包含 verifier 的 expected 参数，也不重执行写操作。
- 大型代码项目验收扩为 31 个文件。Goal 胶囊只保留 read observation 的 path/cursor 索引；完整正文仍留在每个 Task 的
  dependency memory，供该文件的后续 RWKV action proposal 使用。不得因胶囊压缩丢弃文件成员后仍声称全量完成。
