# Live Network Capability v1 预注册

## 目标

验证当前仓库内已经存在的联网内核是否能在 WSL 的真实运行环境中完成公网访问。该轮只定位
Provider/Fetcher/Harness 根因，不调用 RWKV，不评价模型是否会选择联网工具，也不修改评价口径。

## 冻结输入

- 数据集：`data/datasets/rwkv_lh_live_network_preflight_v1/cases.jsonl`；
- 7 条固定用例，覆盖 2 条 exact URL、1 条通用网页发现、GitHub、PyPI、Crossref、天气；
- `web_search` 和 `connector_lookup` 均通过 `LiveRetrievalBackend` 原生路径执行；
- 每个用例使用独立的不可变 snapshot/route 目录，避免先前缓存掩盖真实网络问题；
- 禁止把失败结果改写为成功，禁止自动改 query、换预期或在运行后降低阈值。

## 固定指标

本轮使用机械精确指标，不使用主观相似度：

1. `status_exact_match`：Envelope 状态必须等于预注册状态；
2. `minimum_record_recall`：记录数达到预注册下限；
3. `expected_host_match`：指定主机的用例必须命中该主机；
4. `structured_field_presence`：指定结构化字段必须存在；
5. `snapshot_integrity`：每条 Evidence 的 snapshot digest 能回读且哈希一致；
6. `request_binding`：Envelope 的 request digest 与原 operation/arguments 完全一致。

## 通过条件

- 7/7 `status_exact_match`；
- 7/7 `minimum_record_recall`；
- 所有适用的 host、structured field、snapshot、request binding 检查完全通过；
- 不出现 `provider_unavailable`、空证据伪成功或缓存跨用例复用。

若失败，只报告根因并整改通用路径；不得对单条用例加特判。整改后仍使用同一数据集、参数和指标。
