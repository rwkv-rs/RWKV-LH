# Round0：弱模型友好 Agent 项目源码分析

## 结论边界

本分析只登记可进入后续消融的架构假设，不代表某项机制对 G1i-13.3B 有效。是否采用只能由
固定 90 题的真实 RWKV 对照结果决定。参考仓库只读保存在 temp/reference_projects/，精确
commit 见 reference_projects.json。

## 1. mini-swe-agent：先验证极简闭环

源码：src/minisweagent/agents/default.py。

主循环只做 query → execute_actions → observation，模型消息和环境输出按顺序进入同一
trajectory。它不维护第二套语义状态机，也不在中间替模型选择答案。mini.yaml 的观察模板在
输出过长时保留前 5000 和后 5000 字符，并显式告诉模型省略量。

可消融假设：

- 将 RWKV-LH 当前 Plan/Action/Verification 多阶段调用与“单 RWKV state 上的一次动作一次观察”
  极简循环对照；
- 工具输出过长时采用可复核的 head+tail+artifact，而不是模型外主观摘要；
- 格式错误只回传原错误并让 RWKV 自修，达到预算后真实失败。

禁止借鉴：自动生成提交内容或在达到步数时替模型补最终答案。

## 2. SWE-agent：接口本身是模型能力的一部分

源码：sweagent/agent/agents.py、sweagent/agent/history_processors.py。

ACI 为下一步观察、空输出、截断输出和格式错误分别提供稳定模板。截断会告诉模型保留长度和
被省略字符数，并建议使用更小的读取命令。这些机制不决定任务答案，只降低模型与环境之间的
接口摩擦。

可消融假设：

- 为 G1i 提供更短、更稳定、单一动作的工具表面；
- observation 统一包含 action、return code、stdout/stderr、截断位置和 artifact ref；
- 失败反馈只描述实际环境差异，不包含规则生成的“正确下一步”。

禁止借鉴：reviewer/chooser 根据候选结果打分并选择提交；这会越过 RWKV 单模型决策边界。

## 3. smolagents：完整 typed step trace 值得保留

源码：src/smolagents/agents.py、src/smolagents/memory.py。

每个 ActionStep 保存 model input、model output、tool calls、error、observation、action output、
token usage 和 final 标志；planning step 也独立记录输入输出。这个数据模型适合因果分析。

可消融假设：

- 为 RWKV-LH 每次模型调用增加独立的 raw output → parsed payload → action → observation
  转换记录；
- periodic plan update 只能由同一 RWKV 根据已有真实观察生成；
- summary mode 必须保留原始事件引用和未压缩 artifact。

明确不采用：

- final-answer checks 失败后拒绝模型答案并继续选另一个答案；
- max-step 后额外调用模型生成一个替代答案；
- 使用另一个模型做 planning、judge 或 summary。

## 4. Letta/MemGPT：分区预算与持久状态

源码：letta/services/context_window_calculator/context_window_calculator.py、
letta/services/summarizer/summarizer_sliding_window.py、letta/schemas/memory.py。

Letta 分别计算 system、core memory、memory filesystem、tool rules、directory、summary、
messages 和 tool definitions 的 token，占满时按消息边界压缩。这说明上下文管理应先看数据来源
和预算，而不是把所有历史拼成一个字符串。

可消融假设：

- RWKV 上下文按 Goal、当前任务、依赖证据、失败、工具表和保留输出分区计数；
- recurrent state 可用时保存 parent/fork/commit/rollback；不可用时明确记录 prompt replay；
- 压缩结果必须引用原始事件和 artifact，原始数据不可丢失。

明确不采用：由外部总结模型决定保留事实。首轮只能让同一 RWKV 生成摘要，并与无摘要/确定性
head-tail 方案做固定数据对照。

## 5. aider：结构地图是输入视图，不是答案筛选器

源码：aider/repomap.py、aider/coders/base_coder.py。

repo map 用 tree-sitter 提取定义/引用，在固定 token 预算内提供符号与少量上下文。它组织模型
输入，但不编辑模型输出。lint/test 的真实错误可以作为下一轮模型观察。

可消融假设：

- 对代码任务提供只含路径、符号、签名、引用边的紧凑 workspace map；
- RWKV 自己选择要读取的文件，地图不能按参考答案隐藏或强调文件；
- lint/test 结果原样回给 RWKV，不由程序生成修复。

风险：aider 会按提及标识符和图排名筛选上下文。RWKV-LH 若实验该机制，排名只能依赖题面和
工作区结构，必须记录被纳入/排除的节点，且不得读取 acceptance。

## 6. 首轮候选次序

Round1 先运行当前整改后的基线，不混入参考项目机制。分析后只选择一个有数据支持的单变量：

1. 优先候选：mini-swe-agent 式单动作/单观察循环；
2. 第二候选：统一、短、可复核的 ACI observation；
3. 第三候选：分区上下文预算；
4. 代码题确有“找错文件”证据时再测试 repo map；
5. recurrent-state API 实际可用后才测试 state fork/commit。

## 7. Prime Agent：借鉴状态与协议工程，不复制通用 RLM 产品

固定源码：PrimeIntellect-ai/prime-agent，commit
`a3b3e753490d0a6ed180e905200c1a6690d78608`。2026-08-12 核对时该提交同时是远端
`main` 与 `HEAD`；“当前主线”不等同于对 RWKV-LH 已证明最优，所有机制仍须固定 90 题消融。

`packages/coding-agent/src/core/autonomous.ts` 在 gate 失败后保存 Git worktree snapshot；下一次
若 status、diff、untracked hash 均未变化，就不重复执行同一 gate，但仍增加 attempt 并受
maxRetries 约束。RWKV-LH 可借鉴其“不变 observation 不重复验证”原则，但不能照搬：benchmark
workspace 未必是 Git 仓库，且外部状态、时效性 verifier、超时和进程状态不能缓存。候选 digest
必须绑定 Goal、task、criterion、action、artifact hash、deterministic verifier 和 workspace
manifest；相同 digest 时转向 producer correction/recovery，而不是规则生成答案。

`docs/compaction.md` 的结构化摘要保留 Goal、约束、进度、决策、下一步和累计文件操作。RWKV-LH
若实验该机制，应由 Immutable Goal、Task、CriterionEvidence、RecoveryState 和 artifact hash
确定性生成状态胶囊，模型自由摘要不能成为完成证据。`docs/session-format.md` 的 parentId 树可映射
到 `ModelStateRef.parent_state_id`，但只有推理后端显式声明真实 recurrent-state API 后才启用。

Round2 已实现第一项边界协议借鉴：透明展开已知完整 task/function 外壳并记录归一前后 payload。
它把 External 由 7 提高到 8、Strict 由 5 提高到 7，但 FP 从 6 增至 12，说明协议摩擦降低后
暴露了完成证据问题，不能把归一本身视为最优终点。后续可分别消融 unchanged-observation gate
和确定性状态胶囊；不得引入多 provider、subagent、IPython 万能工具、在线 refinement 或答案筛选。

每项必须在同一 90 题上完整重跑，不能按失败 case 添加规则。
