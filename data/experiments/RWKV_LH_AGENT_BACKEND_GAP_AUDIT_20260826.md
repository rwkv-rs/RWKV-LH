# RWKV-LH Agent 后端差距审计 — 2026-08-26

## 结论

当前项目已经是一个有真实后端骨架的实验型 Agent，不是简单聊天封装：文件操作、原生文本
搜索、命令执行、联网策略、持久任务、Contract Graph、并行 RWKV atoms、SQLite/CausalEvent
恢复链都存在。它最强的部分是状态权威、审计和恢复。

但按 DeepSeek Harness Standard/Code、Codex 和 Claude Code 已公开的后端能力并集衡量，当前
Harness 功能覆盖估计为 **57/100**；按“可以放心交给真实用户自主完成仓库任务”的端到端标准，
当前约为 **40–50/100**。这不是跨产品 benchmark 分数，而是下面固定权重能力表的工程估算。
更硬的项目内证据是：已发布 full90 最佳 Strict 仍为 `31/90`，而本次新搜索 canary 虽能找全
所有 locator，仍把 `HIGH` 排在 `SECURITY CRITICAL` 前。

因此，距离成熟可用 Agent 的主要差距已经不是前端，而是：

1. RWKV 与工具协议的稳定兼容及真实任务正确率；
2. 命令、网络和副作用的机械安全边界；
3. 持久终端、流式/取消/后台任务等执行控制；
4. MCP、Skills、插件、Hooks、LSP 与 Git/worktree 生态；
5. 最后才是动态子代理和多模型编排。

## 本次新增能力的真实验证

`search_text` 已成为原生只读 Action，不依赖外部 `rg`/`grep`，具有 UTF-8/二进制/软链接/
超大文件边界、固定排除目录、正则与 literal、稳定 path/line/column、token/result 双重分页和
query-bound cursor。冻结数据集和结构测试通过，全量回归为 `287 passed`。

真实 G1i 13.3B canary 揭示了后端成功与 Agent 成功的区别：

| 运行 | disclosure | 状态 | 搜索动作 | 模型请求 | 协议拒绝 | locator F1 | 首项优先级 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| v1，literal 默认 | progressive | 人工终止 | 67 | 141 | 6 | 0.0 | 0.0 |
| v2，regex 默认 | progressive | interrupted | 2 | 17 | 12 | 1.0 | 0.0 |
| v2 消融 | full | completed | 1 | 3 | 1 | 1.0 | 0.0 |

解释：

- v1 中 RWKV 明确发出 `pattern="TODO|FIXME", mode="literal"`，得到完整零匹配后重复了 67 次。
- 改为 grep 风格 regex 默认后，第一次搜索就精确返回 3 个匹配。
- progressive 模式下，模型在观察结果后直接发 `final_answer`，而 selector 阶段只接受
  `select_tool`，连续 12 次拒绝后进入 interrupted terminal path。
- full disclosure 仅用 1 次搜索、3 次模型请求、约 10 秒完成，证明搜索执行链成立；但语义排序
  仍错，把 `FIXME HIGH` 放在 `TODO SECURITY CRITICAL` 前。
- 已增加只读幂等零进展观测的三次熔断，避免再次跑到 67 次；这减少损耗，不代表修复语义。

对应预注册与结果：

- [初始 canary 协议](NATIVE_SEARCH_TEXT_RWKV_CANARY_PROTOCOL_20260826.md)
- [v1 失败结果](NATIVE_SEARCH_TEXT_RWKV_CANARY_V1_RESULT_20260826.json)
- [regex 默认协议](SEARCH_TEXT_REGEX_DEFAULT_V2_PROTOCOL_20260826.md)
- [v2 progressive 结果](NATIVE_SEARCH_TEXT_RWKV_CANARY_V2_RESULT_20260826.json)
- [disclosure 消融协议](SEARCH_TEXT_TOOL_DISCLOSURE_ABLATION_PROTOCOL_20260826.md)
- [相同成功观测熔断协议](IDENTICAL_SUCCESS_LOOP_GUARD_V1_PROTOCOL_20260826.md)

