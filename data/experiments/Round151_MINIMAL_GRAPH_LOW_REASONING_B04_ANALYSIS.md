# Round151 Minimal Graph + Low Reasoning B04 分析

日期：2026-08-23

## 结论

Round151 r2 **未通过 strict gate，但传输整改通过**：初始 Planner 单次物理 HTTP attempt 在 26.1 秒
内返回，未再出现 HTTP 500；5 个 RWKV work atoms 完成后 workspace external PASS。最终状态为 FN，
根因是增量 graph patch 的本地 existing-ID generator 被重复消费。

原始目录：`data/experiments/Round151_minimal_graph_low_reasoning_B04_r2_20260823/`。

## 量化结果

- external=true，agent completed=false，Final 为空；RWKV requests=10，actions=5，protocol rejection=0。
- 初始 Planner：1 attempt，prompt 1492 / completion 1337 / reasoning 516 tokens，26.1 秒。
- Reviewer：1 attempt，准确识别“只观察 destination digest、没有 source digest 对照”，4/5 obligations
  satisfied，copy-byte-equality insufficient。
- correction Planner 连续 3 个响应都引用合法既有 obligation
  `obl_copy_source_unchanged_b04`，但本地误报 unknown，造成 3 次无效语义调用。

## 根因

`ContractGraphPatch.create` 对 `existing_obligation_ids` / `existing_node_ids` 接受任意 iterable，却先在
redefinition 检查中 `set(...)` 消费一次，随后又在 known-reference 集合中消费第二次。OpenAI adapter
传入 generator，所以第二次为空；tuple 单测没有覆盖该接口形态。

整改为入口一次性规范化并冻结 existing IDs，后续所有校验复用同一 tuple；新增 one-shot generator
回归。该修复影响所有增量 patch、依赖引用和 obligation repair，不含 B04 特判。
