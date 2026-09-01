# G1J Auditor 模型对照结果

同一最新模板、同一 zero-State、同一证据事实和 stop suffix 下：

| 模型 | Audit | 独立格式错误 | 语义错误 | 额外驻留显存 |
|---|---:|---:|---:|---:|
| G1J 13.3B | 2/2 | 0 | 0 | 0（复用 Executor 权重） |
| G1J 7.2B | 0/2 | 0 | 2 | 约 16.1 GiB |

13.3B 还通过了当前 Executor `write_file` 参数例（1/1）。7.2B 两例都能输出合法六字段，但错误忽略 `complete=true/truncated=false/eof=true`，把已完成 read evidence 判为 `repair`。

默认方案确定为：Auditor 复用 Executor 的 13.3B 服务配置，但必须使用独立 session、独立 clean State、WKV 永不 merge。只有显式配置 `RWKV_LH_AUDITOR_*` 时才启用其他模型；当前不推荐常驻 7.2B。

本轮同时证实此前 Audit 失败的最早工程根因是 evidence ref 没有关联 Harness 事实，以及 prompt 展示了禁止输出的 kernel 字段名。修复这两处后 13.3B 从旧模板失败恢复为 2/2，不需要 State Tuning。
