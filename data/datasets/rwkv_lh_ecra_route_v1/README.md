# RWKV-LH × ECRA route dataset v1

- 来源：RWKV-LH 当前 17 个 ActionDefinition、RWKV-ECRA/Scout 的公开工具分类和统合设计中的隐私出站边界。
- 版本：`rwkv-lh-ecra-route.v1`。
- 用途：在实现路由逻辑前冻结本地/网页/连接器/计算/混合/隐私拒绝的模型动作选择评价。
- 生成方式：120 个独立编写的中英文场景，由 `scripts/generate_rwkv_ecra_route_dataset_v1.py` 机械编号和序列化；运行时不得导入生成器或答案。
- 覆盖：local-only 30、public-web-required 25、structured-connector 20、deterministic-compute 15、mixed-local-online 20、privacy-policy-rejection 10。
- 评价：exact tool、network/non-network macro-F1、web/connector macro-F1、隐私出站零容忍；文本稳定性使用 `utf8-byte-ngram-cosine.v1`（byte 5-gram，near 0.95，exact 1.0）。
- 许可：本数据集为项目内人工编写的通用任务，不复制第三方答案或网页正文。
- 文件摘要：见 `manifest.json`。
