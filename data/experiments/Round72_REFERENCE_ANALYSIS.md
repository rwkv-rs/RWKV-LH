# Round72 外部机制参考分析

## 固定来源

| 项目 | 固定提交 | 本次读取范围 | 用途 |
| --- | --- | --- | --- |
| `cgisky1980/ai00-x-client` | `83d2fe2a2329c7055616d5e1ce6ec50451cb67e0` | session compression、structured fallback、router prompt、session title 前端逻辑 | 评估本地代码预读、用户输入摘要、任务标题和搜索/路由机制 |
| `cgisky1980/rwkv7-state-embedding` | `bc6755a120d177178a1a52c75f750127b2cee95a` | `README.md`、`paper.md`、`scripts/03_classification.py`、`data/golden_balanced.jsonl` 样例 | 核实 `0.93` 分类指标的任务定义、数据与可迁移边界 |

- 来源：两个项目的 GitHub 原始文件和 Git tree API；首次浅克隆因远端连接中断，未把不完整克隆当作证据。
- 文件摘要：提交 SHA 即本次分析的版本身份；上游仓库内容不复制进 RWKV-LH。
- 生成方式：逐文件阅读实现与论文说明，并对照 Round71 的 15 题真实失败链。
- 本文用途：只登记可实验的架构候选，不授权把外部模型、自由摘要或路由结果用作答案/验收事实。

## ai00-x-client 可借鉴的内容

### 1. 上下文压缩的结构边界，而不是自由摘要本身

其 `ContextCompressor` 有四个值得保留的设计点：

1. 头部保护区保留原文，最近 live frontier 保留原文。
2. 压缩结果前插入显式 boundary marker，告知后续模型哪些内容是历史压缩。
3. 模型摘要失败时回退到结构化、本地构造的记录，而不是让运行直接丢失全部历史。
4. TODO snapshot 独立保留，避免任务状态只存在于自由文本摘要中。

RWKV-LH 已有 `GoalState`、Task/Attempt、MemoryEntry、CriterionEvidence、RecoveryState 和 `WorkingMemoryBuilder`，因此不应再引入第二套对话事实库。合适的落点是：

- Goal 和当前 Task/Action 前沿继续保留原文/结构化对象；
- 旧事件只生成确定性的 state capsule，内容带 source ref、owner、workspace digest 和截断标记；
- 如额外让 RWKV生成语义摘要，该摘要只能作为可追溯 memory observation，不能成为 Goal、Task 完成或最终答案的权威来源。

这直接对应 Round71 的 B02/H12：问题不是缺少更多历史，而是旧失败压过当前权威事实。需要清晰的“历史压缩区”和“末端 live frontier”，而不是更长的混合提示。

### 2. 本地代码预读应拆成 deterministic inventory 与 RWKV summary

可立即借鉴的不是“启动另一个模型替 RWKV 总结代码”，而是两个分层：

- deterministic inventory：相对路径、文件大小、语言、符号/import 索引、workspace digest、分页 cursor；它只帮助 RWKV 找到该读什么，不解释代码语义。
- RWKV file-local summary：每个文件由 RWKV 读取真实内容后产生原始摘要，保存 owner task、source path、source digest、读取范围和 raw output；聚合 Task 只能引用这些摘要，不能由控制器补内容。

这与“给大型代码项目，并行总结每个文件”的验收目标一致。当前已有并行 fanout/aggregate 的控制器测试，但真实 Round71 H13 表明固定 ready 上限仍会阻断批量前沿，因此先修读取/前沿结构比增加标题功能优先级更高。

### 3. 用户输入摘要与自动任务标题

`ai00-x-client` 当前固定提交中的 `generateTempTitle` 只是：去空白、压缩空格、最多 20 字符，并尽量在标点处截断；不是模型语义标题。这一做法适合作为 UI 临时标题，不影响 Agent 决策，也不值得进入核心协议。

用户输入摘要若用于核心执行，必须保留 immutable original request。允许增加一个非权威的“navigation summary”，但任何 Goal/criteria 仍必须从原始请求由 RWKV生成并可审计。Round71 LH11/M18 的草案已经保留请求，真正失败是 audit 截断，所以当前不应把新增用户摘要误当作修复。

### 4. 大量搜索结果的有用信息总结

当前阶段不增加 MCP/外部服务。未来搜索工具接入后，应采用与代码文件相同的 evidence map-reduce：

