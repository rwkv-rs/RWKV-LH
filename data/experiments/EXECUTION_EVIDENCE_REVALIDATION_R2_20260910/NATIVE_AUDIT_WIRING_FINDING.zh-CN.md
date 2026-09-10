# Native 首错审计未接入生产会话

状态：已复现、未修复。本轮冻结评测源码，不修改运行中两臂。此发现更正 R1 报告中“无 Native 传输失败”的过强解释；R1 原始日志、结果与清单保持封存。

`rwkv_lh/runtime/openai_compat.py` 的 `_native_request` 确实在恢复前发出 `native_request_transport_error`，但 `_emit` 在 `audit_hook is None` 时直接返回。`rwkv_lh/model_session.py:create_model_session` 创建客户端时未传入会话的 `audit_hook`，`ModelSession.__init__` 和 `NativeRWKVModelSession.__init__` 也没有连接两者。会话自己的 generation 事件进入 trace，不能证明客户端的恢复事件也进入了同一 trace。

实际 benchmark `_build_stateful_goal_role_sessions` 和产品 `product_runtime` 四角色入口都只向该工厂传会话回调。普通 benchmark 显式创建客户端的入口、model 的 Native 隔离副本也未连接底层回调。独立 Selector 网络客户端是另一条传输链，本发现不能外推为 Selector 的同一个接线缺陷。

离线探针使用真实 benchmark 四角色工厂，只替换 capabilities 和 HTTP 会话，不请求模型、不修改生产源码：

- `NATIVE_AUDIT_WIRING_OFFLINE_PROBE.json`：四角色 client hook 均为空。底层事件到达 0，会话对照事件到达 1；仅在探针实例手动连接回调后，底层对照事件到达 1。
- `NATIVE_RECOVERY_AUDIT_OFFLINE_PROBE.json`：四角色都注入首个 POST 连接错误、两次收据 404，再恢复 POST 成功。实际调用顺序均为 POST/GET/GET/POST，全部恢复成功，审计 trace 却完全为空。成功恢复不会自动留下首错。

这证明的是日志可观察性缺陷，不是否定内容寻址重发本身。完整测试中已有 `test_proven_unrecorded_request_is_resubmitted_not_left_unknown`，它直接创建客户端并传 `audit_hook=events.append`，因此能通过但没有覆盖实际工厂的缺口。1447 全绿不能作为生产入口已接通的证明。

本轮统计中的 `native_first_errors=0` 只表示日志中没有该事件，必须同时读取 `native_first_error_counter_observable=false`。Controller 的最终终止原因、已返回 token/字节和 Supervisor 原始事件仍可核验；不能由此推断所有底层请求均未发生已恢复错误，或宣告“不再首错丢失”通过。

下一独立工程修复应在统一会话构造边界明确客户端和会话审计的连接职责，覆盖工厂隐式客户端、显式客户端、Native 角色隔离、已有回调保留、恰好一次送达和无回调调用者。需先让真实工厂恢复场景回归失败，再修复并跑完整回归。不能只在 benchmark 端临时补接。若修复改变 `rwkv_lh/`，后续对比必须以新冻结源码重跑双方，不能重评分或混用本轮结果。此报告不冒充已完成修复。

复现脚本为 `temp/probe_native_audit_wiring_r2_20260910.py` 和 `temp/probe_native_recovery_audit_r2_20260910.py`；冻结副本、探针结果和相关源码 SHA 登记在本轮证据清单。
