# R1 采集管线基础

任务级：本轮新模型执行 0、验收 0、训练 0、强模型调用 0；尚未启动 3 万任务，不报告 Strict。

实现持久队列、冻结材料摘要验证、只允许直接 RWKV 的批量入口、SFT JSONL 流式结构审计。队列中断保留 running，不自动重试未知执行；recorded 不等于验收通过。完整剩余部署门见 docs/COLLECTION_PIPELINE.zh-CN.md。

新增回归先 collection_queue 模块缺失报错，后针对恢复、重复来源、并发领取、强模型配置拒绝和冻结来源改动和跨批路径隔离的六项验证通过。完整回归首次运行遭遇本轮并行定向测试共享 basetemp 冲突，保留 full_tests.txt；重新隔离目录验证，结果见 full_tests_isolated.txt。

已有 SFT 三类各两条加近期 50 条 Code 来源结构审计（合计 56 条记录，包含重叠来源），见 SFT_EXISTING_AUDIT.json；这是结构审计，不代表 56 个可执行或独立任务。Code 依赖真实仓库，General 依赖订单等材料，Search 依赖搜索服务。没有用历史输出伪造环境。

清理仅删除 experiments 下 1762 个未跟踪 __pycache__/*.pyc，28,871,069 字节；逐文件 SHA 和路径见 CLEANUP.json。原始 trace、失败候选、训练来源和验收记录未删除。

现有 owner 五个修改文件保留。本轮不部署服务、不改 Native 请求锁、不 push、不建数据集版本。

额外删除可从保留来源逐字节重建的流式审计输入副本 11798144 字节；累计释放 38.79 MiB。原始来源和导出脚本/摘要保留。

最终隔离目录完整回归：1843 passed，0 skipped，352.17 秒。仅 GPU 0；测试未启动本轮模型采集或训练。
