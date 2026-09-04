# RWKV-LH 单会话直接行动架构

## 设计目标

当前系统的目标不是让 Controller 代替弱模型做对任务，而是让 RWKV 的正确决定不被接口
阻塞，并且不放大其错误决定。用户请求以原文进入一个持续 RWKV Action session；系统不先
要求模型生成 Goal、验收条件、Task DAG 或 evidence contract。

在线链路只有：

```text
immutable user request
  -> one RWKV Action session
  -> one operation-specific registered call OR final_answer
  -> exact Harness ActionResult + artifact revision
  -> the same RWKV Action session
```

RWKV 决定 operation、全部显式参数、是否继续行动和 Final 文本。Runtime 只负责作用域、
sandbox、schema 校验、执行、Observation、持久化和恢复。

## 模型边界

bootstrap 显示 ActionDefinition 注册表投影出的具体工具 schema 和 `final_answer`。每次候选
只能是一个 `{function, params}` 调用。历史调用只存在于 committed transcript；格式失败会
rollback，不会执行半个 Action。

转换层只处理 call envelope 的常见等价拼写和 Markdown JSON fence。operation 参数由其
ActionDefinition 校验。若候选已经明确选择一个已注册 operation、但参数不合法，系统把原始
错误和该 operation 的完整当前 schema 作为最近 Observation 返回同一 session。它不把
`max_start_byte` 猜成其他字段，也不丢弃未知参数。

## CausalEvent 是唯一业务事实源

v17 不再把通用 envelope 作为现有状态旁边的审计副本。每次持久化只追加一个：

```text
schema_version / event_id / run_id / sequence / parent_id / cause_id /
subject_id / event_type / payload_schema / payload / digest / created_at
```

- `event_type` 来自显式注册表，并绑定版本化 `payload_schema`。
- `parent_id` 给出全局追加顺序；`cause_id` 指向直接原因；`subject_id` 聚合同一
  request/action/artifact/session。
- digest 覆盖事件身份、关系、payload schema、payload 和时间。
- Action 开始和结束是两个不可变事件。finish 必须匹配 start 的 operation、参数、fingerprint、
  decision、request、sequence 和 workspace-before digest。
- model decision、protocol rejection、ModelEvent append、artifact revision、rollover 和 Final
  进入同一事件协议。

`RunState.actions`、artifact heads、failure budget、active action、Final、UI 步骤和 SQLite
action index 都是事件 fold 的 disposable projection。Store 保存前先丢弃调用方的 projection，
追加事件，再从权威链重建；加载时也重新 fold，并校验 parent、cause、sequence、event digest
和 projection digest。因此调用方修改旧对象引用不能改变已保存事实。

ModelSession checkpoint/transcript 仍作为 transport cache 保存，因为当前后端只能
prompt replay。它不拥有业务完成语义；未来 native recurrent state 也必须保持相同事件边界。

## 副作用与恢复

Harness 执行前先持久化 `action_started`。正常结束后追加 `action_finished`，其中包含完整
ActionResult、artifact 与 revision。

- 幂等 Action 在 started 后进程丢失时，可用同一 action id 和显式参数恢复。
- 非幂等 Action 不自动重放；追加 interrupted finish，让同一 RWKV session看到未知副作用事实。
- 相同失败预算从 finished 事件的稳定 causal key 投影，不能通过 Task ID 或 replacement 重置。
- artifact revision 只记录时序事实，不判断新内容是否满足用户意图。

## Final

正常完成由 RWKV 显式调用 `final_answer(text)`。转换后的 `text` 字段按原始值交付，不做
事实纠正。达到 transition、protocol 或相同失败预算时，系统仍从同一 Action session请求一个
terminal `final_answer`；如果模型不能遵守 Final schema，则保留最后一份原始 RWKV 输出并
标记 failed。

Agent completed 与 External acceptance 必须分别报告。Final 非空不等于任务正确，Harness
动作成功也不等于用户目标满足。

## 当前明确不做

- 在线 Goal/criterion 解析、Task DAG、selector、reviewer、completion gate。
- Controller 语义验证、候选排序、答案修复或 hidden acceptance 反馈。
- 递归 subagent、MCP、服务插件和多模型 handoff。
- 在 Basic 链路过门前加入 workset、collection reduce 或效率型 prompt 压缩实验。

这些能力若以后需要，必须作为新的单变量协议建立在同一 CausalEvent 权威链之上，不能建立
第二套进度或恢复状态机。
