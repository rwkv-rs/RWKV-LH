# 第一轮：当前状态与下一步

当前以最近六次前端运行作为第一轮基线，不沿用此前累计轮次或汇总旧批次成绩。只保留当前实现、有效验证、缺陷和下一步；原始运行身份不改写，编号整理不代表重新运行。

## 当前验证结果

三类前端任务、两个种子、六次固定预算运行：**Strict 0/6、completed 0/6、mutation 2、独立功能验收1/6**。两次调用预算耗尽、四次输出预算耗尽。一份作品集实际生成index.html和README，独立Chromium **19/19**；其余五次未交付入口。未证明稳定项目交付或一般能力提升。

作品集的成功产物在第31次审查接受检查后，第32次Decision再次bind_checks，未选择verify，最终40调用耗尽；另一个种子试图改写受保护TASK.md，被拒绝后38次读取同一回执。看板和阅读清单的四次首次写入均在正文重复或样式过度展开后触顶，没有执行写入。

88次预留、开始和返回一致：Decision46/Executor10/Planner32。56次Native全部约束开启，23,248个原token独立Guidance审计通过；52次完整参数合法、4次截断未测量、测得缺必填0。32次官方DeepSeek beta strict请求，39个原工具参数合法。没有缺失客户端返回或未匹配服务生成。格式合法不等于检查安装、动作方向或交付正确，语义守卫拒绝另行统计。

清理后完整本地回归**2910通过、0跳过、722.10秒**；Torch/State/必需Chromium未绕过，完整生产源码、通用脚本与测试SHA前后一致。测试对象含既存owner未提交源码，与公开纯提交源码分开；公开源码另通过干净安装/编译、六命令help及sdist/wheel检查，公开CI不替代完整回归。

当前报告：`data/experiments/ROUND_01/REPORT.zh-CN.md`，SHA-256 `6927c18c0bc91c0b36223937d0498eaca343d0a36ffe400c15389c6685936a6c`。同目录 `CALL_INDEX.zh-CN.md` 索引全部 88 次原文，`RUN_DIAGNOSES.json` 记录最早故障，`SEMANTIC_GUARD_AUDIT.json` 保留安装与权限拒绝。`DELIVERY/index.html` 和 `frontend-round-01.zip` 提供六次原始工作区，文件 SHA 与原独立验收一致。

旧实验和临时脚本已按用户要求清理，当前第一轮的原始登记、调用、失败、产物和 SHA 保留；删除清单见 `CLEANUP_RESULT.json` 与 `CLEANUP_FILES.jsonl`。原始证据中的旧路径按 `BASELINE.json` 映射解释。

## 当前架构

完整目标→Decision基于证据选择直接执行或强模型规划→Executor持续执行与局部修正→独立检查→Decision判断目标满足→完成门。原目标、模型设计与可执行检查分开；Controller只校验权限、真实回执、State身份和完成条件，不代选动作。

唯一当前协议：Ledger v10、Goal v1、Plan v5、Assignment v6、Planner v14/chat v3、Decision v17、Executor v13；prompt v7、输入传输v2、格式适配v6。Planner只读批次保留原参数、顺序和逐条回执；同次输入完整相同文字可逐字共享。Native exact-token预填充与真实清理生命周期已验证，旧State不静默复用。所有新RWKV实验约束开启；继续G1j分支。细节只在[架构](ARCHITECTURE.zh-CN.md)维护。

## 当前缺陷与下一步

1. **检查绑定后的方向输入。** 原始输入已含awaiting_verification、完整检查和真实报告，但boundary退回task_direction，bind_checks仍可选。首次增加checks改变完整contract_digest后，步骤摘要把已有执行显示为未做。先修事实投影与边界问题、明确初次绑定/有证据替换条件；动作仍由RWKV选择。需要先失败再通过回归及新受控运行，尚不能把它认定为全部停滞的原因。
2. **重复与正文组织。** Decision会反复读取已知失败回执；Executor会循环CSS、重复JS字段或过度展开样式至截断。模型失败与重复投递的工程影响分别排查，不能靠自动换动作、补写文件或只加预算制造通过。
3. **Planner预算与预留。** 存在本地输入超限、尚未generation_started/HTTP却留下pending的已知路径。统一实际chat+tools计量并前置检查，保留真实已发UNKNOWN；Planner结构化chat尚未共享重复原文。
4. **检查质量与强服务可靠性。** 审查可能混淆实现缺陷和检查缺陷，也可能接受设计过窄或覆盖弱的检查；官方DeepSeek strict存在已复现schema违例。原始wire、角色校验、独立审查和实际验证继续保留。
5. **数值定位与训练来源。** Native非有限State的首个失效算子尚未定位。当前正式角色训练行/可准入候选0；Decision StateTune先补真实来源、独立纠错审查、覆盖与固定隔离回归。开发题和接口探针不转为训练数据。

具体代码路径与下一阶段回归边界：当前报告同目录`NEXT_STEPS.zh-CN.md`。本轮未改生产源码、训练0、新datasets0、Holdout0、OA0、远端Git0。

## 发布与资源

公开分支：`chase/g1j-agent-improvement-public`；只发布允许的当前源码和文档，不带本地实验材料或未发布研发祖先，不改 main。源码发布边界见[发布规范](SOURCE_DISTRIBUTION.zh-CN.md)。

第一轮产物和验证证据保留本地。两个专用 Native 服务和隧道已停止，当前没有待核实 UNKNOWN。清理及发布核验见第一轮目录；源码提交身份与运行时冻结身份分别记录。
