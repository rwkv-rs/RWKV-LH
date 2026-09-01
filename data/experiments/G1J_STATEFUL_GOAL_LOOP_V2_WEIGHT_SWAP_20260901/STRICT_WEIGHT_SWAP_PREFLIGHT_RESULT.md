# G1J 严格 weight-swap 服务预检结果

- 时间：2026-09-01。
- 状态：`inference_requests=0`；尚未产生模型质量结果。

## 最早失败

1. 13.3B 首次服务启动失败：`RWKV7ForCausalLM requires Model Runner V2`。这是启动脚本遗漏 `VLLM_USE_V2_MODEL_RUNNER=1` 的工程配置错误；R2 启动补齐现有生产参数，不改变模型输入或评价。
2. 2.9B Selector 首次服务启动失败：`network Selector fused head portable identity mismatch`。冻结 S60 Head 的 `portable_feature_identity.model_weights_sha256` 为 G1I artifact `01f39d...0444`，G1J artifact 为 `c1a316...866c`。该身份门正确阻止了跨权重复用 Hidden-MLP Head。
3. 13.3B R2 已成功加载权重并通过 `/v1/models`，但 `/v1/capabilities` 返回 HTTP 404。与当前 G1I 生产进程环境对照后，R2 缺少 `PYTHONPATH=/home/chase/chase/vllm-rwkv-g6-cmix-r7-native-state-v1-20260831` 和 `VLLM_PLUGINS=rwkv_lh_native_state`，因此 native-state 插件未加载；尚未发送推理请求。
4. G1J 2.9B R2 首次特征提取在读取任何模型前失败：远端项目缺少冻结 S60 dataset 文件。修复仅同步本地已登记的 `cases.jsonl`、`manifest.json` 和 `README.md`，同步后复核原 SHA-256；不生成或修改数据。

## 结论

原预注册的“严格只换权重并复用 S60 Head”在任何推理前已被工程身份约束否决，不能据此评价 G1J 2.9B 的输出质量。不得修改 Head 元数据、伪造模型哈希或关闭身份校验。后续另行预注册 G1J Selector Head 适配；13.3B 服务配置修复仍属于原实验的基础设施预检。
