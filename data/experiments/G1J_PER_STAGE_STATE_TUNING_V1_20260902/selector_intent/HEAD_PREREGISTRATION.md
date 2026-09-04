# G1J Selector-Intent Head 预注册

- Head ID：`rwkv_lh_g1j_selector_intent_head_v1`
- 基础模型：`rwkv7-g1j-2.9b-vllm-v1`
- 原生 G1J 权重 SHA-256：`966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239`
- 服务模型 artifact 权重 SHA-256：`c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`
- State：严格 zero，SHA-256 为 64 个 `0`
- 输入协议：`rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1`
- feature：同一次 current-step forward 的 final-layer mean 与 last 按 `[mean,last]` 拼接，维度 `5120`
- 标签顺序：生产 `NETWORK_EXACT_TOOL_LABELS` 的固定 25 类顺序
- 数据：只使用 `rwkv_lh_g1j_selector_intent_state_tuning_v1` 的 train 训练；dev 只在固定训练结束后报告；sealed 不复制、不读取、不计算
- 标准化：只用 train feature 的逐维 mean/std；std 下限 `1e-6`
- 结构：`Linear(5120,64) -> GELU -> LayerNorm(64) -> Linear(64,25)`
- 初始化：PyTorch seed `20260902`，全新 Xavier uniform；禁止加载或迁移旧 Head 参数
- 优化器：AdamW，learning rate `0.001`，weight decay `0.0001`
- batch size：`64`
- epoch：固定 `200`，无 early stopping、无 checkpoint 选择、无 Dev 调参
- dropout：训练时 `0.05`，部署时关闭
- temperature：固定 `1.0`，不做 Dev calibration
- 输出选择：第 200 epoch 的唯一 Head；无候选网格
- 评价：raw 25-class argmax accuracy、macro-F1、逐类 precision/recall/F1；这些指标只描述初始能力，不作为改口径或重训依据

Head 文件及其 `head_hash`、文件 SHA-256 一经生成即冻结，后续 zero State、Selector StateTune、组合实验全部复用同一文件。
