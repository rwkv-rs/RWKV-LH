# TASK_OUTCOME_AUDIT_REFORM_R1_20260913

本轮整改当前任务级审核方法，没有运行新的 RWKV 推理、强模型建议或训练，没有改变 RWKV 能力。最终产品仍是 RWKV 专属 Harness 和 Code Agent。

## 任务结果先行

复用上一轮全部 16 条真实轨迹，按新契约作回顾性演示：full 8 条无交付；readonly 7 条无交付、1 条满足主要要求但有轻微事实表述问题。原始答案、旧实验分数不改；全部记录禁止用作新收益证据。两臂实际 mutation 0、虚假工程完成声明 0；full 6 协议中断和 2 预算中断，readonly 6 协议中断、1 预算中断和 1 提交。

唯一答案正确定位 verify_public.py，概括健康检查并指出不能验证预约、冲突、取消幂等和持久化。原文“只做 /health 的 200 响应检查”过强：文件还检查 JSON ok。新契约允许省略一般断言细节，但不免除措辞的事实责任，因此保留 minor contradiction。它不再与没有任何答案混为同一种失败。这是非盲回顾性人工语义判断，不是对新标准收益的独立证明。

诊断数字：full 21 调用、101598 输入 token、5073 输出 token；readonly 20 调用、75644 输入 token、6628 输出 token。两臂各 6 次协议拒绝。数字来自原始 token id 数组；本轮不新增执行模型调用。费用、资源峰值和收益不在本次结构整改中估算为零。

## 已落实的改动

1. `rwkv_lh/task_review.py` 统一外部契约、来源绑定、语义审核记录和任务聚合。必要结果逐项审核，可省略细节独立记录；保留部分满足、无交付、无效和证据不足。
2. 真实答案须通过生产 parser/最终参数验证，并有 candidate commit 事件；不采纳被拒绝候选或被改写的 RESULT。审核不能自动生成答案。
3. 每个条件绑定用户原文和遗漏影响；审核意见绑定契约、原始运行和文件 SHA。无效排除也需要证据。CLI 聚合重新校验所有原始绑定，拒绝篡改、重复计数和覆盖输出。
4. 首错即停只承认 boundary_probe，完整 task_trial 要求真实反馈策略。预算耗尽保留终止原因；提交不等于质量通过；恢复的错误不自动否决正确交付。
5. 强模型介入显式登记三类归属。归因保留观察/假设/确认层次，不能把大输入或一次失败直接升级为输入/State 根因。
6. 完整任务×重复次数网格质量门与收益门分开；基线天花板单列，不把不可达提升门当模型失败。历史回顾不能通过新收益门。
7. `scripts/review_agent_task.py` 提供 freeze/capture/packet/assess/aggregate/gate；新实验使用此入口，旧 temp 评分器只保留历史证据用途。

## 范围、兼容与验证

排查当前摘要、建议、StateTune 与定位实验的评分入口及相关生产代码。当前诊断评分主要在实验/temp 脚本，生产 Controller 已有真实协议错误反馈，不需要为“无反馈”猜测修改 Controller。`statetune_evaluation.py` 的角色诊断、私有项目 verifier 和历史原始评分不是新任务结果审核的替代品，也不在本轮改写；没有读取保留集。

新增模块没有被模型输入构造器或运行时 Controller 引用，不改变工具菜单、参数、State 或补偿分支。当前 capture 只适配已知只读诊断格式，未来写任务必须绑定真实交付快照；不能仅凭一个答案证明代码验收。结构校验不代替语义审核：要求是否重要、事实问题影响多大仍需可复核的外部意见，分歧不得静默隐藏。

红绿记录：RED.log 为统一审核行为不存在时的失败；RED_HARDENING.log 为缺失 commit/显式归属与无效证据约束时的失败。GREEN_FINAL.log：28 passed。真实 trace 导入包括全部 16 条；CLI_VERIFIED_SUMMARY.json 与 RETROSPECTIVE_SUMMARY.json 一致。

全测第一遍 1173 passed/385 errors：并行启动默认定向 pytest 清理了全测嵌套 basetemp，导致 FileNotFoundError。属本次测试调度干扰，原日志保留。独立复查受影响的角色 trace 集成模块 46 passed；随后串行全量重跑：1558 passed，0 skipped，318.46 秒，见 PYTEST_FULL_R2.log。未跳过 Torch、State 或浏览器检查。

四类前瞻契约与任务要求分别冻结在 forward_contracts/，执行源码和参数来源见 FORWARD_REGISTRATION.json / FORWARD_SOURCE_MANIFEST.json。本轮仅冻结、不执行；现有首错即停 runner 不满足完整 task_trial，运行前必须证明真实反馈与 State 续接并匹配身份，源码变化需另行冻结，不能沿用旧记录冒充。

## 下一步

先用冻结契约与真实反馈链建立最小任务基线，允许 RWKV 自己处理工具拒绝，不补参数、不强迫 final。随后继续输入敏感性定位：先固定质量审核，再一次只改变一个输入组织因素，保持文件/目标/模型/采样/State/预算一致。没有差异证据前不重构、不扩展角色或任务难度，不把工程/评测故障直接收为 StateTune 模型错误。

文件清单、逐项 SHA 与保留修改核验见 EVIDENCE_MANIFEST.json。原有五个修改文件不纳入本轮提交；本轮仅本地提交，不更新 GitHub。
