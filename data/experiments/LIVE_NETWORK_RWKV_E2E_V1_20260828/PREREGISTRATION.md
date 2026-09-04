# Live Network RWKV E2E v1 预注册

## 目标

验证现有 13.3B RWKV Agent 能否自主选择真实联网工具、消费精确外部证据、继续调用本地 Harness
写入产物并完成任务。该轮不使用强 Planner，不启用 State Router，不做 state tuning。

## 固定身份

- 模型服务名：`rwkv7-g1i-13.3b-rwkv-lh-stage8-r3-step1700-bos-ctx2496`；
- 13.3B base SHA256：`5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`；
- 初始 state SHA256：`70cea049360422e94c43d3c112693fc148e88b4cde957a21a690f8b2309627d8`；
- 网络策略：`auto_public`；
- 工具披露：当前 `progressive` 路径；
- HTTP retry：1；`return_token_ids=true`；
- 数据集：`data/datasets/rwkv_lh_live_network_rwkv_e2e_v1/cases.jsonl`；
- Provider：本地 `local-web-tavily-bing-ddg-v1` 与既有 public structured connector；
- 本轮运行时 Tavily key pool 已确认无剩余可用 key，通用发现会显式记录 disabled 后使用 Bing RSS；显式 URL 不经过搜索 provider，直接由安全 Fetcher 抓取；
- 每条用例使用独立 workspace、SQLite、snapshot 与 hash-chain raw journal。

## 固定用例

1. RWKV 读取一个用户明确给出的公网 URL，形成证据后写入 Markdown；
2. RWKV 查询公开 GitHub 仓库结构化信息，形成证据后写入有效 JSON。

## 固定机械指标

每条用例必须同时满足：

1. Controller 状态为 `completed`，返回 final 与持久化 RWKV final 完全相等；
2. 至少一次预注册的 network operation 成功；
3. network action 的 external envelope 为 `evidence_committed` 且至少一条 evidence；
4. 目标文件存在，并满足预注册文本或 JSON 字段约束；
5. 每次生成均存在先于解析/执行提交的 hash-chain `model_session_generation_returned`；
6. raw text、UTF-8 SHA256、token IDs、finish reason 被原样记录，`postprocessed=false`；
7. HTTP 请求次数固定为 1，不使用 guided/constrained decoding、重排、输出修复或语义重试。

## 通过条件

- 2/2 用例全部通过全部指标；
- 网络 Provider 与 Harness 相关完整测试、项目完整回归均通过；
- 任一失败必须扩展同类路径检查并修复通用根因，不得对用例加特判或修改阈值。
