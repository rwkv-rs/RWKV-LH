# G1i 单会话直接工具协议

## Wire format

bootstrap：

````text
System: Tools: <compact operation-specific JSON definitions>
Choose exactly one displayed tool. Return one JSON function call.

User: <immutable request + constraints + workspace manifest>

Assistant: ```json
````

内部标准形式：

```json
{"function":"read_file","params":{"path":"input.txt","start_byte":0,"max_tokens":4096}}
```

模型可使用一个无歧义的常见外壳：

- 名称键：`function`、`name` 或 `tool`
- 参数键：`params`、`parameters`、`arguments`、`args` 或 `function_args`
- 单键对象：`{"read_file": {...}}`
- plain/json Markdown fence

转换只搬运模型显式提供的 operation 与值，完整记录 raw/normalized payload 和 digest。多名称、
多参数键、外壳多余字段、字符串化参数、多候选或前后 prose 会被拒绝。

## 具体工具参数不使用通用外壳

RWKV 直接看到并调用每个 Harness ActionDefinition：`list_directory`、`search_text`、`read_file`、
`read_json`、`write_file`、`write_json`、`patch_json`、`replace_text`、`remove_line`、
`append_file`、`make_directory`、`copy_file`、`delete_file`、`bind_evidence`、
`check_command`、`run_command`，以及 terminal `final_answer`。

没有 `lh_task_call(operation, operation_args)`。ActionDefinition 同时生成模型 schema、默认值、
参数校验和 handler 绑定，避免工具说明与执行接口分叉。

读取接口使用 UTF-8 `start_byte + max_tokens`，结果提供实际 byte range、source digest、
`complete` 和唯一 `next_start_byte`。EOF 是显式 Observation。命令使用 argv 且 `shell=False`；
Python 命令复用只读 uv 环境。

`search_text` 是工作区内的原生只读逐行搜索，不通过外部命令。它默认采用 grep 风格正则
（例如 `TODO|FIXME`），只有逐字搜索正则标点时才显式使用 `mode=literal`。结果按相对路径、
行、列稳定排序，返回匹配文本与有界行摘录；`max_results` 和 `max_tokens` 都会产生
query-bound opaque `next_cursor`。工具不做重要性或紧急度排序，语义判断仍由 RWKV 完成。

## Rejection feedback

候选解析成功后，系统先确认 operation 本轮可见，再校验对应参数。失败候选 rollback 且不执行。

如果 operation 已明确且已注册，下一条 typed Observation 包含：

```json
{
  "error": "原始拒绝原因",
  "action_executed": false,
  "selected_operation": "read_file",
  "selected_operation_schema": {"name": "read_file", "parameters": "完整当前 schema"}
}
```

这只是把 RWKV 已选择工具的现有契约移到最近上下文，不选择新 operation，也不补、删、改参数。
JSON 无法解析或 operation 未注册时不添加猜测 schema。

## Observation 与 commit

合法候选 commit 后才执行。ActionResult 被写入 `action_finished` CausalEvent，并以一个
`action_result` ModelEvent 追加回同一 checkpoint：

```text
accepted direct call
  -> action_started persisted
  -> Harness executes explicit params
  -> action_finished persisted
  -> exact action_result appended
  -> next generation
```

Parser 只读取本次候选，不递归扫描历史。一个回合不产生多个 Action。Final 使用
`final_answer({"text": ...})`，`text` 保持 RWKV 显式值。

## ModelSession

`bootstrap / append / generate / commit / rollback / rollover / export / import` 统一当前
prompt replay 与未来 native transport。候选在 commit 前不可见；rollback 回到输入 checkpoint。

当前 endpoint 没有经验证的 recurrent state handle，所以 transport 明确标为
`prompt_replay`。Native transport 只有在服务端实现并通过 create/resume/fork/commit/
rollback/export/import capability 测试后才能启用。
