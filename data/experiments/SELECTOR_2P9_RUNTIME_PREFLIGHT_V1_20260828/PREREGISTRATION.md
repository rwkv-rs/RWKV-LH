# SELECTOR_2P9_RUNTIME_PREFLIGHT_V1_20260828

- 目的：验证远端已有 G1i 2.9B 服务可通过本地只读 SSH 转发供 Selector 基线使用。
- endpoint：`http://127.0.0.1:29611/v1`。
- 期望模型：`rwkv7-g1i-2.9b-20260805-ctx16384`。
- 基础权重 SHA-256：`ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。
- 一次固定最小 prompt、一次生成、无重试、temperature=0.05、max tokens=64。
- 原始文本、原始 token IDs、response ID/model、finish reason 必须先写入 append-only SHA-256 哈希链；不得修改原始输出。
- 通过条件：HTTP 成功、服务模型身份一致、原始 token IDs 非空、原始文本 SHA 可复核、finish reason 非空。
- 本实验只验证运行时，不评价工具选择质量。
