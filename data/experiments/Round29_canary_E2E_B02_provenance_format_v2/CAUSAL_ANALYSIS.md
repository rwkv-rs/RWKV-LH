# Round29 E2E-B02 逐链路因果分析

## 结果

- Strict E2E：FAIL；Agent：FAIL；External：FAIL。
- 终态：`interrupted`。
- 真实模型请求：6；Task：2；Attempt：1。
- 异常：`AttributeError: 'NoneType' object has no attribute 'decision'`。

这次结果不得归类为“RWKV 不会完成任务”：模型已经完成 Goal、两 Task 结构、第一 Task 的 `read_file`、真实读取和
Task postcondition commit。run 被本地异常中断在 criterion evidence 格式纠正路径，第二个 Task 尚未执行。

## 从前向后逐环节

1. `goal_parse`：RWKV 返回可解析 Goal proposal，进入状态。
2. `task_decomposition`：RWKV 返回 `long-horizon.task-batch.v1`，得到两个因果 Task。
3. `tool_action_commit/T1`：RWKV 返回 `{"tool":"read_file","arguments":...}`；透明归一化只把 `tool` 改为
   `name`，参数原样保留。
4. Harness：真实读取 `input.txt`，输出 `project=Orion`、`count=7`。
5. `task_postcondition_commit`：RWKV 判定读取 Task pass。
6. `task_criterion_binding`：RWKV 把 GC1 绑定到 T1。
7. `criterion_evidence_commit`：RWKV 输出完整 `decision/bindings` 内容，但没有输出
   `commit_criterion_evidence` 工具名。格式边界因 unknown fields 正确 fail closed，没有把唯一候选工具名补进去。
8. `ModelInvoker.invoke_tool_call` 已持久化 `model_protocol_error` 后抛出 `ModelProtocolError`。
9. `LongHorizonModel.commit_criterion_evidence` 的 correction loop 将局部变量 `call` 初始化为 `None`，却在
   exception 分支无条件读取 `call.decision.request_id`；因此发生 AttributeError。
10. runner 捕获未处理异常并写 `run_interrupted`。第二次协议纠正、T2、最终回答和外部验收均没有机会运行。

## 归因

- 起点：RWKV 少输出一层工具调用外壳，是可重试的模型协议错误。
- 放大器：模型适配器错误地假设失败时一定有返回的 `ModelCallResult`，属于通用异常路径代码缺陷。
- 终端失败：适配器的 None dereference，而非 Harness、Controller Task 状态、外部 verifier 或转发连接。
- 不采用的修复：根据唯一工具把裸 `decision/bindings` 自动包装成调用。这样会由规则补出 RWKV 未输出的工具决定，违反
  非作弊边界。

## Round30 指导

让失败路径复用 `ModelInvoker` 已记录的 request decision/raw response，生成第二次同协议 correction request；只有 RWKV
自己在第二次输出完整调用才继续。两次仍不合法则返回 `ModelProtocolError` 给 Controller 的现有 fail-closed 路径，不能中断 run。
