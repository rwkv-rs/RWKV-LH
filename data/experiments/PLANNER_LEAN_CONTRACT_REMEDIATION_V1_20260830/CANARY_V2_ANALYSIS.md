# Planner 精简契约 Canary V2 分析

- production 结果：`run_planner_only_canary_v2/RESULT.json`
- 结果 SHA256：`7973411b391d188d6bc5932b442653964e36d654db9ecc96eec4df56b8bad3ed`
- operation authority 复算：`run_planner_only_canary_v2/AUTHORITY_REANALYSIS.json`
- 复算 SHA256：`19ee5965752717a5132fd06e9dfadde43fac86121d27dc7fcd33202be7dc59c7`
- 补充预注册 SHA256：`8df6ed397efe593b28271f5465a9badbba727a91463acc42b4113cbd96462bca`

## 固定条件

与 V1 完全相同的 5 个公开任务、`gpt-5.4-mini`、显式 `reasoning_effort="none"`、temperature 0.1、无 fallback、无 transport retry、无 semantic repair、无 plan cache。未调用 RWKV、未使用 GPU、未读取隐藏验收。

## 结果

- HTTP 200：5/5。
- 单 JSON 对象：5/5。
- production strict JSON Schema 合法：5/5。
- production contract 编译：5/5。
- 原始图 mutation→传递 verify：5/5。
- 编译图 mutation→传递 verify：5/5。
- 逗号/引号拼接伪路径：0。
- 具体 Harness operation 选择：0/5；authority respected 5/5。
- 平均 production 请求：1769.4 token。
- 平均原始输出：3286.4 UTF-8 bytes。
- 平均 API 延迟：14390.9 ms，仅作描述统计。

所有 case 都由 Controller 编译 capability/evidence/freshness/budget，并机械追加 frozen finalizer。2 个 case 的统一 verifier 缺少部分上游 mutation 根，Controller 按依赖图传播只读范围；没有生成业务内容、工具或参数。

## Authority 复算说明

初始 `RESULT.json` 的子串检查把 evidence kind `public_web_search_result` 错报为选择 `web_search`，因此其中 `planner_authority_respected=4` 不能作为最终 authority 指标。既有 V2 消融和本次复算都使用固定算法：递归遍历 JSON 字符串叶子，只有字符串值完整等于 24 个 authoritative ActionDefinition 名称时才算具体 operation 选择。复算为 5/5 无命中。原 RESULT 与所有原始输出均未修改。

## 原始输出 SHA256

- L2 repair：`f79cb151c6e3de06319d608ee641cfcc6e90c7f717d0ffc9bf2ed95876f59c06`
- L3 web：`96ecb37b2b1793321786dd6ad1ba3fae4283f25d44e35aeb5f197c3e57da4694`
- L3 queue：`89475bb814a598ddf5ac23c85c87162159201d36f4f22acbd84e59431ff51fc5`
- L4 ledger：`b88b24976d800003b2ae1c59994e0a8cd05b23e9f0662d1d9d8a78f0d0d03923`
- L5 RWKV：`b82dfffaf9554feb01c7147c016c5edd31f775f31d746c7f0dbd4c032fb895fa`

