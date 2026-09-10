# 本轮逐题架构观察

只根据冻结生产事件分析，不改评分、不向Agent反馈本文件。最终全套数字见AGENT_SUMMARY.json；未结束题不计为通过。

## ULTRA-Code_00001

Strict=false、completed=false、mutation=1、action=1；终止protocol_rejection_budget_exhausted。14/14已返回生成完整token及14/14角色输入重建通过；没有Supervisor失败或Native首错事件。

CE-000003：Planner S1 objective要求完整解法，但success_evidence只有“创建或替换main.py”。正确性验证分配到后续S3。CE-000011代码把D+L不等于X*Y的情况全部输出0，仍含与旧轮相同类别的算法错误；本轮未重评分或将人工实现灌入workspace。

CE-000016/18：Step Auditor对S1给出evidence_complete。CE-000021：Stage Checker advance的明确理由是文件成功写入并存在。此证据显示完成合同较弱，但不能把本例单独定性为Auditor违背“仅创建文件”的success_evidence；Planner目标与成功条件、后续验证安排也在上游影响链中。算法正确性直到S3才可能验证，而本例未到达S3。不能用“审计模块单点放大器”替代这个跨模块区分。

CE-000028至CE-000093：S2要求检查文件输入输出和标准库。Selector先选search_text，后转file_digest；Executor共12次坚持输出当前未展示的code-runner-mcp-server-run-code，系统明确拒绝并保留当前步骤，未执行该工具。最后CE-000094按协议拒绝预算阻塞。这支持“反馈已存在但模型参数/操作遵循不足”的诊断；最终核验重建证明输入交接完整，不证明反馈语义已经生效。

未到Finalizer/Final Auditor，不评价两者能力；也没有证据要求将五角色合并或用外置Head补救。

## ULTRA-Code_00002

Strict=false、completed=false、mutation=1、action=1；终止protocol_rejection_budget_exhausted。14/14完整token与14/14角色输入核验通过，无Supervisor或Native传输失败。

CE-000011成功写入后，Step Auditor首次格式错误在CE-000018被拒；CE-000020/22接受的是repair并给出缺口，未机械地把写入判为任务完成。随后CE-000031至CE-000091，Selector反复选择delete_file，Executor坚持输出当前未展示的write_file，均被拒绝且不产生删除副作用。此例显示审计修复反馈已进入后续边界，但工具选择与参数输出不能协调；不能用“所有Auditor都误放行”概括15题。

## ULTRA-Code_00003

Strict=false、completed=false、mutation=2、action=3；第三次写入不产生字节变化，终止identical_success_budget_exhausted。5/5交接核验通过，无传输失败。两次审计均选择phase_evidence_unproved:mutate并要求repair，随后仍写同一目标，最终触及原无进展门。本例需要在Auditor后续训练中区分具体业务缺口与笼统phase缺口；这里不把缺口文本本身当已证明根因。

## RP-API-01

Strict=false、completed=false、mutation=0、action=4；终止protocol_rejection_budget_exhausted。20/20交接核验通过，无传输失败。

CE-000011只完成list_directory；Step Auditor在一次协议纠错后于CE-000020/22把S1标为完成。CE-000025的Stage Checker明确指出目录清单没有提供README.md/server.py/verify_public.py内容，要求repair。此处有明确的Auditor证据误放行及下游审查纠正，不能归因于输入字节丢失。

Planner先有补丁语义拒绝，纠正后CE-000027提交新计划；不同于历史该题未再次调用Planner，本次确实已有证据支持重规划。后续read_file与两次search_text仍未满足步骤证据；Auditorrepair之后，Selector选择file_digest，Executor反复给出不在绑定发现项中的./README.md或无效JSON/未展示function，最终阻塞。重规划已发生而仍失败，不能把“强制再调Planner”当通用解决方案；需按工具选择、参数合同、具体证据解释与反馈利用分别训练和验证。
