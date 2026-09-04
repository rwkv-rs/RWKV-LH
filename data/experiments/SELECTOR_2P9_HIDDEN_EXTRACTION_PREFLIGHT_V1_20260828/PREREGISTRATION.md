# Selector 2.9B Hidden Extraction Preflight v1

- 冻结日期：2026-08-28（Asia/Shanghai），运行前登记。
- 模型源 SHA-256：`ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。
- artifact runtime weights SHA-256：`01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`。
- 引擎 revision：`67f0c5996c50dca0ad779da545cb491527de988f`，必须 clean。
- 配置：BF16 weights、WKV fp16、batch=1、max_tokens=2048、CUDA direct model。
- 固定输入：v2.4 dataset 第一行的完整 `NetworkSelectorInput.render()`；输入 digest 必须与 dataset 登记一致。
- 同一次 forward 分别读取 `final-layer-last-real-token` 与 `final-layer-all-real-token-mean`。
- 通过条件：两种 feature 都是 `[1,2560]` FP32、全部 finite、token_count 在 1..2048、model source/weights/config/engine identity 精确匹配、两个 feature protocol 精确匹配，且不调用生成/采样接口。
- 任一失败则不允许开始 MLP 特征提取或训练。
