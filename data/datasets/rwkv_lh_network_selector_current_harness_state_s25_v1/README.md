# Current-Harness Selector state S25 v1

- 仅使用 S24 train 2000 条做 2.9B Selector 初始 WKV state tuning；dev 276 只验证，test 250 与 S23 全部排除。
- prompt 是线上同字节 BootstrapV2 + StepV2，target 仅监督标签后缀。
- 不训练 13.3B Executor，不含 schema、完整结果或 Executor 文本。来源、摘要、token 上限与命令见 manifest。
