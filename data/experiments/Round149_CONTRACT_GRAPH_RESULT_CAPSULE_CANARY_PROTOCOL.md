# Round149：Contract Graph Result Capsule Canary 预注册

日期：2026-08-22

## 被测架构

固定架构标识：`strong-planner-reviewer-rwkv-contract-graph.v1`。

- GPT-5.4 Planner 首次把 immutable request 编译为 append-only obligations、RWKV work DAG 和一个
  frozen finalizer；Planner 无审核、工具和 Final 权限。
- 确定性 scheduler 连续派发全部 ready、scope 不冲突节点；普通 RWKV batch 前后不调用 GPT。
- GPT-5.4 Reviewer 与 Planner 使用分离 schema，只读取 immutable contract、graph、workspace manifest
  和 content-addressed result capsules；逐 obligation 返回 verdict 和 evidence refs。
- result capsule 只含 node/status、最终 operation result、artifact path/hash/size、workspace revision 和
  terminal error。禁止 RWKV prompt、transcript、arguments、candidate、worker summary、model request、
  retry/rejection 过程进入强模型请求。
- required obligations 全部由当前 revision 的注册 evidence 满足后，scheduler 才执行 RWKV finalizer；
  顶层 Final 原样交付，GPT 和 controller 均不改写。

旧 `Round149_INDEPENDENT_REVIEWER_CAUSAL_ATOMS_V5_PROTOCOL.md` 未执行并已在运行前废止。

## 固定代码与运行参数

- 全项目回归基线：`150 passed`。
- case concurrency=4；RWKV atom concurrency=4；GPT 请求跨 case 文件锁串行。
- transport retry=3；semantic repair=2；max transitions=200。
- max graph patches=8；max reviewer rounds=8；max graph atoms=48；stagnant rounds=2。
- RWKV sampling、工具定义、hidden verifier、评分算法、任务与 reference 均不修改。
- supervisor strategy=`contract_graph`；训练数据仍不生成。

## 固定 Canary（13 例）

- 旧 FP 公开证据检查：B22、M15、LH06。
- 终止/FN：B09、M24。
- 因果/恢复/scope：H09、M10、LH04、LH08、M28、LH09。
- 稳定正例：B04、M16。

与 Round148 同一 13 例对照。Round148 在这些题为 strict 2/13、GPT 请求 79 次（均值 6.08，
范围 4–13）。

## 预注册指标与晋级门

质量门：

1. strict 至少 11/13；B09、M24 至少一题由 FN 转 TP，且无新增 FN。
2. B22、M15、LH06 至少两题由 FP 转 TP。
3. H09、M10、LH04、LH08 至少两题的公开因果/恢复门通过。
4. M28 无 ScopeViolation；LH09 无 scope-incompatible planner termination。
5. B04、M16 两个稳定正例全部保留。

架构门：

1. 常规成功题只有一次初始 Planner、一次 Reviewer；13 题 GPT request 总数不超过 52，且中位数
   不超过 4，相比 Round148 固定子集 79 次至少下降 34%。
2. 所有 Planner/Reviewer 请求 DTO 均为 result-capsule boundary；审计中 GPT tool execution=0。
3. finalizer 只在当前 graph revision 的全部 required obligations satisfied 后执行，且 action_count>=1。
4. 所有 completed Final 与 raw RWKV candidate byte-exact；controller_rewritten=false。
5. 至少 5 题存在真实 RWKV atom overlap；GPT 串行不降低 RWKV case/atom 并发。
6. 无 HTTP 500 最终终止、duplicate node、stale revision、unknown evidence 或 process-loss 被吞。

若任一质量门失败，不启动 Full90；保持固定数据和指标分析根因。只有全部门通过后才预注册
Contract Graph Full90。
