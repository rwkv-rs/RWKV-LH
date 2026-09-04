# 三阶段 State Tuning 预注册修正：BOS 因果对齐

日期：2026-08-26（Stage 1 restart 前）

## 修正原因

Stage 1 首次启动后，前 78 steps 的 loss 已接近 `1e-5`，但同一 parent state 在固定 selector
dev 上仍为 0/79 operation。沿训练输入和 vLLM 输入逐 token 检查发现：

- vLLM `RWKVTokenizer.encode(..., add_special_tokens=True)` 会返回 `[0, *prompt_tokens]`；
- RWKV-LH 的 `/v1/completions` 请求明确设置 `add_special_tokens=True`；
- RWKV-PEFT 原 JSONL dataset 只编码 `prompt + target`，没有前置 BOS 0。

因此 state 参数在训练中直接消费 `System:`，在线推理中却先消费 BOS 0。首次 Stage 1 运行不是
可比较实验，已在 78/500 steps 中止并移动到
`stage1_selector/INVALID_missing_bos_alignment/`；它的 checkpoint（尚未产生）和 loss 不用于任何
后续选择或结论。

## 冻结修正

RWKV-PEFT 增加显式 `--jsonl_bos_token_id`，默认 `-1` 保持旧行为。Stage 1 及后续与当前 vLLM
对齐的训练必须设置 `--jsonl_bos_token_id 0`。该选项只允许 JSONL `target_suffix` 路径；token id
必须在 vocab 内。Dataset 必须形成：

```text
sequence = [BOS=0] + prompt_tokens + target_tokens
x = sequence[:-1]
y = mask(sequence)[1:]
```

第一个 target label 的输入必须是最后一个 prompt token，BOS 自身和全部 prompt label 必须被
mask。远端 authoritative `MyDataset` 已对全部 579 条逐项验证：

- BOS 0 出现在每个 `x[0]`；
- first target causal index 100% 对齐；
- target suffix exact label match 100%；
- historical Assistant supervised token 0；
- 新最大长度 2255，仍小于 capacity 2497；
- failure count 0。

除加入 BOS 0 外，Stage 1 的 parent state、500 条训练数据、79 条 dev、LR、steps、seed、final
checkpoint 规则和通过门全部不变。修正后的 run 从同一个 Round1 parent state 重新开始，不从
78-step INVALID state 继续。
