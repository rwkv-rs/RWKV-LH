# Network Exact-Tool Selector v2.4 Feature Extraction v1

- 冻结日期：2026-08-28（Asia/Shanghai），正式提取前登记。
- 数据文件：`data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl`，SHA-256 `78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc`。
- 行数/顺序：严格按文件 7500 行，不抽样、不重排标签或 split。
- 模型源/引擎/artifact 与主预注册一致；runtime weights SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`。
- WKV=fp16、max_tokens=2048、正式 batch=1。
- batch=8 padding candidate 已在 `SELECTOR_2P9_BATCH_HIDDEN_EQUIVALENCE_V1_20260828/run_r1` 按预注册门槛失败，禁止用于本次正式 cache。
- 每行只做一次非生成 RWKV forward，同时保存 last-token hidden 与 real-token mean hidden，均为 FP32 `[2560]`。
- 每 16 行原子提交一个 shard；中断恢复时必须逐项验证 sample IDs、数据 SHA、模型 SHA、feature protocol、shape/dtype/finite，不能覆盖已验证 shard。
- 通过门槛：7500/7500 行，sample ID 唯一且顺序一致；两种 feature 均 `[7500,2560]` 等价分片、FP32、finite；token count 1..2048；engine/model/artifact identity 完全匹配；generated text/sampling count=0。
- 任一门槛失败，不允许训练或接入。
