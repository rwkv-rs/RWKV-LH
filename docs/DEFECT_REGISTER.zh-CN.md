# 当前缺陷与StateTune来源登记

更新：2026-09-14。当前台账包含原19项及下方新增工程问题或保留项，不宣称未知缺陷已经穷尽。来源和SHA见[机器台账](../data/experiments/RWKV_EXPLICIT_EDIT_R1_20260914/DEFECT_REGISTER.json)。这不是已准入训练数据，工程/评分问题不能混作模型标签。

|ID|问题|分类/状态|标注或处理原则|
|---|---|---|---|
|M01|非法工具参数及跨工具字段混用|model_observation / open|只允许当前工具schema字段；纠正后参数必须经真实Harness验证。|
|M02|重复读取、缺少推进|model_observation / open|给定已见证据时推进合理操作；不得把所有重复读取都标错。|
|M03|修改未接入实际入口|model_observation / open|修改应影响用户实际调用入口，验证副本上真实行为。|
|M04|测试失败后虚称修复与测试通过|model_observation / open|区分工具退出、断言结果、实际修改与回答。|
|M05|数字、标签、分子分母及比较关系失真|model_observation / open|按来源忠实引用，不编造前后提升；合理等价表达可接受。|
|M06|需求误当实现、来源事实混淆|model_observation / open|文档要求、源码实现、本轮观察分别归属。|
|M07|纠正后仍残留错误或吸收错误建议|model_observation / open|建议不是事实；逐条核实且不能整篇strong答案直接入训。|
|M08|无依据补充与关键遗漏|model_observation / open|主旨和重要限制、忠实性分开标注；不强迫列所有实现细节。|
|M09|无交付终止，当前结果与下一步未形成闭环|capability_gap / unverified_next_step|未输出建议不是错误建议；补采明确操作完成后的真实轨迹。|
|E01|观察顺序与接管重复注入|engineering / extended_regression|本轮又发现旧只读建议入口先建议后观察，已复现并改用共享补观察函数；排除修复前损坏输入。|
|E02|摘要验收过细、全或无压平质量|evaluation / known_invalid_interpretation|保留旧分数但不以0/8等价不会总结；不把评分缺陷喂给模型。|
|E03|建议模板偏向摘要而非未完成操作|input_design / hypothesis|单独验证语义适配，未证明是重复根因。|
|E04|历史重复计数使建议续跑提前终止|policy_interaction / hypothesis|保留真实预算；不把未获得的调用机会当模型已尝试失败。|
|E05|依赖任务集成与共享冲突未闭合|engineering / bounded_implementation|已实现显式coding依赖和同基线无冲突文件集成；冲突拒绝，不宣称通用自动合并。|
|R01|简短读取参数说明固定组有效|positive_control / retain_regression|21/21与独立3/3分别保留，防止新训练破坏已成立能力。|
|R02|已有明确修改和真实测试成功样本|positive_control / retain_after_provenance_review|有6/8任务成功，但部分final受旧边界干预，不把所有成功称自然自主完成。|
|M10|已给明确修法却写回原错误内容|model_observation / observed_candidate_not_corrected|选择写入工具不代表实现了修改；需核对实际差异和行为。|
|M11|写入成功被误当作完成要求的修改|model_observation / confirmed_unfixed|I/O成功不等于语义修改；依据文件真实内容及差异报告，不能将任务要求复述为已完成事实。未运行测试的正确披露单独保留。|

|E06|编码trace离线重放误用只读菜单|engineering / fixed_targeted_regression|本轮修复coding scope及记录工作区身份；重放成功不代表模型答案正确。|

正向纠正、合法例外、既有成功样本均保留。重复读取有时合理；如实报告测试失败不是虚假完成；下一步建议不是执行事实。1万条目标见[数据计划](STATETUNE_10000_PLAN.zh-CN.md)。


归并边界与下一阶段见[展开分析](DEFECT_GROUPING_AND_NEXT_STAGE.zh-CN.md)。


本轮新增工程项（非模型训练错误）：

|ID|问题|当前边界|
|---|---|---|
|E07|Goal模式无变化重复写入强制Final|直接模式已禁用强制Final，保留合法继续操作及既有预算；旧研究模式不冒充当前产品。|
|E08|trace_complete仅反映日志写盘|增加请求/返回配对和未闭合ID；父运行续接核对原记录。配对不等于张量正确。|
|E09|准备时间未计入预算、协助超时worker清理不足|整任务协作式deadline与进程组清理；清理/落盘可超时，如实标记，非OS硬配额。|
|E10|进程池故障丢整批结果|逐future保留结果和故障文件，未知调用数/协助归属不伪造。|
|E11|只读工具每次复制整工作区|只读调用保留原观察和调用记录；修改仍保留before/after快照。成本收益尚未实测。|

编码纠正准入、统一费用/峰值资源计账、语义冲突解决仍是未完成能力，不能按本轮工程回归标为解决。

工作区与恢复补查（`RWKV_WORKSPACE_RECOVERY_R1_20260914`）：E05扩展为记录目录/权限身份，检测复制期间源变化，拒绝不支持的权限/空目录集成及缺少树身份的依赖，修复目录移动后残留旧目录；E08扩展到旧只读建议入口及父历史生成配对。七项回归覆盖上述边界，其中空目录是显式拒绝边界检查，其余六项保留失败复现。尚不保证任意外部并发写入的原子快照；旧协助交付无`final_tree`时仍仅有历史内容身份检查，不把历史证据升级为完整权限认证。详情见[报告](../data/experiments/RWKV_WORKSPACE_RECOVERY_R1_20260914/REPORT.zh-CN.md)。
