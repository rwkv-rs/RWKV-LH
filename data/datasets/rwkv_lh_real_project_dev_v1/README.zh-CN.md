# Real Project Dev V1

Owner 已书面选择“先补齐真实项目任务和验收，再全面测试”。本集是为此编写的 12 道真实项目形式的开发评测题，包含 10 道新建项目、2 道现有多模块项目维护。它们不是从真实用户日志采集的任务，也不是 StateTune 训练样本；不代表大型仓库、外部联网或所有行业场景。

| 题号 | 用户任务 | 关键验收 |
|---|---|---|
| RP-CLI-01 | 创建目录备份与恢复 CLI | 完整恢复、路径安全、失败不污染目标 |
| RP-CLI-02 | 创建持久化时间记录工具 | 跨日统计、时间区间、重复导入与冲突回滚 |
| RP-DATA-01 | 创建 CSV 账单对账项目 | Decimal 金额、对账结果、坏行与坏文件报告 |
| RP-DATA-02 | 创建增量日志入库与查询工具 | SQLite、去重、断点续读、重启与查询结果 |
| RP-API-01 | 创建资源预约 HTTP 服务 | 区间冲突、取消、并发一致性、重启持久化 |
| RP-API-02 | 创建库存与订单 HTTP 服务 | 幂等请求、原子扣库存、并发防超卖、重启 |
| RP-MAINT-01 | 修复已有 SQLite 配置迁移项目 | 多模块升级、备份、失败保持原库、恢复 |
| RP-MAINT-02 | 修复已有文档索引项目 | 内容变更、删除、Unicode、增量索引与异常回滚 |
| RP-WEB-01 | 创建任务看板网页 | 创建、编辑、移动、筛选、键盘、刷新后保留 |
| RP-WEB-02 | 创建阅读清单网页 | 增删、组合筛选、导入导出、错误导入不丢数据 |
| RP-FULL-01 | 创建完整工单管理应用 | 浏览器操作、HTTP、SQLite、状态流转、服务重启 |
| RP-FULL-02 | 创建完整提案投票应用 | 投票与撤票、幂等、排序、关闭保护、服务重启 |

每题 `task.json` 包含自然语言需求、明确的公开接口合同和初始工作区。维护题包含待修复项目，其余题从需求文档起步。只有这些公开字段进入 Agent 工作区。

`private_verify.py`、`reference/`、`mutant/`、`mutation.json` 和作者验证记录仅用于评测构建及校验。私有验收通过实际 CLI、HTTP、SQLite 与 Playwright Chromium 行为判断交付结果，不以源码关键词或 CSS 长度计分。验收在 Agent 阶段结束后运行，候选工作区为只读快照；业务数据位于临时目录。候选 Python 子进程另隔离文件和进程视图，无法读取私有验收程序。

所有题目均检查参考实现通过、关键语义缺陷被拒绝、初始未完成项目被拒绝。完整隔离验证见 `data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/PROJECT_ISOLATION_FINAL_12.json`。这些是验收器质量验证，不能当作 RWKV Agent 的 Strict 成绩。

`MANIFEST.json` 记录源文件、编译脚本与协议模块 SHA、12 个任务族、开发集切分政策和 UTF-8 byte 5-gram cosine 相似度审计（阈值 0.95）。所有任务固定为开发评测用途，不创建 train、confirmation 或 holdout 切分；最终保留集未读取。角色训练数据后续仍只能来自实际生产 trace。

运行资源编译到 `benchmarks/rwkv_e2e/rwkv_real_project_dev_v1/`，suite key 为 `realprojectdevv1`。编译资源与作者合同由回归测试逐题比对；冻结后比较两臂不得修改题目、验收、源码或参数。
