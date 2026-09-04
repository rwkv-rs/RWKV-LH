# Live Tavily Provider v1 预注册

## 目标

验证 RWKV-LH 本地检索内核以 Tavily 为通用网页发现主源，并保留 Bing RSS、DuckDuckGo HTML 为同一 `web_search` 事务内的机械兜底。ECRA 只作为来源边界参考，不导入其 Planner、AgentState、查询改写、排序或工具状态机。

本轮不调用 RWKV，不评价工具选择能力；只验证 provider/fetcher/snapshot 路径。Tavily 只发现 URL，不生成答案，最终事实证据必须来自本地抓取的原始网页。

## 冻结输入与参数

- 数据集：`data/datasets/rwkv_lh_tavily_provider_live_v1/cases.jsonl`；
- 固定查询：`Python Packaging User Guide pyproject.toml`；
- `max_results=3`；
- Tavily 固定参数：`search_depth=basic`、`topic=general`、`include_answer=false`、`include_raw_content=false`、`include_images=false`；
- 固定 provider 顺序：direct URL（仅显式 URL）→ Tavily → Bing RSS → DuckDuckGo HTML；
- 查询只允许首尾去空白，不允许添加、删除、替换或重排查询词；
- 运行目录：`data/experiments/LIVE_NETWORK_TAVILY_PROVIDER_V1_20260828/run_r1/`，首次运行后不得覆盖。

## 固定指标

1. `status_exact_match`：Envelope 必须为 `evidence_committed`；
2. `minimum_record_recall`：至少 1 条 EvidenceRecord；
3. `tavily_primary`：首个 provider attempt 必须是 `tavily-search-api` 且 `status=ok`；
4. `no_fallback_used`：成功用例不得出现 Bing/DDG attempt；
5. `original_page_evidence`：Evidence URL 不得是 Tavily/Bing/DDG 搜索端点，snapshot 必须来自实际结果页；
6. `snapshot_integrity`：每条 exact span 必须能以 snapshot clean text 校验；
7. `request_binding`：Envelope request digest 必须和固定输入完全一致；
8. `credential_isolation`：`.env.local` 被 Git 忽略且权限为 0600；结果、route、snapshot 中不得出现任一明文 key；attempt 只允许 16 位 SHA-256 前缀 credential ID；
9. `provider_response_digest`：成功 Tavily attempt 必须保存 64 位响应 SHA-256，不保存 provider 生成的 answer/snippet 作为事实证据。

## 通过条件

上述 9 项全部通过。失败后只允许整改通用实现，再使用同一数据、参数和指标运行 `run_r2`；不得覆盖 `run_r1`，不得修改本协议改善结果。
