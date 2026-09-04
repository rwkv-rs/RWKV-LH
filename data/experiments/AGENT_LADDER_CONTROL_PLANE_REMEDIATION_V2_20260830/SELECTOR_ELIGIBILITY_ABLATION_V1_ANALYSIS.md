# Selector Eligibility Ablation V1

- 固定原始 Selector 尝试：283。
- A 全局 argmax 结构不可执行：122。
- B atom allowset 结构不可执行：103。
- C allowset + minimum-actions final gate 结构不可执行：0。
- C 相对 A 改变选择：122。
- 所有 arm 使用同一原始 25 维 logits；未重新调用模型、未修改来源选择或 RWKV 输出。
