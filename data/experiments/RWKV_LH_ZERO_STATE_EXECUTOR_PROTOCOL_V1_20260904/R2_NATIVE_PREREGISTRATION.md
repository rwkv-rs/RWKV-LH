# R2 native zero-State 复跑预注册

在 R1 结果产生后登记。沿用 `PREREGISTRATION.md` 的全部四个样本和 `4/4` 门槛，唯一变更为使用生产工厂 `create_model_session()` 加载 `RWKV_LH_EXECUTOR_*` 设置，并要求每条 decision 的 transport 必须为 `native_rwkv_state`。若服务不能提供 native state，测试直接失败，不回退 prompt replay。

R2 输出固定写入 `R2_RESULT.json`，不覆盖 R1。
