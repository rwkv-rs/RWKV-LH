# Planner 精简契约 Canary V1 分析

- 结果：`run_planner_only_canary_v1/RESULT.json`
- 结果 SHA256：`8b6346c225088813ce3f99b1908d32848df3f3ea30f514825b4440a5baf07894`
- 固定条件：5 个公开任务、`gpt-5.4-mini`、`reasoning_effort="none"`、temperature 0.1、无 fallback、无 transport retry、无 semantic repair、无 plan cache。
- 未调用 RWKV、未使用 GPU、未读取隐藏验收；每份强模型原始 assistant content 按原字节保存。

## 结果

- HTTP 200：5/5。
- 单 JSON 对象：5/5。
- production strict JSON Schema 合法：5/5。
- 具体 Harness operation 越权：0/5。
- 原始图中每个 mutation 均有传递可达 verify：5/5。
- 逗号/引号拼接伪路径：0。
- 本地 production contract 编译：1/5。

4 个编译失败属于同一全局类型：工作节点的 `kind=synthesize` 与本地只允许 `synthesize + local_read_only` 的 effect 组合不一致。

| 任务 | synthesize effect | 语义 |
|---|---|---|
| L2 repair | `public_read_only` | 在验证后汇总修复报告 |
| L3 web | `local_process_read_only` | 在修改前形成实施计划 |
| L4 ledger | `local_process_read_only` | 形成设计或汇总验证状态 |
| L5 RWKV | `workspace_mutation` | 形成内容计划，后续另有真实 mutate 节点 |

原始输出表明强模型正确区分了调查、真实修改和验证链，但把“综合信息/形成计划”统一称为 synthesize，并用它所依赖或面向的环境给 effect。根因不是 JSON、路径、依赖或工具选择，而是 production Schema 对工作阶段开放了一个实际上只应保留给最终呈现节点的 kind。

## 指标说明

V1 脚本的 `compiled_all_mutations_have_transitive_verify=5` 对 4 个未编译 case 使用了空集合的真值，因此该汇总字段无效；不可将它解释为 5 个 production patch 均已编译。真实编译成功数以 `compiled=1` 为准。原始图的 `raw_all_mutations_have_transitive_verify=5` 独立有效。

## 原始输出 SHA256

- L2 repair：`e1c9d2cfdb412ff84d63a3894f45c23bbd1f05c008ea9d1545f4d9ffd2ab242c`
- L3 web：`72fec9ab9ef25cde7f63821ee0490427fa3627246b2eb7fa73701e5b5222e06d`
- L3 queue：`71cfab093a3958fe87ce5db5744af7001cb696f2b508f12df91d6e1ab999c904`
- L4 ledger：`ecbee2107a0e49468db7dca0a4dc0c25ccc8a096cadae3342a0937bb03731db4`
- L5 RWKV：`99963e519b5e6ad57e58302261a448df00f200c275bb1ff5f27cb40659ef44f6`

