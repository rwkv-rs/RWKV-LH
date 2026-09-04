# Factory surface seed contract v0 rejection

状态：整批拒绝，0 条进入训练。

首版 `phase_evidence_contrast` 只机械约束了 `{path}`，没有把 fixture 中的可验证目标也暴露为
placeholder。强模型因此生成了“比较草稿和发布版本”“核对最新目录说明”等自然但含额外义务的
请求，而本地 oracle 只有读取单个 marker 的能力。结构 schema、placeholder 和禁用工具名虽然
通过，instruction/environment/oracle 语义没有对齐，不能靠成功 Controller replay 冒充合格数据。

已停止生成并保留 7 个原始 batch 作为失败证据。修订后的 seed 要求请求只能读取 `{path}` 并报告
精确 `{marker}`，同时禁止 comparison/freshness/modification 词；Factory validator 会机械要求两个
placeholder 各出现一次。因为 seed SHA 已变化，v0 batch 不允许 `--resume` 到新一轮。
