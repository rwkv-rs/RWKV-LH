# API 与维护项目开发评测组

来源：**owner-authorized authored development benchmark**。由 owner 书面授权新增开发题；不是历史真实用户请求，不是生产 trace 抽取，不是角色 StateTune 数据。没有执行模型运行或训练，因此没有 Agent Strict / completed / mutation / 终止原因新结果。

| 任务 | 实际行为验收 | 正确参考 | 定点错误变异 | 初始未修复项目 |
|---|---|---:|---|---|
| RP-API-01 | 随机区间冲突 oracle、相邻区间、Unicode、取消、非法输入、并发唯一成功、HTTP 重启恢复 | 100 检查通过 | 关闭重叠判定，在 interval case 10 被拒绝 | 被拒绝 |
| RP-API-02 | 规范化订单幂等、跨 SKU 原子失败、非法输入、随机重试账目、并发防超卖、HTTP 重启 | 91 检查通过 | 相同幂等请求错误返回 409，被拒绝 | 被拒绝 |
| RP-MAINT-01 | SQLite v1→v2、类型/Unicode 保真、无关表、幂等升级、坏 JSON/版本/schema/备份冲突的原库字节不变、合法与坏备份恢复 | 49 检查通过 | boolean 错标 string，被拒绝 | 被拒绝 |
| RP-MAINT-02 | 递归与符号链接边界、增删改、相同 mtime/size 更新、NFC+casefold、坏 UTF-8 原子失败、每次新 CLI 进程读持久化索引 | 87 检查通过 | casefold 错换 lower，STRASSE 被拒绝 | 被拒绝 |

12 次作者自验全部符合预期：**4 reference 通过 + 4 negative 拒绝 + 4 initial 拒绝**。逐项记录在 `self_validation/results/`；汇总在 `self_validation/SUMMARY.json`。每次验证前后候选文件 SHA 相同，没有写入候选 workspace；验证脚本复制到独立位置后运行，证明不依赖相邻 reference 或作者文件。

公开 task.json 只包含自然任务、README 接口合同、初始项目文件及 workspace_generators=[]。API 的 verify_public.py 只有健康检查，明确不能代表功能达标；维护题没有暴露私有用例或完整正确答案。每题 reference/ 和 private_verify.py 只用于作者及外部评分，**NEVER 复制到 Agent workspace**。维护题可见模块是正常的已有实现，其中迁移/恢复和索引扫描/增量逻辑保留待修缺陷。

私有程序接口为 `python private_verify.py WORKSPACE`，只用 Python 标准库；WORKSPACE 可为只读目录。程序在 TemporaryDirectory 中创建测试输入、SQLite DB 和日志；作者自验将临时根配置到本组 data/self_validation/ephemeral/，集成 sandbox 可使用自己的临时目录。测试响应按公开语义字段判断，允许附加响应字段，不限制实现内部文件数/框架/字数；CLI 入口与 SQLite 配置 schema 是明确公开合同。

本组没有读取任何既有 acceptance、confirmation、Holdout 或封存资产。随机种子由作者固定在私有程序中。验收输出只用于作者验证；未来模型运行后不得改评分重打同一轮。私有检查不是完整安全证明，根级集成还需独立验证 bwrap 隔离、12 题注册、完整哈希冻结和运行身份。

本组 4 个 project family 是 reservation_http、inventory_order_http、sqlite_config_migration、unicode_document_index。当前仅为开发评测集合，没有创建角色 train/dev/confirmation split；全套 12 题的跨组重复性/相似度审计、最终 manifest 和授权快照由 root 统一登记。

作者脚本位于项目 temp/，用绝对路径执行；生产、测试或评分均不依赖它们。没有修改公共 runner、pyproject、tests 或其他题组。
