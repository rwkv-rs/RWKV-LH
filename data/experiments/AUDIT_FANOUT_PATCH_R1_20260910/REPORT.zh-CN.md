# 审计扇出与 Selector 传输审计补丁轮（2026-09-10）

对 NATIVE_AUDIT_WIRING_REPAIR_R1（f34e4964）的独立复核发现三项遗留，本轮全部修复。单主题：审计事件的**正确归属与完整送达**；不改模型、提示词、预算、评分或角色分工。

## 1. atom 工厂共享 client 的订阅扇出缺陷（新引入，已修复）

f34e4964 之前该路径静默丢事件；之后变为**错误放大**：`run_case` 的 atom 工厂在共享 `rwkv_client` 上以每 atom 一个新闭包调用 `create_model_session` → 订阅表随 atom 数无界增长且永不摘除，一次传输事件被重复写入 N 份、各带**其他 atom 的 atom_id/contract_digest**（伪造归属）。影响 `parallel_atoms` / `contract_graph` 策略；stateful goal 四角色路径不受影响（本就每角色独立 client）。

修复（scripts/run_rwkv_e2e_benchmark.py）：atom 工厂提取为 `_build_atom_model_factory`，**省略 client 参数**——与四角色工厂同一模式，每 atom 独立 client、独立订阅。配套（rwkv_lh/parallel_atoms.py `_run_atom`）：atom 结束后 best-effort 关闭其 client（拆出 `_run_atom_with_model`，finally 关闭，异常路径同样关闭）。

回归测试（tests/test_native_request_recovery.py）：
- `test_shared_client_never_fans_events_out_to_other_subscribers_hooks`：固化"共享 client + 两个不同 hook"的扇出语义（这正是必须每 atom 独立 client 的原因）；
- `test_benchmark_atom_factory_allocates_one_client_per_atom`：三个 atom 三个独立 client、每个恰一订阅者、传输错误事件只归属自己的 atom_id；
- `test_atom_pool_closes_the_per_atom_client_after_the_run`：atom 体抛异常时 client 仍被关闭。

## 2. Selector 网络客户端零传输审计（既有空白，已补齐）

`NativeNetworkSelectorClient` 此前对 `requests.RequestException` 与非 200 只抛文本异常、零事件——"首错零丢失"口径永远覆盖不到 Selector 网络调用。

修复（rwkv_lh/exact_tool_selector/native_network_client.py）：构造器加可选 `audit_hook`；连接异常与非 200 响应在类型化异常抛出**之前** emit `selector_transport_error`（含 run_id/trace_id/menu_order_id/错误类型与消息，观察者异常隔离）。接线（三处生产构造点）：benchmark 主路径 → `model_trace.append`；atom 工厂 → 各 atom 的归属 hook；product_runtime → `model_audit_hook` 加 `model_role: selector_intent`。statetune_evaluation 的离线评测构造点有意不接（无 trace 概念）。

测试：`test_selector_transport_failures_are_audited_before_the_typed_error`（连接死亡与 HTTP 503 两形态）。

## 3. 订阅健壮性统一（既有不一致，已修复）

- `model_session.py`：`ModelSession.__init__` 与 `create_model_session` 的 `isinstance(OpenAICompatibleRWKVClient)` 闸门改为鸭子判定 `getattr(client, "add_audit_hook")`——包装/代理 client 不再静默失去审计。
- `ModelSession._emit` 与 transport-fallback 通知补观察者异常隔离，与 client 层合同一致（观察者永不改变模型调用语义）。
- `openai_compat.py` `add_audit_hook`/`_emit` 的 `in` 成员判断包裹 try——一个 `__eq__` 抛异常的订阅者不再能炸掉会话构造。

## 4. 交接文档修正（docs/HANDOFF.zh-CN.md）

- "StateTune 的真实进度"段的过时数字（81 条/386 对/113 对、"execute 覆盖已通过"）更新为当前有效状态（60 条/281 对/101 对、execute=0 及其根因——全部 execute 覆盖来自被排除的 RP-WEB-02），并写明正确补法是重跑含命令路径的采集而非扩大 waiver；
- 指向 draft waiver 的两处改为实际生效的 `SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json`，并写明 f34e4964 及本轮改动使已生效 waiver 对新源码失效、下一次等价复核必须覆盖全部新改动文件；
- 范围化 waiver 的执行 wrapper（原仅存于 gitignored temp/，是 14 来源/Selector-only 范围强制的单点）复制入库：`EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/helpers/extract_scoped_waiver_r1_20260910.py`，SHA `86f47b37…` 与 EVIDENCE_SHA256.json 既有登记一致；不改动任何已封存字节。

## 验证与遗留

- 全套 pytest：**1455 passed、0 failed**（上轮 1451 + 本轮新增 4 个测试；两个既有测试桩因 `_product_tool_selector` 新签名同步更新）。
- 本轮再次改动 `rwkv_lh/`（model_session.py、openai_compat.py、parallel_atoms.py、exact_tool_selector/native_network_client.py、product_runtime.py）——**旧 trace 的 SHA 准入需要在下一次等价复核中一并覆盖 f34e4964 与本轮**，一次重签。
- 未处理（非本轮主题）：Executor 18 次 length 的输出预算轮（独立预注册）；RED 缺失的 `test_benchmark_native_recovery...` 属历史记录问题不回补。
