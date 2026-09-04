# Tavily Key Pool Health v2 预注册

## 目标

对用户本轮提供并写入 `.env.local` 的 17 枚 Tavily key 做一次固定、顺序、单请求健康检查。明文 key 不进入实验目录、日志或终端输出。

## 固定探测与分类

- Endpoint：`POST https://api.tavily.com/search`；query=`RWKV`；`search_depth=basic`；`max_results=1`；不请求 answer、raw content 或 images。
- 每枚 key 恰好一次，不重试、不并发；只记录序号、SHA-256 前 16 位 credential ID、HTTP 状态、分类和成功响应摘要。
- HTTP 200 且 `results` 为 list：`usable`。
- HTTP 401/402/403/432：`permanent_unavailable`，检查完成后从 `.env.local` 删除。
- HTTP 429、5xx、网络异常、超时或响应契约无效：`temporary_or_uncertain`，本轮不删除。
- 如果没有 `usable`，不得清空 key pool；Bing RSS 与 DuckDuckGo HTML 继续作为回退。

## 完整性门槛

- 输入和唯一 key 数均为 17；每个序号恰好一条结果。
- `.env.local` 被 Git 忽略且权限为 0600。
- 实验结果不包含任何明文 key。
