# Selector Hidden+MLP S0 结果

## 冻结产物

- 数据集：`rwkv_lh_network_exact_tool_selector_v2_4`，7500 行，train/dev/test=6000/750/750。
- 数据 SHA-256：`78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc`。
- 2.9B vLLM 权重 SHA-256：`01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`；源 PTH SHA-256：`ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。
- 正式提取固定 batch=1，共 7500 行/469 shards，token 903–963；RWKV text generation=0，sampling invocation=0。

## Synthetic test

- last hidden：accuracy=1.0，macro-F1=1.0，search boundary accuracy=1.0，min per-class recall=1.0；全部门槛通过。
- mean hidden：accuracy=0.9933333397，macro-F1=0.9933530043，search boundary accuracy=0.9888888597，min per-class recall=0.9666666667；全部门槛通过。
- 两个 portable JSON head 的 raw-logit replay 均保持 argmax，最大绝对差分别为 `4.3115e-6` 与 `3.3495e-6`。

## ECRA 45-case 固定网络边界回归

- last hidden：accuracy=0.5111111111，web_search recall=0.88，connector_lookup recall=0.05；失败。
- mean hidden：accuracy=0.0888888889，web_search recall=0.04，connector_lookup recall=0.15；失败。
- last 的 20 条 connector 全量错误分布：1 正确；13 错为 web_search，5 错为 replace_text，1 错为 check_command。
- last 的 25 条 web 全量结果：22 正确；2 错为 check_command，1 错为 ABSTAIN。
- 两个候选都返回完整 25 raw logits，无 mask、规则改写、后处理或生成文本。

## 结论与全局影响

- S0 不得接入 product runtime。合成 test 的高分不能代表自然指令迁移质量。
- 根因不是单一 ECRA 用例：同类 connector 的 19/20 全面失败。v2.4 每类虽有 300 个 surface family，但核心 operation objective 只有 6 个英文合同模板；MLP 学会了合成边界，却没有得到足够稳健的自然中英结构化来源表征。
- 失败影响所有需要 GitHub/PyPI/npm/crates.io/DOI/arXiv/结构化天气数据的入口；若接入会把大量 connector 任务错误交给 general web 或本地文本操作。
- 按预注册进入单一 Selector state S1。保持同一输入、MLP、test、ECRA 数据、指标和门槛；不使用规则路由、logit mask 或 13.3B 复核掩盖问题。

