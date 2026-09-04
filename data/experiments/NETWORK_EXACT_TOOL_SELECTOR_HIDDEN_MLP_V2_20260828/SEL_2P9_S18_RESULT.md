# NET-SEL-2P9-S18 结果

日期：2026-08-28  
状态：历史回归失败；拒绝接入

## 实验问题

在 `connector_lookup` 获授权时，以 S6 的 zero-state task hidden 训练一个 CONNECTOR/OTHER 功能头；若输出 OTHER，再交给 S8 在授权菜单内选择。训练集固定为 2,000 行：690 connector 正例、1,310 个分组 hard negative。

## 固定产物

- 数据集：`data/datasets/rwkv_lh_network_connector_function_s18_v1`
- cases SHA256：`1983f1b0c2195eadf08b17a1747ac863225d09c7d3f80f59e29453c0da76c662`
- head SHA256：`0478e21a1b4f6794816006bb72113a5a072544014b55d1d072a2542a3e3e2bba`
- 内部结果：`run_s18_connector_function_head/RESULT.json`
- 历史回归：`run_s18_connector_function_head/ECRA120_HISTORICAL_REGRESSION.json`
- ECRA 角色修正：`SEL_2P9_S18_PREREGISTRATION_AMENDMENT_ECRA_STATUS.md`

## 内部结果

- binary dev connector precision/recall：`0.9894737 / 1.0`
- binary test connector precision/recall：`0.9677419 / 1.0`
- binary test OTHER recall：`0.9986111`
- 合并后 test accuracy：`0.9280000`
- macro-F1：`0.9276000`（完整精度见 JSON）
- boundary accuracy：`0.9777778`
- natural dev：`176/176`
- mixed/privacy connector false positive：`0`

内部预注册门全部通过。

## ECRA120 历史回归

ECRA 已在早期 S9 被完整读取，因此本轮只作为历史回归，不再声称盲测。结果暴露严重分布偏移：

- deterministic：`0/15`，15 次全部选联网
- local-only：`0/30`，28 次选联网
- mixed local-online：`0/20`，20 次选联网
- privacy：`1/10`，9 次选联网
- public web：`1/25`
- structured connector：`20/20`
- local-only network false positive：`28`
- web/connector macro-F1：`0.1862908`
- active integration authorized：`false`

## 根因与结论

该头判别的是通用 task hidden；`connector_lookup` 的名称和描述只存在于 MLP 外部，RWKV 前向没有看到被判断的功能。因此它可以记住内部任务分布，却无法形成“这个任务是否匹配这个功能”的可迁移比较。S18 不接入。S19 改为在同一次 RWKV 前向中显式放入 compact objective 与精确 function name/description，并对 zero-state 与 connector 专用 state 做同协议因果消融。

两个阶段均未生成、诱导、修改、删除、修复或隐藏任何 RWKV 原始文本；所有 raw logits 均保留。
