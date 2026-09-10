# 五角色架构适配复核

轮次：EXECUTION_EVIDENCE_REVALIDATION_R1_20260910。状态：完成本轮证据审阅；完整Agent验收不足，KEEP不成立，需余额恢复后的新轮次补证。

## Agent结果与评估边界

固定15题原始结果：Strict 0/15、completed 0/15、mutation 4、动作28。终止为5题重复成功动作无进展、3题协议拒绝预算耗尽、7题strong_planner_unavailable。后7题官方DeepSeek明确HTTP402 / Insufficient Balance，没有初始计划或RWKV生成；不能把这7题计为模型能力失败或假定Native修复已验证。所有题保留原分母与原评分，没有重评分。

实际发生47个Selector选择边界、74次Executor生成、26次Step Auditor生成；100/100已返回生成完整输入token及100/100角色输入字节核验通过。Finalizer和Final Auditor均未到达。零生成来源的0/0核验不是角色成功，前8题的交接完整也不是语义验收通过。

工程完整回归1447 passed、0 failed；客户端源码b3e89de6冻结不变，服务实际文件按两份完整上传manifest核验，未在服务器调用Git。当前没有StateTune optimizer steps。

## 结论

**目前没有证据要求推翻五角色职责划分；也没有证据允许宣布这套组合已适配项目开发能力。** 保留现有架构继续逐角色数据审计和StateTune，是受现有证据支持的下一工作方向，不是本轮能力KEEP通过。

角色分工帮助定位错误，但“能归因”不是架构性能证明。RWKV定长State与独立角色边界在实现上没有被本轮已返回交接证据否定；本轮没有做与合并角色架构的同代码受控消融，不能声称adjacency原则已经通过架构比较证明。后序两个角色没有观察，不能外推其能力。

## 三个流程问题的修正判断

**证据合同和Step Auditor。** RP-API-01只列目录，Step Auditor却接受读取文件的步骤完成；Stage Checker用同一证据明确指出没有README/server/公开检查文件内容，随后触发有效计划修复。这是有事件锚点的审计误放行，也说明后续阶段审查确实能纠正它。

但不能把所有问题压在Step Auditor上。ULTRA-Code_00001的Planner S1目标是完整解法，success_evidence却只要求创建文件；Auditor和Stage Checker均按这条弱条件放行，实际正确性验证排在尚未到达的S3。此例的上游计划成功条件也是原因，不能将其单独标成Auditor违反既定条件。其他题中Auditor确实返回repair，仍未解除重复或参数错误。后续收紧证据合同应同时明确目标、成功条件、执行事实各自证明什么，避免用额外模型、外置Head或用例特判替代RWKV判断。

**无进展与计划调整。** RP-API-01本轮已在Stage Checker证据支持下再次调用Planner并提交修正计划，最终仍被工具参数/协议拒绝阻塞。因此“没有再次调用Planner”不能作为所有无进展的统一根因，“重复就强制重规划”也不能作为通用修复。现有链路合同规定只有计划遗漏、依赖冲突、目标覆盖缺口等真实依据才有重规划权威；执行失败次数本身不提供这个权威。保留预算阻塞的真实状态，不把它伪装成完成。

**反馈利用。** ULTRA-Code_00002在repair后持续选delete_file而生成write_file，ULTRA-Code_00001连续生成未展示的code-runner工具；这支持模型选择/参数遵循和纠错学习不足。RP-MAINT-01也出现repair后从search_text切换为read_file并推进S1的反例，之后S2又陷入重复；不能概括为“反馈从不改变动作”。要验证的是给定同一角色State时反馈能否稳定改善下一动作，而非机械要求每次必须换工具或缩小合法菜单。

三方向仍各自单变量登记，排在首轮StateTune之后；本轮不修改协议、合法工具菜单、Planner触发条件或评分。前序角色State合格后再按原次序采集后序角色，不用后序未到达阻止合法的首轮训练；同时不绕过当前数据覆盖、相似度、独立标签与预算门。

## KEEP判定

| 原门槛 | 本轮证据 | 判定 |
| --- | --- | --- |
| 不再出现首错丢失的unknown死链 | 实际8题无Native传输失败；旧事故RP-CLI-02被402挡在Planner前 | 整体复测证据不足；不能称旧事故已验证消失 |
| SupervisorGenerationInterrupted下降 | 最新固定15题基线0，本轮所有响应含重试前响应均0；另有7次402 | 未严格下降；402另列，不能混成输出耗尽，也不能换旧R5作比较基线 |
| Strict不劣化 | 0/15→0/15 | 数值持平，但0分下限与7题外部阻塞不能证明能力不回归 |

没有同代码双零噪声带或成功题翻转证据；历史与本轮跨代码结果仅作描述性对照，不构成正式架构消融。工程修复的单测证据和Agent KEEP必须分开。

## 来源

完整逐题结果在AGENT_SUMMARY.json；角色、402原文、服务/验证元数据在ROLE_AND_INFRASTRUCTURE_EVIDENCE.json；逐题原事件引用在*.PUBLIC_CAUSAL_OBSERVATION.json，代表性解释在ARCHITECTURE_CASE_NOTES.md。所有文件SHA由EVIDENCE_SHA256.json统一登记。原raw trace与评分保留在两个独立的新采集目录，Holdout未读取。
