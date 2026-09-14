# 当前交接（2026-09-14）

## 产品与当前入口

目标：为RWKV构建专属Harness和Code Agent；同质量下的成本、速度与吞吐是优化指标。当前架构只从[ARCHITECTURE](ARCHITECTURE.zh-CN.md)进入，历史设计不再作为互相竞争的产品入口说明。

当前执行是RWKV直接选择工具/参数→真实Harness→观察及连续State→原始交付→外部验收。默认不调用Planner/Selector/Auditor链。历史多角色构造仍有研究代码及测试依赖，尚未物理删除；不能声称已全部清理。

推荐统一入口：`scripts/run_rwkv_agent.py --jobs /absolute/jobs.json --concurrency 2`。格式见[批量使用说明](AGENT_BATCH.zh-CN.md)。原单任务修改、只读CLI及既有前端共享底层执行；本轮不改页面。

## 正在交付的阶段

独立任务交付与协作阶段已经开始：读取/检查/修改共用批量调度器，全批预算和路径预检查、spawn进程隔离、原结果返回、普通任务启动错误单列。修改任务复制源目录，不自动集成共享文件。任务独立性由目标和依赖决定，不由程序替用户拆分。

前轮并发小批2/2满足事前登记任务要求、2提交、mutation0：读健康检查脚本准确说明范围；递归扫描测试真实运行并如实报告通过。共4真实生成、11936逻辑输入/396输出token，输入和State父链核验。这是集成smoke，不是项目Strict、并发收益或通用修改能力。

工程红→绿及完整验证见[本轮报告](../data/experiments/RWKV_AGENT_ARCHITECTURE_BATCH_R1_20260914/REPORT.zh-CN.md)。已有owner五处修改必须继续保留：controller.py、model.py、supervisor_openai.py、test_hybrid_supervisor.py、test_supervisor_openai.py。未混入本轮代码提交。

前轮真实失败恢复：同一查询问题的两个失败父运行，建议后RWKV 0/2，强模型显式接管2/2；后者均真实修改并测试，外部原测试通过。建议续跑仅1/2次生成即再次触发历史重复保护，不能宣称建议无效或RWKV独立能力提升。完整记录见下方恢复阶段。

本轮完整目标入口：显式on_stall=takeover后RWKV先执行，停滞时按剩余预算最多接管一次。固定三任务3/3交付：RWKV独立2、接管1。查询RWKV用12次后重复保护中断，strong用3次修改并测试；不是RWKV独立修复已稳定。完整1650测试通过。

最新单处修改验证0/2：RWKV分别7/11次生成后重复读取中断，未修改、未回答。任务仍包含自行判断修法，不能据此否定真正单步执行；下一步分离诊断与明确操作执行。已清理101个有核验存档的temp/data重复文件，生产架构未改。

最新明确方案执行0/2：两遍write_file成功但内容未变，一遍无回答、一遍虚称改好且正确说未运行测试。已补M10/M11缺陷记录；下一步统一审核纠正来源，不再扩架构。temp约1.5GB→285MB，删除2参考副本、68重复脚本、458旧一次性脚本及11字节码，清理后1650测试全绿。

最新离线来源阶段：编码 trace 重放误用只读 Harness 已定位并最小修复；新增真实失败轨迹回归，原答案不改。1万条仍仅计划，未训练或新建数据版本。[缺陷归并与下一阶段](DEFECT_GROUPING_AND_NEXT_STAGE.zh-CN.md)明确模型、工程、评分与假设的边界。

工程优先整改：停止继续检查真实trace或调用RWKV。已复现并整改Goal强制Final、生成配对审计、准备预算、进程池结果丢失及旧只读建议顺序；补协助进程组清理、只读快照减负和显式coding依赖/保守集成。[工程报告](../data/experiments/RWKV_ENGINEERING_FIXES_R1_20260914/REPORT.zh-CN.md)保存红绿和完整回归结果。1万条仍仅计划。

工作区与恢复补查已完成本轮实现：复制前后身份核对、目录/权限变化记录、目录移动集成、缺树身份与不支持变化拒绝、旧只读恢复父trace校验。新增7项回归，显式GPU 0完整测试1678 passed（327.08s），未运行新Agent验收。[本轮报告](../data/experiments/RWKV_WORKSPACE_RECOVERY_R1_20260914/REPORT.zh-CN.md)列出证据和剩余边界；下一步是编码纠正候选准入与资源计账，工程问题未全部关闭。

