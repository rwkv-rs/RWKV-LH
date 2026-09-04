# 三阶段 State Tuning 预注册修正：vLLM state 矩阵方向

日期：2026-08-26（修正后的在线复评前）

## 原始错误

RWKV-PEFT 的 state 参数 `blocks.<layer>.att.time_state` 表示递归核内部的 `[V,K]`
矩阵。FLA 训练 wrapper 因其公开 `initial_state` 内存契约为 `[K,V]`，调用前执行
`time_state.transpose(-2, -1)`；FLA 核计算时再按 `[V,K]` 读取该内存，因此核内部仍是
原始参数方向。

旧 vLLM adapter 错误地把这个 wrapper 级转置当作推理 state 的固有布局，也对 checkpoint
再次执行了 `transpose(-2, -1)`。vLLM 的 WKV 核直接把 state 内存按 `[V,K]` 使用，所以部署
实际加载了学习矩阵的转置。

## 可复核证据

固定非对称随机 64×64 state、隔离 token-local update 后的核级比较：

- RWKV-PEFT/FLA wrapper 与原参数内部方向：cosine `0.9999975562`，mean absolute error
  `0.0000481453`；
- vLLM 直接加载原参数：cosine `0.9993027449`，mean absolute error `0.0040044594`；
- 旧 adapter 转置后加载：cosine `0.2380073071`，mean absolute error `0.0308357086`。

诊断脚本为 `temp/validate_rwkv_state_orientation_contract.py`，远端结果为 Stage 1 run 下的
`state_orientation_fla.json` 与 `state_orientation_vllm.json`。

## 修正规则

adapter 必须把 checkpoint tensor 直接复制到 vLLM `[V,K]` state，不再转置。修正后的 adapter
SHA-256 为 `be0523b8abb557b8cdbbc22c4cc8dd927b2d07d675afba25b8702897a485bec2`，systemd
preflight 同步固定该摘要。

所有使用旧 adapter SHA
`853df387c2ea587819e24bdba95e450eec7f2a5fff8d069f0b4764639d914644` 的 tuned-state 在线
评价均标记为 `INVALID_wrong_state_orientation`，不能作为模型能力或调参结论。checkpoint 训练、
loss、tokenizer/BOS 验收不受影响。

修正后必须先重新评价 Round1 parent，再判断 Stage 1 数据是否仍对应真实残差；随后以同一修正
adapter 评价 Stage 1 child。原有 temperature、seed、评价集、parser 和通过门保持不变。
