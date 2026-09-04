# Tavily Key Pool Health v1 预注册

## 目标与范围

对 `.env.local` 中当前 30 枚 Tavily key 做一次固定、顺序、单请求健康检查，为用户明确授权的无效 key 删除提供证据。明文 key 不进入实验目录、日志或终端输出。

## 固定探测

- Endpoint：`POST https://api.tavily.com/search`；
- Query：`RWKV`；
- 参数：`search_depth=basic`、`max_results=1`、`include_answer=false`、`include_raw_content=false`、`include_images=false`、`topic=general`；
- 每枚 key 恰好一次，不重试，不并发；
- 输出只记录 1-based ordinal、SHA-256 前 16 位 credential ID、状态类别、HTTP 状态与成功响应 SHA-256。

## 固定分类与删除规则

- `usable`：HTTP 200、JSON object 且含 `results` list；
- `permanent_unavailable`：HTTP 401/402/403/432；
- `temporary_or_uncertain`：HTTP 429、5xx、网络异常、超时或 200 但响应契约无效；
- 仅删除 `permanent_unavailable`；`temporary_or_uncertain` 不得删除；
- 如果没有 `usable`，不得把 key pool 清空。

## 完整性门槛

- 输入 key 数必须为 30 且去重后仍为 30；
- 每个 ordinal 恰好产生一条结果；
- 实验目录不得包含任一明文 key；
- `.env.local` 必须被 Git 忽略且权限为 0600。
