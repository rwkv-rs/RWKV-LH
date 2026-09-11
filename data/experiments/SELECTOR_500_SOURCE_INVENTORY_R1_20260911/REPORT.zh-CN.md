# SELECTOR_500_SOURCE_INVENTORY_R1_20260911

本轮是存量盘点，没有新Agent成绩或训练；最新完成采集仍为Batch01 Strict0/12、completed0/12、mutation1、42动作，12题重复成功动作耗尽预算。

现有唯一数据管线已经实现：生产trace → 唯一协议builder/输入token/来源核验 → 自动证据或双独立AI语义标签 → 固定去重 → selected-source逐组重放。它不调用模型。role_trace_generation.py是原始生成证据核验器，不是独立场景合成器。旧合成入口退役事实在docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md记录；本轮未恢复旧协议或生成器。

显式盘点历史公开开发采集登记，不读取Holdout或私有验收。UltraData R1–R3共9个旧来源存在不可豁免角色协议SHA差异，不重放旧协议。UltraData R6的3来源、RealProject R3除已知命令工程缺陷WEB02以外的11来源已经在当前历史组消费，不能重复计数。

额外同协议未合并来源是UltraData R4的3题、R5的3题、RealProject Handoff R1的12题，共18个。历史候选仅6自动+24待复核，其中15行与当前有效输入达到原0.95相似度阈值。R4/R5/Handoff分别有16/11/16个当前生产文件SHA差异，现有已签范围不自动覆盖；输入相似度诊断既不是准入，也不是标签批准。其余15行仍是待复核，不能承诺净增15条。

源协议匹配不代表底层State证据或全部producer等价。Handoff报告已明确Native输出后的数值边界错误；不得把这类工程错误转成纯模型能力问题。尚未对这些新增旧来源发起正式准入重放，本轮新增有效行声明为0。

因此存量优先盘点是必要补查，但这里没有一个未消费的500条有效库。当前有效池仍33（28train/3dev/2confirmation），来自全量377条已准入候选去重；当前耗时集中在采集新真实边界，而非抽取阶段。后续保持500有效train目标、标签证据和固定相似度政策。

完整对账见INVENTORY.json、UNCONSUMED_YIELD_DIAGNOSTIC.json。临时诊断第一次直接读取review queue的split字段触发KeyError，未生成输出；修正为如实记录缺失字段null后成功，没有推断或改变原split。
