# 主动 Harness P1/P2 审查整改报告

状态：8/8 工程项已整改；正式模型实验继续冻结。

| 审查项 | 系统性整改 | 新回归 |
|---|---|---|
| P1 lease takeover | 所有 run/terminal 写入校验 `lease_owner + lease_generation + lease_until`；迟到结果静默失去提交权 | 接管后旧 worker 的 bind/complete/retry/fail 全拒绝；过期未接管也拒绝 |
| P1 truncated evidence | output 或整体 result 投影一旦截断即强制 `metadata.complete=false` | 超长 `text_excludes` 返回 unresolved，不能把前缀当全文 |
| P1 graph v2 resume | 架构版本集中为常量，恢复兼容 v1/v2，benchmark 写当前 v2 | 仅存在 v2 `run_started` 时无 supervisor 仍失败关闭、零模型调用 |
| P2 disclosed retry budget | 拒绝事件追加后重新检查；若 rollover，重建单工具菜单并重新披露完整 schema | 边界上下文触发 rollover 后仍按原 `read_file` schema 纠错 |
| P2 retrieval commit window | Harness 注册只读 recovery handler；先读 route cache，缺失时走未知非幂等中断 | 已提交窗口 provider 只执行一次；缺失窗口 provider 执行零次 |
| P2 template multiplicity/order | 先排序 expected rows，再逐项非重叠消费；无排序也保留 multiplicity | 无序源→有序输出通过；两条重复源不能由一个输出行满足 |
| P2 empty aggregate | 空 `minimum/maximum` 明确返回 unresolved | 两种算法均不抛异常 |
| P2 stream close | peer、redirect、HTTP error、body bound、成功路径统一 `finally: close()` | 503 `raise_for_status` 后 response 已关闭 |

全量结果为 `245 passed`。这些整改只改变 ownership、证据完整性、恢复和边界处理，不调整 R9 数据、阈值、
工具 expected 或模型 prompt 的任务语义，因此没有借机重跑失败 case。
