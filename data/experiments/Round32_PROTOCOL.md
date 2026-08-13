# Round32 预注册协议：单一 Task-batch replan 输入投影

预注册日期：2026-08-13。依据为 Round31 E2E-B02 的 T3 failure/replan 链。Round32 请求尚未发出。

## 唯一结构变量

- replan 输出仍只接受 `long-horizon.task-batch.v1` 与五字段 Task，不增加 normalizer 变体。
- failed Task 输入只保留：title、description、dependencies、postcondition；失败 Task 的现有全局 ID 单独作为不可复用字符串。
- observed failure 只保留实际 action name/arguments、真实 ActionResult 的 success/output/metadata/error/outcome_type，以及失败 required
  checks 的 kind/message。移除 Attempt bookkeeping、criterion/witness 内部状态、completion criteria 和旧 Task schema 字段。
- bounded context 只保留 Immutable Goal 与 dependency/evidence observations；不再第二次注入 rich ACTIVE TASK、causal bookkeeping 或
  recovery object。
- correction 只给 deterministic error 和所需 canonical field list，不回灌被拒绝的 rich payload。

Controller 仍整体拒绝非五字段 Task、旧 ID、依赖 failed Task、未知/未完成依赖和 cycle；不会从被拒绝 payload 中提取“看起来可用”
的 title/action/arguments。

## 验证

- replan prompt 不含 `advances_criteria/satisfies_criteria/completion_criteria/operation_kind/recovery_lineage_id/last_attempt`。
- raw rich replan 仍被拒绝；第二请求只能由模型生成新 Task batch。
- 完整 pytest、LH-Control-30、E2E-90 validate-only、同一 E2E-B02 real canary。
- 单独记录 T1 错误 GC2 evidence，不因 Strict 变化掩盖模型语义缺陷。
