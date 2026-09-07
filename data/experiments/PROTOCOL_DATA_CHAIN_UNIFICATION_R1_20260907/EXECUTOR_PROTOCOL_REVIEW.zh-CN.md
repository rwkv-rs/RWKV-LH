# Executor 协议统一记录

Agent 级：本次未运行模型 Agent 评测，Strict / completed / mutation 数 / 终止原因均无新结果。没有启动训练，也未读取 Holdout 或 confirmation。

角色级：Executor 及关联协议、会话、参数溯源、角色配置首批回归 100 passed；Controller 首批集成回归 61 passed。移除更早的独立 Executor fallback 后，最终定向回归和协议静态门禁合并 108 passed；同期 model.py 调用方集成另由角色协议子任务覆盖。

## 根因与整改

原 Executor v4 委托完整 v3 renderer/validator/parser，Controller 另行组装 execution_state，generation boundary 同时接受 v2/v3/v4。单一输入格式在模块结构、构造路径和生成边界三个位置均未闭合。

- v4 内聚全部验证、渲染、解析；按本轮 owner 最新明确要求，删除 executor_args.py 与 executor_args_v3.py，不保留旧 identity stub。
- build_execution_state 从绑定当前 step revision 的 durable actions、机械证据和 repair gaps 投影；Controller 保留 revision 校验和 action 排序，调用共享构造器。结果游标、完整性与异常字段的规范化保持原生产规则。
- build_target_contract 统一 Harness descriptor 字段投影、字段顺序和 schema 常量；Controller 已有目标兼容性判定维持原规则，仅返回值委托共享构造器。
- build_prompt_source 统一 observation_binding 与输入字段顺序，build_source 委托它附加带 verifier 的训练目标。生产模型调用该输入构造器。
- model_io generation boundary 使用 v4 schema 常量，并通过同一 renderer 复核完整协议；不再只校验 schema 和若干顶层字段。旧 v2/v3 明确拒绝。
- 同时删除更早的独立 Executor request-last/retry-question 格式、披露 renderer、retry 参数和 generation fallback。Session 的披露入口仅接收 executor_source，通过 v4 renderer 构造输入，并核对已选工具契约；独立 lane 缺少完整输入时，HTTP/native 两种传输均拒绝披露或生成。bootstrap 角色说明不再暗示 Executor 可以输出 Final。
- Session 在 checkpoint 中保留 executor_protocol_required 标记，保证 append、candidate/commit、rollover、fork 后不能退回通用披露；非独立 Selector 的通用工具会话仍按其明确角色运行，不标记为 Executor 输入。
- 测试改用共享构造函数；协议负例只在合法 builder 输出上修改。测试 fixture 不再使用 temp/ 下的工作目录。

## 证据与边界

executor_red.log 记录修复前 2 条失败：旧 v3 仍可执行、缺少统一 execution_state builder。随后 owner 将“保留 identity stub”改为“完全删除旧代码”；对应最终回归检查旧模块已不存在。executor_green.log 记录 100 passed，executor_controller_green.log 记录 Controller 61 passed。

新增生成边界回归覆盖当前 v4 接受、v2/v3 拒绝以及 observation_binding 非法事实权限拒绝。目标构造迁移在原有 Controller 集成回归中通过；本轮操作前 v3/v4 尚未纳入 Git，HEAD 也没有对应 Controller 方法，因此本记录不声称已执行修复前后完整 prompt 字节对照。

追加旧入口回归的失败证据见 executor_legacy_session_red.log：HTTP/native 两种 Session 的独立 lane 在没有协议 source 时均错误接受披露。executor_legacy_session_green.log 覆盖整改后的两种传输、bootstrap 生成拒绝、输入披露、一次生成与提交、append 和 rollover 的标记保留，以及未知版本 v999 拒绝、旧 renderer/参数不存在、实际枚举协议模块只能有五个角色。

## 输入帧解析补充整改

根因复核发现，按字符串 rfind 查找当前协议 prefix，会把合法 current_requirement 或 executor_history 中引用的 prefix 当成真实帧开头。补充回归先出现 4 failed / 2 passed（executor_framing_red.log），覆盖普通 prefix、伪 JSON 对象、完整合法帧的文字引用，以及包含引用的最终 retry 输入。

生成边界现在仅从输入起始位置或生产 Session 的空行分隔位置解析完整 JSON 文档，且文档终点必须恰好位于最终 Tool Call anchor 之前；随后仍由 v4 renderer 复核字段、顺序与语义。这样既允许字段中的协议文本，也拒绝在有效当前输入后追加的旧版本或未知版本真实帧；此前输入不能替代最后一次请求。协议和 HTTP/native Session 定向验证合计 88 passed，见 executor_framing_green.log。此改动只修输入帧定位，不改变模型生成输出的 parser 或 stop boundary。

## Fork 输入约束补充整改

最后复核发现两种 Session 的 fork 没有复制 parent_metadata，导致 executor_protocol_required 丢失。新增 HTTP/native 回归先出现 2 failed（executor_fork_red.log），证实 fork 后无 source 披露被错误接受。修复后 fork 保留父 checkpoint 的输入约束，并将独立 Executor assignment 作为无生成 anchor 的事实追加，使新分支只能在提供完整 v4 source 后生成。回归同时验证拒绝无 source 披露/生成，以及提供合法 source 后可正常生成；最终协议和 Session 合并 90 passed，见 executor_fork_green.log。生产代码在该验证后冻结，完整测试由主任务对最终代码执行。

源码与日志 SHA-256 见 executor_SHA256SUMS。该文件记录本子任务交付时的源码指纹；主任务后续共享文件变化应以最终全套验证后的总 SHA256SUMS 为准。本次没有提交，由主任务完成全套测试后统一本地提交。
