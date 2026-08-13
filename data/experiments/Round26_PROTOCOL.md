# Round26 预注册协议：单一渐进因果接口

> 状态：`preregistered_implementation_in_progress_not_run`。冻结时尚未发出 Round26 RWKV 请求，未读取任何 Round26 hidden
> acceptance。触发证据为 `Round25/CAUSAL_ANALYSIS.md` 的完整 90 题第一断点。

预注册日期：2026-08-13。唯一结构变量为 `single_progressive_causal_protocol.v1`。

## 假设

Round25 的 0/90 不是下游执行失败：47 题被逐字 source_quote gate 拦截，32 题被仍停留在 v1/v2 的 normalizer 拒绝，剩余
主要被重复必填元数据和封闭 operation enum 拒绝。只保留一个在线 causal v3，并把不参与控制的元数据改为渐进字段，应首先恢复
Task materialize 和真实 action 覆盖；不会替 RWKV 生成任务、参数、期望值或答案。

## 唯一在线结构

1. Goal 在线协议只有一个版本；RWKV 生成 objective/constraints/success criteria。criterion provenance 绑定 immutable
   original_request digest，不再要求模型复制逐字 quote。Controller 不修改 criterion description。
2. Plan、goal-obligation extension 和 failure replan 只接受 causal v3。删除 v1/v2 与 bare-task 在线 fallback；旧 schema 仅限
   checkpoint load 时一次性迁移。
3. causal Task 核心字段仅为 local_id/title/description/explicit dependencies/postcondition。subject/member/phase/effect targets/
   expected outcomes/dependency outcomes/operation label 位于同一个 Task 内渐进披露；出现则严格类型校验，缺失不补入 raw payload。
4. 普通 dependency 没有 outcome 条件。只有 RWKV 显式声明的 dependency_outcomes 才产生条件边；expected_outcomes 缺失时动作仍
   只能按普通 success 路径提交。operation label 不参与 gate，真实动作仍由后续单工具 G1i 调用决定。
5. frontier 上限按同时 ready 的入口节点计为 8，不截断模型完整 DAG。总图仍保留 64 节点资源上限。
6. 透明 normalizer 只展开 plan.v3 的 task_graph.tasks/nodes，保留 raw/normalized payload 与 digest；无 schema、旧 schema、缺显式
   dependencies 的 nodes、冲突数组继续 fail closed。

## 固定验证与晋级

- 新增/更新测试覆盖：旧在线协议拒绝、v3 外壳全类型、无损字段保持、渐进 metadata、typed conditional edge、Goal digest
  provenance、总图/ready frontier、checkpoint 单向迁移。
- 运行完整 pytest、LH-Control-30、E2E-90 validate-only、历史恢复回归，再运行固定 E2E-90。
- 指标仍为 Strict/External/Completed/FP/FN、zero-task、zero-attempt、协议首断点、请求与 token；不得改变 hidden acceptance。
- 必须 FP=0、全回归通过，且至少恢复真实 action 覆盖并相对 Round25 严格改善；达到既有最佳门槛前不上传为更优版本。
