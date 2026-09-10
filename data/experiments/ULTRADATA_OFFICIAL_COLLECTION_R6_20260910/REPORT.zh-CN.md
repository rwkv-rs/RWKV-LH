# ULTRADATA_OFFICIAL_COLLECTION_R6_20260910

Agent **Strict 0/3、completed 0/3、mutation 3、动作 6**。终止原因各 1 题：重复成功动作无进展预算耗尽、工具/参数协议拒绝耗尽、Step Auditor 协议拒绝耗尽。全部 3 题已完成观测，分母不删减；各 433.44 / 248.76 / 165.86 秒，总 848.06 秒。源码与注册参数全程不变。实际 optimizer steps **0**，未创建正式角色数据版本。

## 与上一轮的可观察区别

使用冻结源码 e7c455b6、官方 DeepSeek V4 Pro，Planner/Stage Checker 显式 thinking=enabled、reasoning_effort=low。Planner/Stage Checker 最大输出保持 32768/16384，读取预算 600 秒；题目、评分、固定 family 切分和角色覆盖未改。

R5 为 Strict 0/3、completed 0/3、mutation 0、动作 1，2 题将全部输出 token 用于思考而没有计划正文。R6 的三题都返回完整初始计划、都实际写入了文件；全部 6 次 Strong 请求自然 stop，没有 HTTP 故障或输出耗尽。本次同时改变了提示和思考配置，因此不能把差异单独归因于某个因素，也不能宣称解决所有 Planner 正确性问题。

## 真实错误传播：ULTRA-Code_00001

1. 初始 Planner 给出两个任务所需阶段：实现 main.py、运行公开样例及边界验证。没有沿用上一轮错误的“每行每列非空”不可变目标，也没有把内部算法思考设成额外动作。
2. Selector 正确选择 write_file；Executor 写出的代码却将 D+L!=X*Y 全部输出 0，并在其余情况使用错误组合公式。原始写入内容的独立副本对四个公开样例输出 1/0/0/0，正确答案为 12/10/364527243/976668549，**0/4**。该诊断未改 Agent workspace，没有重新评分，也没有把输出当训练标签。
3. Step Auditor 接受了第一次写入。Strong Stage Checker 依据该代码指出具体计算错误并要求修复；这次重规划有已执行错误的依据，不是仅因后续测试尚未完成。
4. Planner 首个补丁把新 S3 放入 replace，机械校验拒绝；一次有明确反馈的修正后补丁被接受。随后 Selector 在修复时曾误选 delete_file，Executor 输出未展示的 write_file 或无效 JSON；重新选择后仍写回相同程序。只有首次写入实际改变 workspace，最终以重复无进展阻塞结束。

错误主线是“实现错误 → 审计误放行 → 有依据的修复 → 错误选择/无效参数/重复内容”。新交接证据支持模型能力缺陷的定位，不能继续把这些错误全部归因于网关或 State 缺失。另两题在 Step Auditor 的格式/语义判断以及工具选择/参数遵循上失败；后序 Finalizer / Final Auditor 均未调用，不能据此评价其能力。

## 角色与交接证据

Selector 13 个真实选择边界、39 个菜单求值；Executor 19 次生成，Step Auditor 10 次，合计 29 次 Native 生成。对全部三个 case 的 durable 边界使用当前生产 builder 重建：**29/29 角色输入与原交接字节一致，29/29 完整输入 token 核验通过**。没有 Native transport failure。此结论证明已发生的交接，不代表所有角色的任务语义正确。

自动 Selector 标签 12 条：train 9、dev 3、confirmation 0；另 27 条仍为待独立复核。自动标签只支持相应工具选择，不能把其下游错误代码或错误审计判为正确。当前来源不足原注册 30 菜单、10 个合格选择边界，且未到 execute 覆盖，候选为 INVALID。

另有 27/27 个 train/dev 输入比较超过固定 0.95 相似度阈值，典型 cosine=0.993514387239。不同编程题在“实现 main.py”步骤形成了非常相似的角色决策输入，不能因为原始题目不同就绕过角色泄漏检查。作为诊断，同一 dev 编程输入与真实开发题 API-01 的观察输入 cosine=0.871149249999，说明并非一切生产输入都必然被相同固定模板判为重复。本轮相似度算法、文本字段和阈值均未更改。

## 下一步

REALPROJECT_OFFICIAL_COLLECTION_R3 的固定 12 题已启动，继续保留当前源码，逐题收集实际边界和错误。两组来源全部完成后统一核对覆盖、标签、固定切分及污染；不能为满足训练条件补造后续阶段、伪造双人复核、重命名 family 或降低门槛。只在合格数据到位后按现有授权登记实际 Selector StateTune。低 Agent 分数本身不构成训练禁令。

完整原始结果与运行证据保留在本地 all_zero/cases；这些较大的原始文件受现有 Git ignore 规则控制，路径和 SHA 均收入 EVIDENCE_SHA256.json。代码与摘要本地提交，owner 负责 push。Real Agent Holdout V2 未读取。
