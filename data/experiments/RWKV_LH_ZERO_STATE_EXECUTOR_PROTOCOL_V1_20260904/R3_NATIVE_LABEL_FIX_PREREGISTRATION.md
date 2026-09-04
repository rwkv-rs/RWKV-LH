# R3 native transport 名称修正预注册

沿用 R1/R2 的四个样本、采样、768 token 上限和 `4/4` 门槛。唯一变更是把已由源码复核的 native transport 标识固定为 `native_rwkv`。输出写入 `R3_RESULT.json`；不覆盖 R1/R2，不修改模型 prompt、parser、参数 normalization 或 State。
