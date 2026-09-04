# EXE-G6 task-level Stage C 确定性引擎复验 R6 预登记

登记时间：2026-08-30。登记时 R6 本地输出、三个远端 evidence tag 与 multi log 均不存在，
18075 空闲；R6 inference call 为 0。

R5 的输出已可恢复归档为
`invalid_generated_artifacts/run_exe_g6_task_level_stage_c_deterministic_engine_ablation_wrong_evaluator_wiring_20260830`。
其 result SHA-256 为
`3c9fba9daaef88a580fce95be7da2b40bb2e316ffd5e38a814b6035a6e2b436d`，invalidation
SHA-256 为 `773a974ae4325291bcc2e06aade1e16bd296edac8f1fb93347048a600cb12a07`。

## 唯一修正

R5 runner 校验了 deterministic evaluator `4b2ed1…`，但 `base.run_evaluator()` 使用的是冻结
helper 模块内部的 `EVALUATOR`，实际四组 summary 均记录旧 evaluator `f7c88…`、协议 v1、
temperature=0.1。R5 因此不是确定性实验，不得用于 R5 门禁或质量结论。

R6 在加载 helper 后显式绑定 `module.EVALUATOR` 到已冻结的 deterministic evaluator。并在每组
完成后立即失败关闭验证：

- summary schema 必须为 `rwkv-lh.executor-multi-profile-recovery72-summary.v2`；
- summary purpose 必须为 `deterministic_engine_state_identity`；
- summary runner SHA-256 必须为
  `4b2ed1bfa6c4e693241ea36e1a48e06a39948cc76d77405af4d8f3dd2b281006`；
- protocol schema 必须为 v2、purpose 相同、temperature 必须为 0.0；
- 行数必须等于 72×order 数量；每条 raw 的 temperature 必须为 0.0 且必须包含
  `request_semantics_sha256`。

任一内部身份不符，runner 在进入下一组之前失败，不能再由文件路径或外层声明掩盖。

## 数据、算法与门禁

R6 完整继承 R5 预登记 SHA-256
`1cb78b610c6ff5ee3f5802c0d327db096e1abd0067de906165ea0bd903bae9e4` 的数据、两个 state、
四组顺序、请求参数、语义 digest 算法、raw-first 保存、延迟阈值、GPU0/端口要求与 72/72
逐 token 全等门禁。除了 evaluator 依赖注入和上述内部身份校验，不允许修改任何评价口径。

R4 的失败结论与 R5 无效结论均保持不变；R6 通过才允许进入生产 temperature=0.1 质量消融。