1. 每条搜索结果保留 URL、抓取时间、内容 digest、原始片段和截断元数据。
2. RWKV 对每个来源生成 file/source-local summary，raw output 不改写。
3. RWKV 聚合 Task 引用来源摘要与 source refs。
4. 控制器只验证引用存在、来源未过期、输出格式和作用域，不判断“哪条信息正确”或改写综合结论。

这能提高可读上下文质量，但不应在当前没有 search action 的 E2E-90 上抢占 Round71 公共缺陷的修复顺序。

## ai00-x-client 不直接借鉴的内容

- 不采用其远端模型 fallback；RWKV-LH 的能力测量保持 RWKV-only。
- 不复制其自由文本 compaction prompt 作为事实源。该 prompt 要求保留全部用户消息和大量代码片段，适合通用聊天续接，但会在 16K RWKV 上形成新的长上下文竞争。
- 不引入 Router subagent 或多 Agent handoff。其 router 是一次额外 LLM 分析，并不提供模型状态分类器；还会改变单 RWKV 测量口径。
- 自动标题仅属于前端展示，不能驱动 action/Task/验收。

## rwkv7-state-embedding 指标核实

### 真实任务定义

`0.9325` 来自 `Hidden + MLP` 对 `golden_balanced.jsonl` 的四分类，标签为任务难度 `R0–R3`（文件中字段为 `tier=0..3`），不是 coding/debugging/research/documentation 等根用户意图分类。

实验细节：

- 数据量 `16,751`；分层 `70/15/15` train/dev/test。
- 冻结 0.4B RWKV-7，通过 albatross 抽取 L12 hidden。
- MLP 为 `1024 -> 256 -> 4`，dev 用于 early stopping，held-out test accuracy `0.9325`。
- Top-8 WKV head + PCA + MLP 只有 `0.9208`，hidden baseline 更好。
- 上游明确指出任务专用 projector 不可混用；分类结果不能直接迁移为 STS/聚类，反之亦然。

因此该项目证明的是“RWKV hidden state 中存在可监督提取的分类信号”，不是“现成分类器能以 93% 准确率路由 RWKV-LH Agent”。

### 对 RWKV-LH 的合适落点

这是一个有价值但受后端和数据阻塞的 P2 实验：

1. 先定义本项目真实、互斥且会改变提示/工具披露的路由标签，例如 `workspace_coding`、`workspace_data_transform`、`workspace_inspection`、`external_research`；如果路由不改变任何执行边界，就不值得增加分类器。
2. 从 E2E-90 和真实匿名任务建立独立 train/dev/test，按任务模板/来源分组去重，防止同模板泄漏。
3. 只用用户原始输入的 RWKV hidden state；分类器不得读取隐藏验收答案、运行结果或最终输出。
4. 先做 shadow mode：记录建议路由但不影响执行，比较 macro-F1、每类 recall、校准和 OOD 拒绝率。
5. 只有 held-out 指标达到预注册阈值且对 Strict E2E 有独立增益，才允许分类结果选择“披露哪个固定 action catalog/prompt profile”。它不能选择答案、工具参数、证据或最终输出。

当前 OpenAI-compatible 转发端点只暴露文本 completion/model 元数据，没有已验证的 hidden/state 导出 capability。已有 `ModelStateRef` 也不能代替真实模型 state；在推理后端提供 capability negotiation 前不得伪造 embedding。

## 优先级结论

| 优先级 | 候选 | 当前决定 | 原因 |
| --- | --- | --- | --- |
| P0 | live frontier 置于提示末端、历史区显式分界 | 立即进入 Round72 | 直接修复 B02/H12 等真实失败，不改变 RWKV语义 |
| P0 | 批量代码 inventory + 读取 fanout 的结构容量 | 立即修复基础上限，后续真实验收 | 对应 H13 和大型项目逐文件总结目标 |
| P1 | deterministic state capsule/结构化 fallback | 延续现有 WorkingMemoryBuilder 改造 | 防上下文刷新丢状态，但不把摘要当证据 |
| P1 | RWKV file/source-local summary + RWKV aggregate | 在基础读取链稳定后实验 | 能支持代码/搜索大量输入，raw output 可保持不变 |
| P3 | UI 临时标题 | 延后 | 不影响当前 Strict 质量 |
| P2，后端阻塞 | hidden-state 意图/难度路由 | 先建本项目数据与 shadow protocol | 上游 93% 不是本项目意图分类，且端点无 state API |

结论：外部参考强化了“状态与信息边界优先”的方向，但不会替代 Round71 已经暴露的格式、证据、Goal audit、Task 可执行性和 frontier 容量修复。
