# 当前交接：工程机制已验证，完整项目交付尚未通过

维护文档仅描述当前实现、有效验证、未解决问题和下一步。历史设计与轮次说明从 Git 查询；原始运行、失败及 SHA 保留在本地，不随源码发布。

## 已完成验证

最近完成全链路审计的 Agent 测试：**Strict 0/4、completed 0/4、mutation 3、独立功能验收 0/4**。终止为调用预算耗尽 1、输出预算耗尽 2、原记录 uncertain_operation 1。静态作品集 Chromium 检查 **18/19**：页面、移动端和导航可用，缺 README；不能将可展示页面称为完整项目交付。

角色记录：84 次预留、83 次实际开始/返回，Decision 42、Executor 18、Planner 23。60 次 Native 返回、20,578 个原 token 独立 Guidance 掩码审计通过；58 次完整参数合法、2 次截断未测量、测得缺必填 0。23 次官方 DeepSeek beta strict 请求、26 个原工具参数合法，未发现已发生成缺回执。格式合法仍不能证明行为或事实正确。

正式 exact-token 入口的两个真实角色探针通过 create→generate→rollback→release；原 prefix 与 1,842 个生成 token 独立核对，未提交为 Agent 后续 State。该证据只证明接口生命周期，不提供角色训练资格或 Agent 完成证明。

本次重新执行完整本地回归 **2910 通过、0 跳过（729.14秒）**，Torch、State 注入和必需 Chromium 未绕过，完整源码/测试集合与 SHA 核验一致。测试对象是包含既存 owner 未提交工作的冻结工作树；纯提交源码另做干净导出构建及入口检查，两者不是同一测试对象。

上述最新完整审计报告：`data/experiments/PROJECT_LOSSLESS_HANDOFF_R161/REPORT.zh-CN.md`，SHA-256 `6335c10c23bd4a725154e09e263f5be49948088b726d8864a4e62c7baa1aa082`。逐次原文与服务请求、返回、journal 由报告索引复核，不在本文件累积旧成绩。

## 当前测试与发布

前端扩展已登记 3 类任务×2 个种子，共 6 次：作品集、任务看板、阅读清单。保持 G1j 13B zero、Native Guidance 约束开启、官方 Planner strict；每次 40 调用/900 秒、两个专用 GPU，生产源码和评分冻结。没有 OFF 对照，不因格式通过推断一般能力提升。

用户要求先完成文档和 GitHub 更新，当前已暂停后续批次接纳，已发送的任务自然结束。任务看板首个已审计运行 Strict 0/1、completed 0/1、mutation 0，Executor 首次写入重复 CSS 至输出预算，文件未发布；其余结果尚未构成完整批次结论。重新执行的完整回归已完成：2910通过、0跳过、729.14秒，完整源码与测试清单前后相同。当前过程：`data/experiments/PROJECT_FRONTEND_EXPANSION_R162/`，预注册 SHA-256 `87e532e14c027d76e0151ca7c4266fcfaf83a15ec5e7e3f5b19244fe1f027d55`。

GitHub 发布只含已提交维护源码、当前文档和构建配置；测试、数据、页面产物、凭据及 owner 未提交工作保留本地。采用基于已发布远端提交的新源码分支，避免上传包含实验材料的本地未发布祖先；不改写 main 或远端既有历史。上传后继续登记中的测试，不重复发送已开始任务。

## 当前实现

完整目标→Decision 按证据选择直接执行或强模型规划→Executor 连续执行与局部修正→独立检查→Decision 判断目标满足→完成门。原始目标、模型设计和可执行检查分别保存；Controller 只校验权限、身份、真实回执、State 和完成条件，不代选动作。

当前唯一协议：Ledger v10、Goal v1、Plan v5、Assignment v6、Planner v14/chat v3、Decision v17、Executor v13；prompt v7、输入传输 v2、格式适配 v6。Planner 的明确只读多调用保留全部原参数、顺序和逐条回执；同次输入内完全相同的长块可逐字共享，实际 token 不省则保留原文。所有新 RWKV 模型实验开启约束，不兼容 State 不复用。详细行为只在[架构](ARCHITECTURE.zh-CN.md)维护。

## 未解决问题与下一步

1. **长代码正文重复与错误实现。** 约束只保证生成形状，字符串内仍会重复至截断；也会把 JSON 包装写成源码。先完成已登记的前端两种子运行，逐次区分未写入、可展示、交互正确和完整交付，不手工补文件冒充模型结果。
2. **Decision 反复取证、错误 ID 和虚报交付。** 保留已送达的原回执、后继输入和 State，核对同一证据内容未变却因 revision 递增再次投递的影响。单次输入共享不解决跨次重复，Controller 不按次数换动作。
3. **Planner 检查编写和审查往返。** 仍可能把实现缺陷误判为检查缺陷；模型虽可显式 advise 交回 Decision，实际使用和恢复尚未稳定。检查应忠实于原目标，不能取消审查或把 reject 转成 accept。
4. **Planner 输入预算与操作预留顺序。** 已证实一次本地输入 99903>98271，在 generation_started/HTTP 前被拒绝，却留下 pending 和 uncertain_operation。下一工程修复统一实际 chat 传输计量并前置预算检查；保留真正已发 UNKNOWN，不重发。Planner 结构化 chat 尚未共享重复原文。
5. **数值与服务约束可靠性。** Native 非有限 State 的首个失效算子尚未定位；官方 DeepSeek strict 存在已复现的 schema 违例。实际请求、回执与本地校验继续留证，不能声称闭源强制约束已经可靠。

训练步骤 0、当前可准入角色候选/正式训练行 0，无新 datasets、Holdout、OA 操作。继续当前 G1j 分支；Decision StateTune 先补真实来源、独立纠错审查、覆盖与固定隔离回归，开发题和接口探针不转成训练样本。训练规则只在[数据入口](PROJECT_ROLE_DATA_PIPELINE.zh-CN.md)与 `AGENTS.md` 维护。
