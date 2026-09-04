# Current direct-Harness identifiable Selector S26 v1

- 训练/开发/盲测为 2000/500/500；每个 split 的 25 类与中英文均严格平衡。
- literal request 自身决定当前工具；stage 仍为产品的通用 CurrentDirectStageV1。
- continuation 必须依次复放 history_steps，禁止重新 bootstrap 当前 step。
- 不含参数 schema、完整工具结果、Executor 文本或生成的 RWKV 文本；来源与摘要见 manifest。
