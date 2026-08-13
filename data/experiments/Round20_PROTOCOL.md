# Round20 实验协议：不变确定性证明失败的恢复去重

预登记时间：2026-08-13；在任何 Round20 RWKV 请求之前。

## 因果来源

本轮变量在标准答案解封前已经写入 Round19
`PRESTANDARD_CAUSAL_SYNTHESIS.md`：Round19 的模型写入同一目标来源拒绝在 8 题重复发生
49 次；相较 Round18，obligation saved replans 增加 10、appended tasks 增加 30、
duplicate task instances 增加 43、首次 replan 后事件增加 616。该选择不依赖 Round19
hidden acceptance 或 Codex 标准答案。

## 唯一架构变量

变量名：`unchanged_deterministic_proof_recovery.v1`。

保留 Round19 的渐进 witness 协议和 `model_written_target_provenance_independence.v1`。
只接通现有 GoalObligationState、workspace observation digest、proof failure 与 recovery budget：

1. Goal obligation capsule 增加完整 workspace observation 的 `cacheable/digest/reason` 元数据；
   不把 digest 当成正确性证据。
2. 从冻结状态中登记先前的确定性 proof failure，只有以下条件全部成立才可登记：
   - validation 是 `model_cross_check` 或 `criterion_cross_check`；
   - `observation_cacheable=true` 且 `protocol_valid=true`；
   - `proof_passed=false`；
   - 失败指纹是 Round19 已实现的
     `actual and expected share model-written workspace target lineage`；
   - 失败时的 workspace digest 与当前完整 workspace digest 相同。
3. RWKV 的 obligation proposal 若包含任何与上述失败任务完全相同的预登记语义签名，整份 proposal
   原样拒绝，不删除其中字段或只选择部分任务；现有 obligation budget 消耗 1，并把语义签名、
   failure fingerprint 和 prior task id 作为透明 recovery feedback 交给下一次 RWKV replan。
4. 语义签名固定复用 Round15--Round19 的离线指标：`title`、`description`、排序后的
   `advances_criteria`、排序后的 `satisfies_criteria`。运行后不得改变算法。
5. workspace 变化、snapshot 不可缓存、失败不是上述窄化 proof failure、任务语义不同，均不得抑制。

Runtime 不生成任务、action、criterion、expected value 或答案；不修改 RWKV action/final output；
不读取 hidden acceptance/standard answer；不根据候选正确率选择 proposal。

## 固定运行

- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`
- endpoint：`http://127.0.0.1:29610/v1`
- 数据集：RWKV-E2E-90 v1，Basic/Medium/Hard 各 30
- 并发：8
- 每题最大 transitions：200
- 与 Round19 相同的 request-level sampling、相似度算法、hidden-answer boundary 与 runner
- 生成结束前不运行标准答案比较

## 运行前验证

- 新增边界测试：不变 workspace + 相同失败语义整份拒绝；workspace 变化后允许；不同语义允许；
  不可缓存 snapshot 允许；混合 proposal 不做部分筛选；feedback 与 budget 可审计。
- 全产品 pytest 全通过。
- LH-Control 30/30。
- RWKV-E2E-90 validate-only 90/90。
- Round18 proof replay 仍保持 4 条允许、8 条新 provenance 拒绝、1 条既有 hash 拒绝。

## 运行后指标与晋级门

先运行 score-independent 分析，再解封标准答案。除 Strict/External/Completed/FP/FN 外，固定报告：

- unchanged deterministic proof proposal 抑制事件/题数；
- 被拒 proposal 的完整 task 语义签名和 failure fingerprint；
- 发生 workspace 变化后重新允许的次数；
- model-written same-target proof rejection events；
- saved replans、appended tasks、duplicate task instances；
- witness mode/binding、proof、CriterionEvidence 漏斗；
- 总模型请求、token、时延和 raw/delivered final equality。

GitHub 晋级条件恢复并固定为全部满足：

- FP = 0；
- Strict > 7/90；
- Completed > 7/90；
- External >= 历史最佳 24/90；
- 全产品测试、LH-Control、E2E-90 完整性、边界/异常/历史恢复回归全部通过；
- 没有通过规则补值、筛选答案或改写 RWKV final output。

任一条件不满足则 `do_not_upload`。
