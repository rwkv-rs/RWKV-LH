# RWKV-LH × ECRA Contract Graph v2 route canary protocol r2

状态：运行前冻结；替代已中止的初始运行协议

日期：2026-08-25

输入 case、模型、架构、并发、预算、指标和门槛全部沿用 `PROTOCOL.md`。
唯一整改是增加固定的 `rwkv-lh.ecra-route-goal.v1` route-only 包装：

- 保留原始用户任务全文，不提供 expected tool/category/answer；
- 要求执行该任务所需的最小工具序列；
- 成功的 synthetic evidence envelope 只证明路由完成，不评价事实答案；
- sensitive/tool-untrusted 出站的一次 typed rejection 证明隐私路由完成；
- 禁止为获取夹具不存在的事实内容而重复调用同一路由。

这消除了 frozen route fixture 与 factual Reviewer 的评价对象错配，不改变动作答案或阈值。

输出目录：`variant_b_contract_graph_r2`。命令除输出目录外与 `PROTOCOL.md` 相同。
