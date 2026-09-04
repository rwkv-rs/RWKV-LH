# Current-Harness persistent Selector state S27 v1

- 仅使用 S26 train 2000 条做 2.9B Selector 初始 WKV state tuning；dev 500 只验证，test 500 与 S23 全排除。
- prompt 按线上顺序包含一次 Bootstrap、0–2 个历史 Step 和当前 Step，target 只监督标签后缀。
- 不训练 13.3B Executor，不含 schema、完整结果或 Executor 文本；摘要与 token 上限见 manifest。
