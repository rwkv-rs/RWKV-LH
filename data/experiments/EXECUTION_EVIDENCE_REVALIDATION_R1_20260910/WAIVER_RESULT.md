# 双独立 AI 复核与旧 trace 重提取结果

本步骤无新增 Agent 成绩；固定15题新评测独立进行。历史基线仍为 Strict 0/15、completed 0/15、mutation 3。未训练，optimizer steps 0。

Owner本任务明确授权两个独立AI reviewer。两人分别审阅全部六文件的精确SHA diff与实际旧来源；身份写为AI，未冒充人工签名。原全量EQUIVALENCE_WAIVER_DRAFT.json未取得一致批准，保持原文draft。

核心原因：check_command工具描述和写入持久性、失败run_command范围证据、超时输出发生真实语义变化。输入字节匹配不能单独证明历史执行标签等价。实际15来源中，只有RP-WEB-02含受影响的命令路径：5次check均因旧Python/ELF入口错误失败。为避免把宿主缺陷作为合法执行语义，当前准入方案排除该来源全部21行，仅覆盖其他14来源的Selector；保留被排除来源全部原始事实和旧复核劳动，不修改15题评测分母。

具体注册文件、waiver和执行wrapper经两名reviewer再次独立审阅并签署精确SHA。wrapper固定14个source id、注册SHA、selector_intent角色和输出路径，校验两份accept记录与自身SHA。检查使用显式require，Python优化模式不会删除。原生产CLI按--equivalence-waiver及--waiver-sha256执行全部后续校验；没有修改生产准入器或协议。

正式重提取返回exit code 2，原因是角色数据质量门未过，并非来源SHA被拒：14来源全部登记进入provenance，恢复60自动候选（train55/dev3/confirmation2）与126待复核行。要求的execute覆盖为0；281对固定跨切分比较中101对达到0.95阈值。其余覆盖仍按原口径：mutate12、missing_target9、py_root21。候选状态INVALID，未建立正式数据集或改变标签/评分/相似度/切分算法。

因此，“15/15全部旧trace无条件恢复”未达成；“安全保留14来源且不取消原语义与质量防线”已完成。新采集若提供execute证据，仍须经过同一来源、标签、切分及质量门；不能拼接失败旧标签来补覆盖。

对用户特别关心的既有复核劳动另作精确核验：SELECTOR_REVIEW_PACKET_R1的9个边界、27行全部在新review_queue中保留；完整原始行、输入SHA、protocol_source、原输出记录SHA、request id、证据引用逐项一致。LEGACY_REVIEW_PRESERVATION.json记录27/27通过。仍是待标签复核，approved_labels=0；本轮waiver的双人技术签署没有冒充这些语义标签的双人批准。

证据：

- SCOPED_APPROVAL_ONE.json / SCOPED_APPROVAL_TWO.json：两名AI的具体批准范围与SHA。
- SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json SHA-256：c3e2bc4d5fbeb4ee99089ed387d38d1ce231035fdcc2697e420506af97aac85e。
- SCOPED_SOURCE_REGISTRATION.json SHA-256：0317d262960128fd43884ee7191c69bb15b5e54d645912446618b4c99366f6f7。
- scoped_selector_candidates/manifest.json SHA-256：ab8cad8efd54c195d932ea506764e9d40ae4365694ae672e9d10ea48ea7f86d5。
- SCOPED_EXTRACTION_COMMAND.json / SCOPED_EXTRACTION.log / SCOPED_EXTRACTION_SUMMARY.json：正式调用、原输出与质量门。

复核过程限制如实登记：reviewer two在正式共同批准前使用内部mapping做只读重建诊断，不属于CLI准入、数据冻结或标签批准；正式提取在两份精确批准到位后才执行。该诊断不能代替本节的正式准入结果。
