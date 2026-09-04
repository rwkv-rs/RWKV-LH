# R1 基础设施无效

R1 固定四例得到 `4/4`，证明当前格式转换、canonical parser、Executor-Args parser 和 Harness 参数规范化可接受四个首次输出；但运行记录中的 `decision.transport` 均为 `prompt_replay`。

根因是测试脚本直接调用了 `ModelSession()`，该构造器使用数据类默认设置，没有经过产品使用的 `create_model_session()`/`get_runtime_settings()` transport 选择。产品 Goal 模式要求 `native_required`，所以 R1 不进入产品 zero-State 指标。原始输出保留在 `RESULT.json`，不覆盖、不删除。

该错误与模型输出无关，且 R1 已达到 `4/4`，R2 只纠正 transport 构造，不改变样本、采样、token 上限、parser 或阈值。
