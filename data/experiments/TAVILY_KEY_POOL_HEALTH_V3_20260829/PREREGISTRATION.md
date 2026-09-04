# Tavily Key Pool Health V3 预注册

登记时间：2026-08-29；发生在当前 `.env.local` 29 枚唯一 Tavily key 的本轮健康调用之前。

## 固定探测与分类

- Endpoint：`POST https://api.tavily.com/search`；query=`RWKV`；`search_depth=basic`；`max_results=1`；不请求 answer、raw content 或 images。
- 29 枚唯一 key 按配置顺序各调用一次，不重试、不并发；只保存序号、key 的 SHA-256 前 16 位、HTTP 状态、分类和响应摘要，绝不保存或输出明文凭据。
- HTTP 200 且 `results` 为 list：`usable`。
- HTTP 401/402/403/432：`permanent_unavailable`，完成审计后从 `.env.local` 删除。
- HTTP 429、5xx、网络异常、超时或响应契约无效：`temporary_or_uncertain`，本轮保留但不当作可用证明。
- 如果没有 usable，不清空 key pool；产品仍保留 Bing RSS 与 DuckDuckGo 回退。

## 门槛

- 输入和唯一 key 数均为 29，每个序号恰好一条结果。
- `.env.local` 被 Git 忽略且权限为 0600。
- 报告与实验目录不含任何明文 key；至少一枚 usable。

