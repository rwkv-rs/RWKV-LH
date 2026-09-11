# 全公开开发题集原始 trace 采集 R1

Owner 最新授权：按本地公开题集全量运行，积累原始生产 trace。此前暂停扩大采集的状态已被本次授权替代。

Agent：启动时完成 0/117，Strict/completed/mutation/终止原因待实际结果；首题 E2E-B01 已启动。角色：本轮新增有效训练样本未统计，optimizer steps=0。历史有效数据57行（train52/dev3/confirmation2）未改。

8套题集119个成员，117道独立题：core30 30、extension48 48、lh12 12、realprojectdevv1 12、agentladderv1 10、agentv1 1、diagfix2 2、execute diagnostics 4。最后一套中的RP-CLI-01/RP-WEB-02与realproject题目和验收逐对象相等，登记别名后各执行一次。架构回归30项为程序验证规格，不伪称模型trace；最终holdout未读取。

新隔离工作树冻结da067f25，生产源码包含5ff6ed4a路径工程。完整回归1480 passed，未修改生产源码。上传132项目文件、6393engine文件并验证完整清单；服务器无Git。项目manifest SHA 36f054ffa38b9ade0504163ee0baa0f3b65cd321c5283a7ba399bb8aaf163aab，engine manifest SHA a01d49ffd93c539bdc37abdb08e5de488230c47c15b61074a83afa377cece27a。两服务重启并健康通过，fresh State store，权重与所有角色zero保持。

固定轮询原始题集顺序，单并发，单题200 transitions/1800秒，总预算210600秒（58.5小时上限，并非预计耗时），不自动重跑，native transport resume 1。完整生产任务终止，不使用Selector边界截停。保留逐题失败、超时、原始事件、角色输入输出及最终验收。两个联网梯度题使用原任务runner_control；LH09的mock_api能力缺口和diagfix历史grader疑点预先登记，不以静默排除消除失败。

原始题目/私有验收只由runner分发，验收不注入Agent workspace。沿用诊断验收事件绑定wrapper，绑定前模板SHA检查。原始trace不是已准入训练行；后续Selector缺陷统计、复核、去重另行登记。本轮不改数据政策、不复用旧waiver、不启动训练。

运行目录：data/experiments/FULL_TRACE_COLLECTION_R1_20260911。STARTED.json是启动收据，PROGRESS.json逐题更新，COMPLETION.json仅全队列结束时生成。后台有限队列自动继续，不在每批等待复核。主驱动PID见STARTED.json。
