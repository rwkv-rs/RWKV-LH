# 编码纠正候选与用量审计

轮次RWKV_CORRECTION_USAGE_R1_20260914；父提交a441b4b8。只使用GPU 0，不训练、不发布数据集版本、不修改前端或线上决策。本轮不push。

Agent级：无新模型任务验收，Strict/completed/mutation及新模型终止统计不适用，原历史任务分数保持不变。角色级：无新推理/训练结果。下面数字是工程验证及旧trace用量审计，不能作为模型能力提升。

## 结果与边界

1. 新增原子编码纠正验证：使用现有生产replay_run重建完整输入；源文件和before快照绑定；只接受有来源的write_file/replace_text候选，原文执行，不合成参数或答案。两名审核者声明绑定输入/目标；外部固定检查先复现真实非零退出，再在单独副本执行候选并复查。无内容变化、程序未启动、测试仍失败不能成为有效纠正。输出始终training_admitted=false，不能绕过后续数据授权、切分、去重和freeze。
2. 已有真实失败回归：从RWKV_EXPLICIT_EDIT_R1的atomic-2原始归档抽取失败输入、原写入及工具快照，用真实生产重建和Harness重放原无效写入，结果no_effective_change；原文件/答案不改。这不是新生产成功样本，测试中的审核者声明只是用于挑战执行验证器，不代表已审核标签。
3. 确认并修复源重放缺陷：replay_run以前用字典覆盖重复generation_started，重复请求仍可能通过。RED_REPLAY.log真实归档变异复现，现与运行恢复共享generation_trace_integrity，拒绝本轮/父历史重复或未配对请求。没有改变输入协议或构造函数。
4. 新增离线用量账本及CLI：供应商attempt计入失败重试，复制日志去重、冲突拒绝，缺usage/单价记未知；逻辑上下文token与实际费用分开。原生服务GPU秒/峰值尚无证据，混合model/provider日志无统一计费ID时不猜配对。记录最外层延迟、原始协助/终止/验收归属，不把回答提交当通过。

入口及登记字段见docs/EVIDENCE_AUDIT.zh-CN.md。上述验证是离线能力，不自动触发模型、训练或逐步审核。

## 回归记录

新增功能先以缺少入口的测试失败登记：RED_USAGE.log、RED_CORRECTION.log；不能把缺模块当原线上故障。GREEN_CORRECTION.log暴露测试夹具把dict当str，修正夹具后GREEN_CORRECTION_2.log定位接口调用错误；随后GREEN_COMBINED.log发现原样write会改变权限，不能据整树差异认定内容修复，改为对文本候选检查实际文件内容差异。全部中间结果保留，不覆盖旧日志。

目标相关34 passed（1.34s），GREEN_FINAL.log。包括真实源重放、编码候选真实工具红绿、拒绝边界、重复/缺失用量和来源归属。完整tests/使用CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0，结果见FULL_TESTS.log。未排除Torch/State或浏览器测试。

最终完整回归1700 passed、0 skipped（327.49s），较上一轮新增22项。GPU_ENVIRONMENT.txt从实际pytest进程环境核对。源码与文档diff空白检查通过，原始日志按原字节保留。

## 已有生产trace的账本抽查

|来源|调用与用量|解释|
|---|---|---|
|RWKV_GOAL_DELIVERY_R1/runs/fix-query|15次generation配对；供应商3个attempt，63494输入/1223输出token|包含RWKV和接管；不是RWKV独立完成。供应商token不和RWKV逻辑输入相加当物理计算量。|
|RWKV_ASSISTED_RECOVERY_R1/runs/advice-1|本次续跑1次generation；建议供应商1个attempt，10828输入/1175输出token|只计该续跑目录，未包括原父任务费用。|

两份账本均没有登记单价或原生GPU成本，total_cost=null。known_cost_subtotal=0且priced_attempts=0表示没有可计价条目，不表示免费。USAGE_*.json包含原日志SHA、供应商明细和交付来源，旧验收不重算。新CLI真实调用成功。

## StateTune方向

Owner提供四张社区截图，报告G1J 7B约3000条数据训练State后Three.js展示改善；该外部经验支持积极验证，尚未在本项目做受控复现。截图文件SHA单列，没有将社区声明冒充本项目指标。

明确：zero模型低分不是训练禁令；不要求先独立完成所有待改进任务。训练门槛限定在可复核输入/State、可信纠正、隔离回归、授权与预算，不等待所有工程增强完成。优先训练有效修改、库调用与测试反馈，而不只做格式修补。更新统一StateTune计划，不新增在线State路由或专属角色。

## 尚未完成及下一步

- 当前是原子文件纠正候选验证，尚非完整coding训练freeze：现有训练入口仍保持原读取/摘要准入，不兼容扩展必须在获准数据版本中明确登记。
- 两个reviewer字段是可信审核流程的声明；检查器不能证明人员独立，也不能仅靠固定测试证明全部用户语义。审核与外部检查必须先登记。
- 验证使用副本及既有Harness，不提供任意恶意命令的主机安全沙箱；每条命令有时限，不是整个验证过程的OS硬截止。
- 源目录是前后身份检测，非事务快照；单次调用参数无法唯一绑定快照时保守拒绝。不把复杂多步纠正硬塞进当前单步验证。
- 供应商费用仅支持调用方登记统一token单价的估算；未覆盖缓存阶梯价、原生GPU计费、全部资源峰值与项目成本。吞吐收益仍需同质量固定任务实测。
- 下一步按已获准来源盘点可重建边界和可验证纠正，形成覆盖/缺口清单；随后按统一多缺陷数据计划生成。不得再把“等待所有工程完美”作为训练前置条件。

Owner原五处修改不编辑、不暂存；工作diff SHA保持314ca524bbb1e4fc28460409f1068222f29f1819cb410d025edefe64c8f796e0。源码、日志与报告SHA见SHA256SUMS。
