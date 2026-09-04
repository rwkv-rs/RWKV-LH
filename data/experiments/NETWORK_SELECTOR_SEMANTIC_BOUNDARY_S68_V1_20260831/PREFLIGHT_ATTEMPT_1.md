# S68 feature preflight attempt 1

第一次运行在首个模型前向前被 `local model artifact engine revision mismatch`
拒绝。原因是 local backend 把模型转换时引擎 revision
`67f0c5996c50dca0ad779da545cb491527de988f` 与当前派生执行引擎 revision
`0501caa628967103490507d734f6a5efaf165794` 当成同一变量。

本次没有生成 hidden、logit、采样文本或 RWKV 输出；train/dev 行按协议读取，test
仍在 JSON 解析前跳过。空 staging 目录保留并重命名为
`run_zero_train_dev_features.failed_preflight_model_revision_20260831`。

整改不是放宽校验：backend 显式区分 artifact revision 与 runtime revision；只有在
提供哈希固定的 runtime-derivation manifest，且其引用的真实模型 source-validation
仍为 passed/eligible、重复路径与 state round-trip 全通过时，才允许派生引擎加载原
artifact。
