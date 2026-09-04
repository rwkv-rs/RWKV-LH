# NET-SEL-2P9-S16 结果

日期：2026-08-28  
状态：拒绝接入

## 实验问题

验证非对称组合：compact query 使用 S2 state，tool description 保持 S8 的 zero-state 锚点。数据、头结构、随机种子和阈值均按 S16 预注册冻结。

## 固定产物

- head SHA256：`5f887750fd7c2d8c787a98d26c371ff73eed910884d041af9584a8dec00258ac`
- 完整指标：`run_s16_query_state_tool_anchor_head/TRAINING_REPORT.json`

## 结果

- 25 路 test accuracy：`0.2240000`
- macro-F1：`0.1635723`
- boundary accuracy：`0.0666667`
- natural dev：`149/176 = 0.8465909`
- connector natural dev：`64/64`
- ordinary web：`6/16`
- mixed local-first：`33/48`
- privacy local-first：`46/48`
- test 上 `read_file`、`web_search`、`connector_lookup` recall 均为 `0`
- RWKV 文本生成调用：`0`；sampling 调用：`0`

所有综合门仍失败，因此未读取外部 ECRA，未进入在线流程。

## 根因与结论

仅移动 query 表示也无法与 zero-state tool anchor 对齐。S2 对自然 connector 的局部增益不能弥补 25 路工具语义坐标的系统性破坏。功能 state 必须用与实际 serving 完全一致的“任务 + 功能描述”协议训练和比较，不能跨协议借用。

