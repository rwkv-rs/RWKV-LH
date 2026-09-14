# 当前缺陷与StateTune来源登记

更新：2026-09-14。当前登记18项问题或保留项，不宣称未知缺陷已经穷尽。来源和SHA见[机器台账](../data/experiments/RWKV_EXPLICIT_EDIT_R1_20260914/DEFECT_REGISTER.json)。这不是已准入训练数据，工程/评分问题不能混作模型标签。

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
|E01|观察顺序与接管重复注入|engineering / fixed_regression_required|已红绿修复；排除修复前损坏输入，不当模型错误标签。|
|E02|摘要验收过细、全或无压平质量|evaluation / known_invalid_interpretation|保留旧分数但不以0/8等价不会总结；不把评分缺陷喂给模型。|
|E03|建议模板偏向摘要而非未完成操作|input_design / hypothesis|单独验证语义适配，未证明是重复根因。|
|E04|历史重复计数使建议续跑提前终止|policy_interaction / hypothesis|保留真实预算；不把未获得的调用机会当模型已尝试失败。|
|E05|依赖任务集成与共享冲突未闭合|engineering_gap / not_implemented|实现与系统回归负责，不能靠StateTune修工程缺口。|
|R01|简短读取参数说明固定组有效|positive_control / retain_regression|21/21与独立3/3分别保留，防止新训练破坏已成立能力。|
|R02|已有明确修改和真实测试成功样本|positive_control / retain_after_provenance_review|有6/8任务成功，但部分final受旧边界干预，不把所有成功称自然自主完成。|
|M10|已给明确修法却写回原错误内容|model_observation / observed_candidate_not_corrected|选择写入工具不代表实现了修改；需核对实际差异和行为。|
|M11|写入成功被误当作完成要求的修改|model_observation / confirmed_unfixed|I/O成功不等于语义修改；依据文件真实内容及差异报告，不能将任务要求复述为已完成事实。未运行测试的正确披露单独保留。|

正向纠正、合法例外、既有成功样本均保留。重复读取有时合理；如实报告测试失败不是虚假完成；下一步建议不是执行事实。1万条目标见[数据计划](STATETUNE_10000_PLAN.zh-CN.md)。
