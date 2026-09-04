# INVALID：省略 reasoning_effort，不是正式配置

- 终止时间：2026-08-30
- 状态：人工终止，退出码 130；不得用于方案选择或发布结论。
- 原因：脚本把正式配置中的显式 `reasoning_effort="none"` 错误实现为删除该请求字段。
- 已完成样本：`AGENT-LADDER-L2-REPAIR01` 的 A/B/C，以及 `AGENT-LADDER-L3-WEB01` 的 A；下一请求在等待响应时终止。
- 关键诊断：L2 的 C 获得 HTTP 200，但上游在 assistant content 前插入 `<think>...</think>`，因而不是单个 JSON 对象；该现象仅归属于错误配置臂。
- 原始请求与强模型响应文件保留不动；没有 RWKV 调用，没有隐藏验收读取，没有产品服务修改。
- 当时脚本 SHA256：`d11bc05cc58110b7dad5fae3054c4ab53fe5ff8b6ad28798a6cac1ab97177bc9`。

