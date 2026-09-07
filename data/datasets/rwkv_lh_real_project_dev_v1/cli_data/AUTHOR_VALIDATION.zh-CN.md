# CLI / 数据项目作者验证

Agent 级：未运行 RWKV Agent；没有 Strict、completed、mutation 数或终止原因成绩。本记录是基准题集作者验证，不是模型性能或 StateTune 增益。

来源是 owner-authorized authored development benchmark；不冒充真实用户生产 trace，不生成角色 StateTune 样本。本组包含四个不同项目任务族：

| 任务 | 项目 | 黑盒行为覆盖 | 明确错误变异 |
| --- | --- | --- | --- |
| RP-CLI-01 | 可移植目录备份/恢复 | 固定 seed 二进制/Unicode/隐藏/空文件与空目录；跨进程恢复；损坏归档失败原子性；symlink snapshot 拒绝；目录穿越拒绝 | 移除 `..` 路径拒绝，私有验收拒绝 |
| RP-CLI-02 | 持久化时间记录 CLI | SQLite 跨进程持久化；时区归一化；跨日/闰日分摊；范围裁剪；重复导入；冲突/坏记录整批回滚；空查询 | 静默接受冲突 ID，私有验收拒绝 |
| RP-DATA-01 | 财务 CSV 对账管道 | Decimal 逐行 half-up 舍入；退款；重复与冲突；多币种/坏行报告；无付款/零额发票；稳定输出；非法 header/坏 CSV 失败保护；空输入 | 改成 half-even 舍入，私有验收拒绝 |
| RP-DATA-02 | 访问日志增量入库查询 | 固定 seed 多路径/状态/时间数据；部分行延迟消费；持久 offset；跨文件去重；坏行/冲突隔离；半开时间边界；改写/截断拒绝；重启稳定性 | 重启后 offset 归零，私有验收拒绝 |

最终作者验证：4 个参考实现通过；4 个具有语义缺陷的变异全部被拒绝。每项均由独立 `private_verify.py WORKSPACE` 通过真实 CLI 子进程及文件/JSON结果验证。评分不读取候选源码，不检查关键词、长度或预制固定最终答案。变异的源文本替换只负责构造错误候选；是否通过完全由黑盒行为决定。

公开 `workspace_files` 仅包含 README 契约，没有完整正确实现、私有输入或参考答案。候选工作区仅读；所有私有输入、数据库、归档、报告均由 `TemporaryDirectory` 新建。作者运行将 TMPDIR 设在本数据目录；通用 runner 可使用自己的隔离临时挂载。reference/、mutation.json、私有验收、作者记录均不得投放 Agent 工作区。

作者脚本位于项目 temp/，以绝对路径执行；生产 runner 不依赖作者脚本。作者验证后删除临时候选副本，仅保留参考源码、变异规则、验证日志、结果和 SHA。`author_validation/RESULTS.json` 记录每次返回码、候选 SHA 与 verifier SHA；`MANIFEST.json` / `SHA256SUMS` 记录本组文件。

全套任务注册、cross-family 相似度审计、外层只读 sandbox 验证和数据集冻结由主任务整合。尚未完成这些步骤时不得将此作者记录称为最终基准验收。训练仍未授权执行。
