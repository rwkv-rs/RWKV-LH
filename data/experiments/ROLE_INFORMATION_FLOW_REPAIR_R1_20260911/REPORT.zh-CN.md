# ROLE_INFORMATION_FLOW_REPAIR_R1_20260911

## Agent 级结果与边界

本轮没有新增真实模型 Agent 评测：Strict / completed / mutation / 终止原因均无修复后数据，不宣称循环已解决。修复前冻结队列117题：严格成功0、completed0、155次动作、mutation2；116份结果，LH09入口不支持mock_api，无结果和trace。39题进入RWKV，77题在Planner HTTP402停止。逐题最后终止：重复成功31、重复失败3、审计协议预算3、执行协议预算1、Stage Checker不可用1、Planner不可用77、无导出终止事件1。HTTP402和入口失败不能计为RWKV能力失败。

角色层历史证据为Selector 489次菜单评估（163边界×3）、Executor222次、Step Auditor107次、Finalizer0、Final Auditor0。329份生成调用的完整checkpoint链与服务端token一致，未发现传输漏token；818份输入审计为前一轮冻结诊断材料，未重评分、未变成新协议训练数据。原始报告及索引身份见SOURCE_PINS.json。本提交包含原汇总的逐字节副本BASELINE_SUMMARY.json；上轮818份输入仍在原本地目录，不声称本提交已收入该目录全部原始文件。

## 本轮修复

| 原缺陷 | 当前处理 | 全局影响与权限边界 |
| --- | --- | --- |
| 审计异常只有request_id，Controller误从执行decision读取被拒原文 | 按request_id和audit_boundary_id读取持久化goal_audit_recorded.raw_generation.raw_output，写入统一反馈 | Step / Final Auditor重试都能看到自己的错误对象；无生成的前置失败保留空原文，不伪造输出 |
| Selector只有动作参数和元数据，没有正文和累计依赖事实 | 唯一build_current_progress增加共享结果投影与evidence_records | 同样机械进度、不同返回内容现在形成不同输入；正文继续带投影完整性，不能把内容摘要当完整原文 |
| Step Auditor只保留每root最新成功动作，无依赖事实 | Selector / Executor / Step Auditor共用goal_step_evidence_action_ids，保留当前版本全部动作和已提交的传递依赖证据 | action/artifact/revision共用来源解析；分段、同路径多证据不覆盖；旧步骤版本不冒充当前步骤执行 |
| 新增依赖上下文会被完成校验误拒或消除当前步骤缺口 | 完成校验允许引用依赖但只用当前步骤动作证明执行；gap catalog同样检查step_binding | 依赖不能替代当前成功动作、读写范围或allowset；无关步骤、过期版本、失败的当前动作继续拒绝 |
| 机械前提易与语义完成混淆 | Selector字段改为mechanical_preconditions_satisfied，completion_authority固定false，角色说明明确区分 | 原始成功条件保留；是否满足语义仍由RWKV审计决定 |
| 固定reason无法表达这次失败的具体诊断 | reason允许非空的证据诊断，feedback.v2独立保存diagnosis，原criterion不变 | Selector/Executor收到步骤缺陷；Finalizer收到回答缺陷；Planner收到执行证据缺陷；不新增指挥模型、不由Controller发明诊断 |
| 必需事实按12/8/4/2/0或Planner默认12条裁剪 | 当前角色Executor构造与Native恢复、Planner默认投影取消固定事实条数；预算不足中断/阻塞 | 必需动作ID不静默消失；单条内容仍可显式投影，超预算不意味着完成 |
| Prompt replay通用rollover会删除frontier和事实绑定 | 独立Executor保留完整责任输入，超预算抛InputBudgetError，不用通用摘要替换 | 补充先红后绿回归；原型通用执行器的独立压缩路径不作为当前五角色架构入口 |

