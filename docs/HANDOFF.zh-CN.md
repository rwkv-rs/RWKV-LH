# 当前交接（2026-09-14）

## 产品与当前入口

目标：为RWKV构建专属Harness和Code Agent；同质量下的成本、速度与吞吐是优化指标。当前架构只从[ARCHITECTURE](ARCHITECTURE.zh-CN.md)进入，历史设计不再作为互相竞争的产品入口说明。

当前执行是RWKV直接选择工具/参数→真实Harness→观察及连续State→原始交付→外部验收。默认不调用Planner/Selector/Auditor链。历史多角色构造仍有研究代码及测试依赖，尚未物理删除；不能声称已全部清理。

推荐统一入口：`scripts/run_rwkv_agent.py --jobs /absolute/jobs.json --concurrency 2`。格式见[批量使用说明](AGENT_BATCH.zh-CN.md)。原单任务修改、只读CLI及既有前端共享底层执行；本轮不改页面。

## 正在交付的阶段

独立任务交付与协作阶段已经开始：读取/检查/修改共用批量调度器，全批预算和路径预检查、spawn进程隔离、原结果返回、普通任务启动错误单列。修改任务复制源目录，不自动集成共享文件。任务独立性由目标和依赖决定，不由程序替用户拆分。

本轮并发小批2/2满足事前登记任务要求、2提交、mutation0：读健康检查脚本准确说明范围；递归扫描测试真实运行并如实报告通过。共4真实生成、11936逻辑输入/396输出token，输入和State父链核验。这是集成smoke，不是项目Strict、并发收益或通用修改能力。

工程红→绿及完整验证见[本轮报告](../data/experiments/RWKV_AGENT_ARCHITECTURE_BATCH_R1_20260914/REPORT.zh-CN.md)。已有owner五处修改必须继续保留：controller.py、model.py、supervisor_openai.py、test_hybrid_supervisor.py、test_supervisor_openai.py。未混入本轮代码提交。

本轮真实失败恢复：同一查询问题的两个失败父运行，建议后RWKV 0/2，强模型显式接管2/2；后者均真实修改并测试，外部原测试通过。建议续跑仅1/2次生成即再次触发历史重复保护，不能宣称建议无效或RWKV独立能力提升。完整记录见下方恢复阶段。

## 能力和限制

- 固定单步读取、部分文档总结及明确测试执行已有成功证据。
- 自主多步修复尚未稳定：会重复读取、读不存在路径、不选择修改/测试、无回答终止。不能由此推断不会简单总结。
- 改恢复句及精简菜单未改善固定修复任务，候选不保留；局部定位实验到此收束，不再继续无方向微调。
- State传递和真实观察已多轮核验，未发现可解释上述停滞的遗漏；不等于证明数值State及长上下文利用没有问题。
- 强模型建议/显式接管已接入统一任务入口，归属分开；不增加逐步审核关卡或自动求助路由。当前轮工程和真实验证结果见协助阶段报告。
- 共享文件并发修改、依赖任务集成、自动合并与前端续跑仍未完成。

## 后续顺序

1. 显式strong建议/接管接口已实现；保留固定回归，继续验证真实失败任务的恢复能力，不能用成功父任务的接口smoke宣称恢复收益。
2. 增加有依赖任务的结果集成与最终验收，再测同质量下端到端成本/延迟/吞吐，不提前宣称并发优势成立。
3. 汇总真实失败及经验证纠正后再评估获准数据构建/StateTune；不每阶段训练一次，不把强模型成果当RWKV独立能力。

## 必须保留的约束

遵守AGENTS。所有命令在WSL；服务器禁止Git；不读最终holdout/acceptance目录。不改前端或可视化；本轮不push、不训练、不新建dataset版本。以后授权按具体范围判断。模型输入只走现有唯一构造函数，程序不代选业务动作、补参数或改答案。

预算耗尽/中断不是合格完成，final_answer不是通过隐藏评分；外部验收按目标和真实交付、不限定实现路径。完整逻辑token不是实际费用。生产变更需先失败后通过回归、完整测试后本地一轮一提交。

## 最近证据索引

|记录|作用|
|---|---|
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
