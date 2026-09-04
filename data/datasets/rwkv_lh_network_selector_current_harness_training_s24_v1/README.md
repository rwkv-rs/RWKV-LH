# Current direct-Harness Selector training S24 v1

- 训练/开发/测试分别为 2000/276/250，沿用 S3 冻结标签与语义族拆分。
- 输入严格使用当前 `LongHorizonModel` 的 SelectorBootstrapV2 + CurrentDirectStageV1 紧凑投影。
- 每次 continuation 至多投影一个最新动作；不含工具参数 schema、完整结果或 Executor 文本。
- S23/ECRA 只用于冻结后外部评估，未进入训练。来源摘要、生成命令与验证指标见 manifest。