没有增加角色、外置Head、模型调用或用例路径特判。Planner规划、Selector选择操作、Executor填参数、Auditor判断与Finalizer作答职责保持不变。既有重复动作预算仍是安全终止门，未通过放宽它掩盖循环。

## 协议、重建与兼容性

当前唯一版本：Selector / Executor / Step Auditor v7，Finalizer v3，Final Auditor v5，feedback v2。旧三个角色模块和字节码删除，服务路由、decoder、attestation、生产调用、trace重建与数据入口引用当前模块常量。旧版与未知版输入拒绝，不保留兼容入口。公共单元测试的prompt快照通过当前生产builder重新渲染，生成脚本和源码SHA记录在夹具中；未迁移任何角色训练数据集或confirmation。

本轮只在本地WSL UbuntuRecovered实施，没有上传服务器、训练、创建datasets版本、调用真实模型或push。运行服务仍需按新源码清单及协议重新冻结部署；旧State兼容性未经验证不能直接复用。没有读取Real Agent Holdout V2或运行acceptance_tests/。

## 验证证据

最终完整回归：**1502 passed、0 skipped、249.51秒**，日志FULL_04.log。

- PLAN.zh-CN.md在实现前登记范围、版本和门槛。
- RED.log保留首批10个失败；其中Selector正文差异用例第一次使用了不一致的机械夹具，后续SELECTOR_BODY_RED_GREEN.json使用修正后的同一测试，对冻结2a54bf46源码在内存执行：旧版断言失败，新版通过。没有将旧模块写回磁盘。
- RED_DEPENDENCY_CATALOG.log证明依赖观察错误消除当前步骤缺口；RED_REPLAY_BOUNDARY.log证明通用rollover原先可成功返回但丢失角色边界。均补充相同回归的通过记录。
- NATIVE_RECOVERY_RED_GREEN.json以冻结源码中的原恢复方法在内存执行同一17条事实回归：原方法丢失早期事实，新方法全部保留。GREEN_RECOVERY.log的首次夹具断言把bootstrap正文误当成带动作ID的协议包，修正为检查真实事实路径；原失败日志保留。
- GREEN_BOUNDARIES.log：35 passed，覆盖累计分片、依赖引用、artifact/revision解析、当前执行权限、实际审计重试与无条数裁剪。后续完整回归还包含新增replay边界与五角色持久化重建检查。
- FULL_02为1500 passed；其后补充两项恢复测试，并澄清审计reason：通过时解释证据支持，只有repair时解释缺口，避免要求通过分支也发明缺陷。FULL_03在908 passed时主动中断以纳入最终文本，最终验收使用FULL_04。
- 初次TARGETED/FULL日志保留集成失败及修复过程，不把中间失败当最终通过。最终完整tests/结果见VALIDATION.json及对应FULL日志；包含Torch/State和必需浏览器验证，无跳过才允许提交。
- 五角色生产checkpoint与持久化trace重建逐字节对齐测试同时断言具体diagnosis和审计被拒原文。网络Selector、StateTune入口及协议拒绝测试覆盖版本迁移。

## 未被工程测试证明的事项

真实2.9B/13.3B模型能否利用新增正文和诊断减少重复，需要在服务条件恢复后重新冻结输入/源码/模型/预算，用原评分执行公开完整集合并做同代码双零对照。Final两角色过去没有真实到达，本轮是实际Controller+真实Harness+模拟模型响应的工程验证，不能冒充真实Final模型验证。

本轮没有把多次工具合同披露认定为必然错误，也没有为缩短输入删除原失败上下文。新增事实可能使某些长流程更早触及输入预算；现在应明确阻塞而非丢事实继续。每条结果仍有内容投影上限，保留全部引用不等于所有原始字节永久进入上下文。这些限制和模型本身能力仍可能造成任务未完成。

证据文件与变更源码的逐文件SHA-256见SOURCE_PINS.json、SHA256SUMS。结论只确认本轮信息传递缺陷的工程修复，不满足AGENTS.md全部真实Agent完成条件时不标记整体问题已解决。
