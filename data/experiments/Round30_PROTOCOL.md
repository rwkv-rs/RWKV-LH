# Round30 预注册协议：criterion commit 协议错误不放大为 run 中断

预注册日期：2026-08-13。依据为 Round29 固定 E2E-B02 的 6 请求因果链。Round30 真实请求尚未发出。

## 唯一结构变量

- `commit_criterion_evidence` 第一次 `invoke_tool_call` 在解析/归一化失败并抛出时，不再访问不存在的 `call`。
- 原始 response、request id、temperature 和 protocol error 仍由 `ModelInvoker` 原样持久化。
- correction loop 只把已记录的错误和截断 raw output 放入第二次同工具协议提示；不包装裸 arguments，不补工具名、binding、
  criterion、ref、reason 或答案。
- 只有第二次 RWKV 自己返回完整 `commit_criterion_evidence` call 才能进入 binding validation。第二次仍失败时，将
  `ModelProtocolError` 交给 Controller 的 `criterion_provenance_commit_blocked` 路径，不得使 run interrupted。

## 固定验证

1. 单元回归：第一次裸 `decision/bindings`、第二次完整工具调用；验证两次真实请求、第一次 protocol error、第二次 raw
   输入显式包含工具名，且 `controller_semantic_fields_generated=false`。
2. 完整 pytest、LH-Control-30、E2E-90 validate-only。
3. 同一 `E2E-B02`、`max_transitions=80`、concurrency=1 真实 canary；对比 Round29 的请求链、Task、Attempt、Strict、
   External、FP/FN 和 Codex reference similarity。
4. 即使 External 通过，也要检查 T1 提前绑定 GC1 是否由 RWKV 自己产生，以及它是否造成错误证据或假阳性；不得只看总分。
