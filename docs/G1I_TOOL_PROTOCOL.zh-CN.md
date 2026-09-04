# Selector→Executor 工具与原生状态协议

## 1. 职责边界

2.9B Selector 只接收名称/描述、有界进度与 eligible labels，返回一个原始 eligible argmax 和完整
logits。它不看参数 schema、完整工具结果或 Executor 文本。在线事件是：

```text
exact_tool_selection_staged
status=staged
authorizes_execution=false
```

13.3B Executor 在本 action 的干净角色 State、模型/profile、工具定义和 Goal contract 下复核该 handoff，
只接收一个 operation 的完整 schema、有界 Harness 事实和当前步骤，自己生成全部参数。selection 被 consumed 也仍然不是执行
authority；accepted Executor Decision + Goal/Harness policy 才允许 `action_started`。

## 2. Executor wire format

````text
ExecutorArgsPromptV1: {"current_requirement":"...","selected_operation":"...","selected_tool_contract":{...},...}

**Tool Call:**

```json
```
````

内部标准形式：

```json
{"function":"read_file","params":{"path":"input.txt","start_byte":0,"max_tokens":4096}}
```

允许无歧义的常见外壳：

- 名称键：`function`、`name` 或 `tool`；
- 参数键：`params`、`parameters`、`arguments`、`args` 或 `function_args`；
- 单键对象：`{"read_file": {...}}`；
- 显式 OpenAI 外壳：`{"function_call":{"name":"read_file","arguments":"{...}"}}`，其中
  `name` 必须存在，字符串化 `arguments` 必须精确解析为一个 JSON object；
- plain/json Markdown fence。

转换只搬运 RWKV 显式提供的 operation 和值，完整保存 raw output/digest。多名称、多参数键、外壳
多余字段、缺失显式 operation、多候选或前后 prose 均拒绝。Controller 不猜字段、不删除未知参数、
不把一个 operation 改成另一个。

## 3. 工具注册与 rejection

ActionDefinition 是模型 schema、默认值、参数校验、scope/policy、handler 和 recovery 的唯一注册源。
产品分类空间为 23 个 operation，加 `final_answer` 和 `ABSTAIN`。合法候选 commit 后才执行；失败
候选 rollback 且不产生 Action。

若 RWKV 已明确选择本轮可见 operation 但参数无效，下一步 delta 包含：

```json
{
  "action_executed": false,
  "selected_operation": "read_file",
  "selected_operation_schema": {"name":"read_file","parameters":"当前完整 schema"},
  "error_record": {"type":"...","message":"..."}
}
```

这只是重显同一工具契约，不选择新工具，不补参数；每个 handoff 最多一次修复。再次失败后返回 Selector，
并从干净 Executor State 开始新 action。连续 12 次 action 协议拒绝后进入 `BLOCKED`，停止 worker 自动续跑。

读取工具使用 UTF-8 `start_byte + max_tokens`，返回 byte range、source digest、`complete` 和唯一
`next_start_byte`。命令使用 argv、`shell=False` 和 bubblewrap；`search_text` 是 workspace 内原生
逐行搜索，不通过外部 `grep`。

## 4. 原生 RWKV state wire

服务端能力协商：

```json
{
  "recurrent_state": {
    "create": true,
    "resume": true,
    "fork": true,
    "commit": true,
    "rollback": true,
    "export": true,
    "import": true,
    "protocol": "rwkv-lh.native-state.v1"
  }
}
```

缺任一布尔能力或 protocol 不精确匹配，`native_required` 必须失败；不能根据 token cache、模型名或
普通 OpenAI completion 推断 WKV 可恢复。

状态端点：

| Endpoint | 输入核心 | 输出核心 |
|---|---|---|
| `POST /v1/state/create` | lane + bootstrap delta + cache binding | committed state snapshot |
| `POST /v1/state/append` | parent state ref + 新 delta + binding | child snapshot |
| `POST /v1/state/fork` | parent state ref + assignment delta + binding | fork snapshot |
| `POST /v1/state/generate` | parent state ref + sampling；无 prompt | candidate ref + raw output delta |
| `POST /v1/state/commit` | candidate ref + candidate binding | committed snapshot |
| `POST /v1/state/rollback` | candidate ref + exact parent ref | 无语义状态变更 |
| `POST /v1/state/import` | durable export locator + binding | recovered snapshot |

每个 binding 固定覆盖 lane/lane kind、model/model SHA、state profile、state-chain digest、delta digest、
event-ID digest 和 parent-state digest，并序列化：

```json
{
  "schema_version":"rwkv-lh.native-state-cache-binding.v1",
  "cache_role":"disposable_acceleration",
  "authoritative":false
}
```

snapshot 必须回显 binding digest、state digest、state format、server build 和 tokenizer build；
candidate 必须回显 parent state/binding digest。任一不一致都 fail closed。

## 5. commit、Observation 与下一步

```text
staged selector handoff
  -> Executor reauthorization + one schema
  -> state/generate(parent_ref)
  -> raw candidate persisted
  -> parse/schema/identity pass
  -> state/commit + accepted Decision
  -> selection consumed (still non-authoritative)
  -> action_started
  -> Harness exact operation(arguments)
  -> action_finished
  -> causal ledger commits bounded action facts
  -> next selection starts a clean Executor State from configured role profile
```

Parser 只读取本次 candidate，不扫描历史。ActionResult 的完整事实持久化在 causal ledger；下一
action 只收到有界精确投影，不继承旧工具输出或格式锚点。若 native cache 丢失，从 Goal/Action 权威
投影重建；不把旧 transcript 连成新 prompt，也不因 cache 存在跳过 ActionDefinition 校验。

## 6. Final 和 Goal

Finalizer 在独立 clean State 中生成 `final_answer({"text":"..."})`，文本保持 RWKV 显式值。Goal
mode 中只有该 candidate 通过独立 Final Auditor 才能产生 `run_completed`。普通 slice 或服务中断
产生 `run_yielded`；连续协议预算耗尽产生可人工恢复的 `run_blocked`，不会继续自动消耗调用。

`exact_tool_selection_committed` 仅为历史 ledger 读取兼容，不属于当前在线协议。

## 7. 当前验证边界

服务是否在线必须在每次实验中重新记录，不把历史端口当作当前事实。`/v1/capabilities` 必须精确
声明 `rwkv-lh.native-state.v1`、`prompt_replay=false` 和 `authoritative=false`。当前旧 Selector Head
因离线独立 feature 与在线持久 WKV 不一致已被淘汰；完成新的持久轨迹 Head 前不得宣称产品能力通过。
