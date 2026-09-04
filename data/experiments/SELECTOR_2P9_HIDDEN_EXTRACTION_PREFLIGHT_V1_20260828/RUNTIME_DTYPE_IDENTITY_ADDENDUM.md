# Runtime dtype identity addendum

`run_r1` 的 `configured_dtype` 检查验证的是 artifact `config.json` 的 `torch_dtype=bfloat16`，字段名不够精确；它不是对 CUDA GEMM tensor dtype 的声明。

固定 vllm-rwkv 在 `_preprocess_weights` 中把模型计算权重显式转换为全局 `DTYPE=torch.float16`，现有服务器 2.9B 服务也走同一 FP16 compute 路径。WKV profile 为 fp16。源 PTH 与 artifact 序列化仍保持 1062 个 BF16 tensor 数值不变。

身份字段从现在起拆为：

- `artifact_dtype=torch.bfloat16`；
- `runtime_compute_dtype=torch.float16`；
- `wkv_state_dtype` 由 execution profile 记录。

该修订只消除身份字段歧义，不改变 run_r1 的输入、前向、feature 数值或通过门槛。
