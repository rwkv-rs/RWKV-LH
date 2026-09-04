# Selector 2.9B Batched Hidden Equivalence v1

- 冻结日期：2026-08-28（Asia/Shanghai），运行前登记。
- 输入：v2.4 数据集中每隔 300 行选一行，共 8 行；顺序固定。
- 模型/artifact/engine/WKV 与 `SELECTOR_2P9_HIDDEN_EXTRACTION_PREFLIGHT_V1_20260828` 完全相同。
- candidate：8 行按 token 长度排序、right pad 到 batch 内最大长度，一次 forward；last 取各自行最后真实 token，mean 只平均各自真实 token。
- reference：相同 8 行逐条 batch=1 forward。
- last 与 mean 都固定比较每个 FP32 元素和 cosine。
- 通过门槛：shape/token count 完全相同；每种 feature 的全局 max_abs_diff ≤ 0.002；每行 cosine ≥ 0.999999；全部 finite；padding token 不进入 pooling。
- 任一失败则正式 7500 行只能 batch=1，不得放宽同一次实验门槛。
