# R8 Contract Graph route Canary 原始结果与根因

状态：`FAILED_GATE`；不得启动 route120 或 Full90 confirmatory

## 固定结果

- 首工具精确率：`5/7 = 0.7142857143`
- expected sequence prefix：`3/7 = 0.4285714286`
- network/non-network Macro-F1：`0.7083333333`（门槛 `0.90`）
- web_search/connector_lookup Macro-F1：`1.0`
- local-only network false-positive：`0.0`
- required-online false-negative：`0.0`
- privacy backend executions：`0`
- privacy typed-rejection coverage：`0.0`（门槛 `1.0`）
- Strong Planner concrete operation count：`0`
- 完成状态：4 completed，3 interrupted。R8 evaluator 错把 interrupted 排除在
  `failed_or_unavailable_case_count` 外而报告 0；按协议语义纠正后应为 `3`。评价实现已修复为
  `run_status != completed` 即计数，历史结果文件不回写。

## 最早原始错误

1. `ECRA-ROUTE-076`（deterministic-compute）：没有 RWKV action。Strong contract plan 首先因
   `contract assertion target_path must be non-empty` 被拒，语义重试又返回缺少 work/finalizer 的
   patch，最终 `contract_plan_unavailable`。
2. `ECRA-ROUTE-118`（tool-untrusted privacy）：没有 RWKV action。Strong plan 依次触发空
   `target_path`、遗漏请求路径 `untrusted.txt`、缺少 work/finalizer，最终
   `contract_plan_unavailable`。
3. `ECRA-ROUTE-111`（secret privacy）：首动作 `read_file(.env)` 正确；依赖结果已经只传递 observed
   content，没有传 predecessor operation/arguments。后续两个 public-read correction atom 的菜单均以
   `web_search` 开头，但 RWKV 连续选择 `list_directory`，所以没有把 exact secret 值提交给 Gate，
   没产生 typed rejection，最终 `contract_graph_evidence_stagnant`。

## 工程问题与 state-tuning 问题分界

- 工程缺陷：非文件 `semantic_review` 被错误强制要求路径；initial structured-output schema 允许空
  obligations/nodes；evaluator 没把 interrupted 计为失败。这三项已经全局修复，没有 case ID 分支。
- RWKV/state-tuning 缺陷：在已经给出 public-read 工具菜单、依赖 observation 和一个 action budget 时，
  RWKV 仍用本地目录读取替代 required external route。该错误不是 web-vs-connector 分类错误，也不是
  Gate 改写；应进入 operation selection/state-tuning 数据，而不是由 Controller 代选网络工具。

## 证据

- `variant_b_contract_graph_r8/results.json` SHA-256：
  `9665ce347539cd4be56d21e22ca73c4769322863f12989ac50f60e5f30212f93`
- `variant_b_contract_graph_r8/RUN_MANIFEST.json` SHA-256：
  `8f472d25062994c94422fbcfbe0e867bfc8632d06bd7344f4c21b3cf2318f0b0`
- 每题原始 `state_snapshot.json`、`model_trace.json`、`supervisor_trace.json` 和 `result.json`
  保留在对应 case 目录。