最新完成离线原子编码纠正候选验证与用量账本：[调用说明](EVIDENCE_AUDIT.zh-CN.md)。真实原无效写入仍被拒绝；修复replay_run重复生成请求被覆盖的问题。供应商重试、未知usage、逻辑token与费用分开；原生GPU总成本仍未知。训练freeze未增加编码标签、未建数据版本或训练，不能把候选验证算已准入样本。[本轮记录](../data/experiments/RWKV_CORRECTION_USAGE_R1_20260914/REPORT.zh-CN.md)。

本轮GPU 0完整回归1700 passed、0 skipped（327.49s），新增22项；原owner五处修改保留，未计入本轮提交。没有新模型验收成绩。

Owner补充StateTune社区证据：约3000条数据的G1J 7B Three.js展示改善，当前只作外部复现线索。明确zero低分不是训练禁令；训练门槛是来源/纠正可信、协议State身份、隔离回归及授权预算，不等所有工程增强完成。下一步盘点获准真实来源与可验证纠正、覆盖缺口，推进统一多缺陷训练准备。

已查看Lightning CUDA、Preen及RWKV-APP State-Tuning Studio的文档/源码，[参考核对与下一阶段](../data/experiments/RWKV_STATETUNE_REFERENCES_R1_20260914/REPORT.zh-CN.md)。Lightning作为候选训练/推理后端，Preen借鉴mask/导出验证，Studio借鉴run管理。外部训练text格式、截断和State轴语义不可直接混入当前链路；先做有界兼容验证，数据准备主线继续，不等待换后端才训练。未构建或启动外部训练/UI。

最新完成真实失败纠正试点：[记录](../data/experiments/RWKV_VERIFIED_CORRECTIONS_R1_20260914/REPORT.zh-CN.md)。初始强接管目标1/3（提交1），关闭thinking的独立恢复目标1/2（提交2、修改1）；均不算RWKV独立或Strict。数字纠正1条复核通过，API无依据细节被人工拒绝，编码原样修改独立红→绿但审核分歧/家族切分待解，正式准入0。双API审核也出现漏错/误拒，旧票原样保留，不通过反复审核凑通过。GPU 0完整回归1700 passed、0 skipped（329.55s）。共19次供应商请求、121514/10905输入/输出token，成本未知；未训练/建版本/push。下一步先补审核证据规则回归和来源切分，再扩优质真实来源；1万条不再作为首批最低门槛。

最新审核与来源阶段：[R2记录](../data/experiments/RWKV_CORRECTION_REVIEW_R2_20260914/REPORT.zh-CN.md)。旧审核3/6、新审核4/6，API仍被语义漏判，新6/6门未达；不宣称E13解决。已增加离线原样候选/引用绑定回归，不接入逐步执行审核。编码来源确认RP-MAINT-02→MAINT/train，14条相关已知运行不是独立来源；原样补丁经既有验证器红→绿。现有正式库存128条（28读取/100回答、28来源ID/52生成边界、CLI/FULL/MAINT/RAG四家族），协议/SHA核验通过但未完成新语义审核。下一步优先复核这128条而非重复造样本，再补编码freeze及有来源的覆盖缺口。新增正式准入0，GPU0完整回归1710 passed、0 skipped（319.50s），未训练/建版本/push。

## 能力和限制

- 固定单步读取、部分文档总结及明确测试执行已有成功证据。
- 自主多步修复尚未稳定：会重复读取、读不存在路径、不选择修改/测试、无回答终止。不能由此推断不会简单总结。
- 改恢复句及精简菜单未改善固定修复任务，候选不保留；局部定位实验到此收束，不再继续无方向微调。
- State传递和真实观察已多轮核验，未发现可解释上述停滞的遗漏；不等于证明数值State及长上下文利用没有问题。
- 强模型建议/显式接管已接入统一任务入口，归属分开；不增加逐步审核关卡；可显式开启无交付预算停滞的有界接管，尚无语义自动求助。当前轮工程和真实验证结果见协助阶段报告。
- 已增加显式coding依赖与同基线不冲突文件集成；冲突、不同基线和纯权限/空目录变化不自动合并。语义冲突解决与前端续跑仍未完成。

## 后续顺序

1. 优先验证owner提出的原子任务与“RWKV完成当前小任务后提出下一步”：先测局部交付和建议，再测依赖衔接；不预设强模型规划所有小任务。当前整目标基线和新对照分别冻结，建议与已执行事实分开。
2. 增加有依赖任务的结果集成与最终验收，再测同质量下端到端成本/延迟/吞吐，不提前宣称并发优势成立。
3. Owner已提出之后统一约10000条多缺陷StateTune数据目标。按[缺陷台账](DEFECT_REGISTER.zh-CN.md)与[1万条计划](STATETUNE_10000_PLAN.zh-CN.md)先审核来源/纠正与覆盖，再分批生成；当前未建数据版本或训练，不把强模型成果算RWKV独立能力。