## 与 Cordis / 成熟 Agent 的功能差距

DeepSeek Harness 的官方定位是所有能力均可由 Cordis plugin 组合，覆盖 model、tool、skill、
session、sandbox、storage、loop、schedule 和 UI；Standard 模式包含文件/网页搜索、编辑、shell、
skills、planning、goals、subagents 和 workflows，Code 模式还能用模型生成的 TypeScript 编排多轮
工具调用。官方同时明确它仍是 developer preview，存在破坏性变更，所以它是功能上限参考，
不是生产稳定性金标准。来源：[DeepSeek Harness](https://www.deepseek.com/harness/en/)、
[官方仓库](https://github.com/deepseek-ai/deepseek-harness)。

其工具目录还明确提供 persistent bash/terminal、background jobs、LSP、session query、goal、
schedule、skills、workflow 和多种 subagent provider；子代理可来自 in-process、fork、ACP、Codex、
Claude Code 或 DSH SDK。来源：[官方 tool catalog](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/tool-catalog.md)、
[subagent subsystem](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/subagent)。

Codex 的公开后端也包含并行 subagents、MCP、插件、skills、hooks、Git worktrees、CLI/IDE/cloud、
以及 sandbox/approval profiles。其 sandbox 对派生命令同样生效，并把文件、命令、网络和越界访问
放在可配置 approval policy 下。来源：[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)、
[MCP](https://learn.chatgpt.com/docs/extend/mcp)、[worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)、
[sandbox](https://learn.chatgpt.com/docs/sandboxing)、[approvals](https://learn.chatgpt.com/docs/agent-approvals-security)。

Claude Code 进一步提供生命周期 hooks、MCP、插件、隔离 subagents、项目/用户持久 memory 和
worktree isolation，可作为另一个已经实际使用的产品基线。来源：
[hooks](https://code.claude.com/docs/en/hooks)、[plugins](https://code.claude.com/docs/en/plugins)、
[subagents](https://code.claude.com/docs/en/sub-agents)。

## 固定权重能力评分

评分只比较后端能力，不把 UI 美观、公司规模或模型品牌计入。每项得分上限等于权重，总分 100。

| 能力维度 | 权重 | RWKV-LH | 证据与主要缺口 |
| --- | ---: | ---: | --- |
| 工作区搜索/读写/命令 | 15 | 12 | 文件/JSON/搜索/命令较完整；缺 persistent PTY、LSP、结构化 patch/diff、Git 原语 |
| 持久状态/恢复 | 13 | 12 | CausalEvent、CAS、checkpoint、lease、非幂等未知副作用处理很强；native RWKV state 仍依赖服务端 |
| 计划/工作流/自动化 | 10 | 7 | Contract Graph、parallel atoms、proactive queue 已有；缺通用 goal/workflow runtime 与交互式计划 |
| 插件/Skills/MCP 扩展 | 12 | 3 | 构造时可注册 Python Action；无包发现、依赖生命周期、Skills、MCP、热挂载或市场 |
| 多 Agent 编排 | 8 | 3 | 有受 Contract Graph 限制的线程 atoms；无模型动态 spawn、消息、取消、异构 provider 和独立 session |
| Sandbox/审批/安全 | 12 | 5 | 有 workspace scope、bubblewrap、联网 Gate、proactive approval；仍有关键执行漏洞，见下节 |
| 代码智能/上下文/记忆 | 8 | 3 | 有文本搜索、chunk、RWKV state 接口；无 AST/LSP/语义索引/repo map/跨会话项目记忆 |
| 执行 UX 控制 | 7 | 2 | 有 CLI/Web/worker；无 token streaming、请求取消、stdin、PTY、后台进程统一控制 |
| 审计/可观测/Eval | 8 | 8 | append-only 事件、可重建投影、冻结数据、预注册实验与隐藏验收是当前优势 |
| 外部集成/浏览器/多模态 | 7 | 2 | 有 ECRA web/connector 抽象；无 MCP 生态、浏览器/电脑操作、图片输入与 IDE 集成 |
| **总计** | **100** | **57** | 实验 Harness 已成形，距离成熟通用 coding-agent backend 仍约 43 分 |

## 当前最危险的生产差距

### P0 — 命令安全不是机械闭合

`check_command` 被声明为只读，但实现直接调用 `_run_command`，没有可执行文件/子命令只读策略；
任意可变更 workspace 的 argv 都可以通过这个“只读”能力发出。bubblewrap 同时显式使用
`--share-net`，所以普通命令沙箱默认继承网络。当前 retrieval Gate 只约束注册的网络 Action，
不能机械覆盖任意子进程的出站访问。

必须先做：

- `check_command` 独立执行策略或严格 allow/prompt/deny command policy；
- 命令 sandbox 默认断网，仅对有明确 provenance/approval 的调用开网；
- destructive、越界、网络、凭证、外部副作用的逐调用审批；
- 将审批决定、规则命中和网络尝试继续写入同一 CausalEvent 链。

### P0 — 工具协议和模型行为仍不稳定

本次 progressive/full 单变量消融从 `17 requests + interrupted` 变为 `3 requests + completed`，
差异不是搜索逻辑，而是 selector 与 RWKV 的 direct-final 行为冲突。不能只凭一个 canary 就把
生产默认切到 full；应在冻结 Basic30/full90 上比较 Strict、FP、FN、token、延迟和恢复，再决定：

- 默认使用 full disclosure；或
- progressive selector 在模型显式给出合法 direct `final_answer` 时走透明终止路径；或
- 针对当前 G1i checkpoint 训练/校准 selector 协议。

### P0 — 任务正确率仍未过门

项目自身 README 的完整证据为 Strict `31/90`、Agent completed `55/90`、FP `24`、FN `1`；
较新 Basic30 结果没有进入 confirmatory/full90。本次 locator 全对但排序错，说明工具可用不会自动
带来用户目标正确。必须把“检索事实完整性”和“RWKV 语义排序/决策正确性”分开建集与计分。

## 建议路线

1. **P0：安全闭合。** 修复 `check_command`、默认命令断网、逐调用审批与命令策略，并跑全部
   命令/联网/恢复同类路径。
2. **P0：协议全量消融。** 用冻结 Basic30/full90 比较 progressive 与 full，不根据单题改默认。
3. **P0：真实任务可靠性。** 为搜索/排序/无匹配/多页/中文/错误 regex 增加真实 RWKV E2E，
   同时报 locator F1、优先级、Strict、FP、FN、token 和延迟。
4. **P1：执行基座。** 增加 persistent PTY、stream/read/send/signal/cancel、后台 jobs 和输出 spill。
5. **P1：代码智能与安全编辑。** 增加 LSP/符号查询、apply-patch/diff、Git 状态/工作树隔离和回滚。
6. **P1：可组合扩展。** 先在 CausalEvent 权威链上做稳定 plugin/skill/MCP lifecycle，不需要一开始
   复制 Cordis 的全部热卸载能力。
7. **P2：动态子代理。** 只有单会话 full90 过门后再预注册验证；项目历史已经证明 selector、
   reviewer 和多角色状态会让当前 RWKV 退化，不能因为竞品有就直接加入。
8. **P2：浏览器、多模态、IDE/cloud。** 这些能扩大任务面，但不能修复当前正确率和安全边界。

## 不应误读的地方

- `57/100` 是透明能力权重，不是 SWE-bench，也不是与 DeepSeek/Codex 的同题胜率。
- DeepSeek Harness 自身仍是 developer preview；“功能更多”不等于“更稳定”。
- RWKV-LH 在 append-only 因果状态、崩溃恢复、严格预注册和事实/完成分离方面并不弱，某些结构
  甚至比常见轻量 Agent 更严谨。
- 当前不需要完整前端；先补上述后端 P0/P1，前端才能真实呈现而不是掩盖 Agent 缺陷。
