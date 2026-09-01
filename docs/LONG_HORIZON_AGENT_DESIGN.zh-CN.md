# RWKV-LH 长程 Agent：state+delta、权威链与自终止

## 设计目标

系统不让 Controller 代替 RWKV 决策，也不要求 16K 窗口反复容纳全部历史。用户请求作为
不可变 Goal；2.9B Selector 暂存 operation 候选；13.3B Executor 生成完整调用参数、决定继续
或 Final；Harness 只校验并执行已接受调用。

```text
immutable Goal + folded causal facts
  -> Selector WKV state + bounded selector delta
  -> exact_tool_selection_staged (non-authoritative)
  -> Executor reauthorization + one operation schema
  -> Executor WKV state + current delta
  -> accepted direct call OR explicit final_answer
  -> action_started -> Harness -> action_finished
  -> bounded observation delta -> same Executor state chain
```

## 16K 与 state+delta

`NativeRWKVModelSession` 首次把 bootstrap 送入 `/state/create`，以后只发送：

- `parent_state_ref`；
- 本步新 event、schema 或 Observation 的 delta；
- 当前采样参数和输出上限。

服务返回新的 state ref/digest。候选先是 forked candidate，只有 parser、operation visibility、
ActionDefinition schema 和所有 identity binding 通过后才 commit；否则 rollback 到精确父 state。

健康 native lane 不因为累计历史超过 16K 而 rollover 成 prompt replay。16K 只限制单次 bootstrap、
单步 delta 与输出余量。WKV 是模型对历史的递归压缩，不是精确事实数据库；文件正文、ActionResult、
证据和完成状态继续存在 CausalEvent/Artifact 中。cache miss 时系统从当前权威投影重建一个有界
bootstrap，不发额外语义模型请求，也不把全部旧 prompt 重放。

`ModelSession` prompt replay 仍保留作显式 bounded 消融。产品 Goal 强制 `native_required`；服务未
声明精确 `rwkv-lh.native-state.v1` 时 fail closed。

## WKV 只是一层 cache

每个 native checkpoint 带 `NativeStateCacheBinding`：lane、lane kind、模型和 SHA、state profile、
state-chain digest、本步 delta digest、event-ID digest、父 state digest。序列化值固定：

```json
{"cache_role":"disposable_acceleration","authoritative":false}
```

这层 cache 不能：

- 宣布 Action 已执行；
- 宣布 Goal 已完成；
- 覆盖 Goal、Decision、Action 或 causal ledger；
- 因为 state ref 存在就跳过当前工具/权限校验。

导入时若模型/profile/build/delta/event/binding 任一身份不一致，cache 被拒绝。Executor cache 丢失
时 staged selection 会被 discard，随后从权威 Goal/Action 投影重建并重新选择；Selector cache
丢失时同样从当前投影重建，不重放历史 Selector prompt。

## Selector 不是 execution authority

Selector 输出 `exact_tool_selection_staged`，其 `authorizes_execution` 必须为 `false`。Executor
使用它之前机械复核：

1. Selector 父 state 和 Executor 父 checkpoint；
2. Selector/Executor 模型、SHA、profile；
3. eligible labels、menu digest 和唯一工具定义 digest；
4. 当前 atom execution contract digest。

随后只披露一个工具 schema。13.3B 必须自己生成同一 operation 的直接调用和全部参数。有效
candidate 形成 accepted `DecisionRecord`，selection 变为 consumed；但 selection 本身仍不授权。
Controller 只有在 accepted Decision、Goal policy、ActionDefinition 和当前 contract 全部匹配后，
才先持久化 `action_started`，再调用 Harness。

`exact_tool_selection_committed` 仅作为历史 ledger 的读取兼容事件保留，不由在线链路产生。

## CausalEvent 是唯一业务事实源

每次持久化只追加一个版本化事件：

```text
schema_version / event_id / run_id / sequence / parent_id / cause_id /
subject_id / event_type / payload_schema / payload / digest / created_at
```

`RunState.actions`、artifact heads、failure budget、lane heads、Final、UI 状态与 SQLite action index
都是事件 fold 的 disposable projection。Store 保存前后均重新 fold，并校验 sequence、parent、
cause、event digest 和 projection digest。

权威层次为：

```text
Goal policy
  + append-only CausalEvent
  + accepted RWKV Decision
  + committed Harness Action/Result
  = current executable truth

WKV / transcript / staged selection / retrieval snapshot / isolated workspace
  = cache or candidate only
```

## Action、副作用与恢复

Harness 执行前先提交 `action_started`；结束后追加 `action_finished`，包含完整 ActionResult、artifact
与 revision。幂等 Action 可在进程丢失后用同一 action id 恢复；非幂等 Action 不自动重放未知
副作用。相同失败预算由稳定 causal key 投影，不能通过新 Task ID 清零。

当前默认 Stateful Goal Loop 不创建 Contract Graph atom workspace；Strong Planner 只编译义务与
证据门，唯一 13.3B 主 State 串行执行，RWKV Audit Fork 自审核。旧 Contract Graph atom 模式仍在
隔离 workspace 中执行，只有 contract 通过、声明写根完整覆盖后才事务合并；它不属于默认闭环。

## Goal 只能由 RWKV 自己停止

Goal Studio 写入固定 lifecycle policy：

```json
{
  "mode":"goal",
  "self_termination_only":true,
  "budget_boundary":"checkpoint_and_continue",
  "completion_authority":"rwkv_explicit_final_answer"
}
```

transition、action、protocol、重复或图预算只是 worker slice 边界；运行时、Selector、Supervisor、
state service 故障只是等待恢复边界。Controller 把所有内部 `run_interrupted/run_failed/run_blocked`
尝试转成 `run_yielded`，状态保持 running。web worker 重建 adapter、指数退避并继续。

唯一完成路径是已接受的 RWKV `final_answer(text)`，其 completion event 必须带明确 decision id 和
`output_source=rwkv_explicit_final_answer_text`（Contract Graph finalizer 使用对应的显式 RWKV source）。
外部杀死进程只停止计算，不改变持久 Goal 的语义状态。

bounded CLI 与历史实验仍可选择 interrupted/failed 语义或显式 prompt-replay 消融；它们不能改变
Goal mode 的不变量。

## 当前部署边界

代码、协议夹具和真实项目 Harness 验收已经覆盖 state+delta 与生命周期；13.3B 生产 tunnel
`29613` 也已声明并通过完整 create/resume/fork/generate/commit/rollback/export/import 验收。
固定 capability、续写 token 和 lifecycle exact 指标均为 1.0，产品客户端确认
`native_rwkv`、`prompt_replay=false`、精确 rollback，并在真实项目母路径执行只读 Action 后以
Observation delta 推进 child state。

这证明 live 原生 WKV transport 已上线，不代表多步 Agent 能力已经达标。固定三题模型能力结果仍为
0/3；后续能力优化必须继续使用固定数据、参数、阈值和 verifier。