## 必须保留的约束

Owner最新要求：只使用物理GPU 0。后续本地测试及模型进程显式设置`CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0`；远端启动同样限定目标主机GPU 0，不改动无关进程。

遵守AGENTS。所有命令在WSL；服务器禁止Git；不读最终holdout/acceptance目录。不改前端或可视化；本轮不push、不训练、不新建dataset版本。以后授权按具体范围判断。模型输入只走现有唯一构造函数，程序不代选业务动作、补参数或改答案。

预算耗尽/中断不是合格完成，final_answer不是通过隐藏评分；外部验收按目标和真实交付、不限定实现路径。完整逻辑token不是实际费用。生产变更需先失败后通过回归、完整测试后本地一轮一提交。

## 最近证据索引

|记录|作用|
|---|---|
|[明确操作与统一缺陷](../data/experiments/RWKV_EXPLICIT_EDIT_R1_20260914/REPORT.zh-CN.md)|0/2、无效写入及错误修改声明；temp大幅清理、18项台账和1万条计划|
|[单处修改与清理](../data/experiments/RWKV_ATOMIC_CHANGE_R1_20260914/REPORT.zh-CN.md)|0/2，保留失败；清理46脚本与55验证副本|
|[完整目标阶段](../data/experiments/RWKV_GOAL_DELIVERY_R1_20260914/REPORT.zh-CN.md)|固定3/3：RWKV独立2、接管1；RWKV24/总32额度，实际停滞如实保留|
|[失败恢复阶段](../data/experiments/RWKV_ASSISTED_RECOVERY_R1_20260914/REPORT.zh-CN.md)|建议0/2、接管2/2；一个固定问题，未改变生产源码|
|[显式协助阶段](../data/experiments/RWKV_ASSISTED_AGENT_R1_20260914/REPORT.zh-CN.md)|清理旧入口、建议续State与接管新文本根、回归及真实验证|
|[架构与批量阶段](../data/experiments/RWKV_AGENT_ARCHITECTURE_BATCH_R1_20260914/REPORT.zh-CN.md)|当前代码与入口、回归及并发smoke|
|[菜单定位](../data/experiments/RWKV_MENU_LOCALIZATION_R1_20260914/REPORT.zh-CN.md)|19→5菜单两组均0/2，不保留候选|
|[恢复说明对照](../data/experiments/RWKV_REJECTION_RECOVERY_AB_R1_20260914/REPORT.zh-CN.md)|同父State两组均0/2|
|[自主修复验证](../data/experiments/RWKV_QUERY_REPAIR_FEEDBACK_R1_20260914/REPORT.zh-CN.md)|未推进至修改与测试反馈|
|[诊断材料](../data/experiments/RWKV_EVIDENCE_BUG_DIAGNOSIS_R1_20260914/REPORT.zh-CN.md)|根因定位2/2、修复建议0/2，不能合并归因|
|[前端演示](../data/experiments/RWKV_FRONTEND_DIRECT_R1_20260914/REPORT.zh-CN.md)|固定串行演示4/4，非通用能力|
|[飞行轮](../data/experiments/RWKV_FLIGHT_CAMPAIGN_R1_20260913/REPORT.zh-CN.md)|strong归属、续跑、历史失败与限制|

更早结果以各实验原报告及Git历史为准，不把旧分数重算成新收益。StateTune管线见[现状](STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md)，本交接不新增训练授权。


最新R3已完成128条结构复核和100条回答人工语义审核：98回答保留、2歧义隔离；28读取+24回答代表形成52行引用建议，未改旧数据/评分。历史同批已训练384步并因验收退化NO_KEEP，不盲目重训。GPU0完整回归1710 passed（321.23s）。[完整记录](../data/experiments/RWKV_EXISTING_DATA_AUDIT_R3_20260914/REPORT.zh-CN.md)。Owner随后明确授权离线期间继续推进，按[下一轮范围与预算](../data/experiments/RWKV_EXISTING_DATA_AUDIT_R3_20260914/NEXT_AUTHORIZATION.zh-CN.md)先补编码freeze及训练一致性验证，再有条件冻结新数据/训练；此前“本轮不训练”只描述已完成审计轮。
