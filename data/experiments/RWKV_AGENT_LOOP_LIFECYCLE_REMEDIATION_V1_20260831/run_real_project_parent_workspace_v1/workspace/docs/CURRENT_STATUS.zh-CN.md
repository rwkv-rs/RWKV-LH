# RWKV-LH 当前状态

更新时间：2026-08-31（Asia/Shanghai）

本文是当前产品与实验状态入口。历史 Round、旧 Full90 与旧 profile 文档只代表登记时状态，不能替代本文。

## 目标

1. 当前目标：补齐本地真实 Harness 的联网能力和检索质量，同时保留 RWKV 原始输出、权限、证据、恢复链与 state 身份审计。
2. 中期目标：strong model 只做 Planner/Reviewer；RWKV 2.9B 只选工具；RWKV 13.3B 负责参数、执行推进和总结，形成能完成真实中型项目、细致 bug 修复和联网任务的 Harness。
3. 后续目标：用失败簇驱动的独立 state tuning 增强旧 Agent 能力，并用新的 Agent Capability Ladder 衡量真实闭环能力，而不是继续把旧 Full90 当总能力分。
4. 最终 RWKV 核心 Agent、扩大有效上下文与更大训练由用户后续推进，不由辅助模型或 Harness 逻辑替代。

## 当前固定架构

```text
strong Planner/Reviewer
        │ 只生成/审查 contract graph，不执行工具
        ▼
2.9B RWKV Selector + Hidden(mean+last)+h64 MLP
        │ 只看 25 个名称/描述与当前紧凑状态，提交一个 operation
        ▼
13.3B RWKV Executor
        │ 只看已提交 operation 的一个完整 schema、当前状态与末端目标
        ▼
Harness 机械校验/执行 → 精确 observation → append-only audit
```

- Selector 与 Executor 是不同模型、不同 lane、不同 checkpoint、不同 persistent initial-state profile。
- Selector 固定 25 类：23 个可执行 operation、`final_answer`、`ABSTAIN`；不看参数 schema 或 Executor 文本。
- Executor 不接收完整工具菜单，只完成已提交工具的参数与执行目标。
- G3 为 offline/general Executor state，G6 为 network Executor state；一次 task 只绑定一个 profile，run 内不切换。
- 历史 0.4B State Router Shadow 已退出产品运行栈和前端，不参与路由、输入或评价；历史源码/
  实验记录仅保留审计。当前选择职责完全归 2.9B S60。
- 所有模型输入把当前问题/执行目标放在续写点末端；相关不变量已有回归测试。
- Parser、Controller、Harness 不诱导、不修复、不截断、不删除、不替换、不重排或隐藏 RWKV 原始输出。raw text、token、finish reason、model/profile 与 digest 先追加保存，解析和评分只是派生视图。

## 当前编号与身份

| 编号 | 模型/职责 | 状态 | 关键身份 |
|---|---|---|---|
| `PLN-C1-GPT54MINI-NONE` | strong Planner/Reviewer | 已验证配置 | `gpt-5.4-mini`，reasoning `none`，strict JSON，无 fallback |
| `SEL-Z0-S60` | 2.9B Selector | 当前基线 | zero state；S60 v7 requirement-byte-tail；head SHA `721669ce…0d441` |
| `SEL-S31-R` | 2.9B Selector tuned | 已拒绝 | 2K state 只净改善 1/500，未达到因果门 |
| `SEL-S71-ST500/1000/1500/2000-R` | 2.9B Selector tuned | 已拒绝 | 最佳 dev `0.920 / 0.918819 / 0.50`，locked 未读，未接入产品 |
| `EXE-G3-MULTISTAGE-STEP2000` | 13.3B offline/general | 当前实验绑定 | state SHA `13f65869…54f12` |
| `EXE-G6-NETWORK-RECOVERY-STEP1500` | 13.3B network | 当前实验绑定 | state SHA `611d9e55…dd68b` |
| `EXE-L0-S8R3` | 13.3B 旧混合角色 | 产品连续性对照 | 旧 selector/executor 混合 state，不作为新训练父结论 |

13.3B 基础模型 SHA-256 为 `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。按工具拆 state 只保留编号空间；先做固定联动消融，只有可复现残差且无跨功能回归时才增加 profile。

## 已验收组件

### 2.9B 静态分类

- S60 locked test 所有预注册数据面门通过；S28 accuracy `99.733%`，S39 accuracy `96.266%`，其余 S52/S53/S55 门均达标。
- 该结果证明静态分类超过 96%，但不代表真实多步轨迹同样超过 96%。最新 canary 已证明未完成写根后的 `final_answer` 边界仍是主要缺口。

### 本地联网与检索

- 发现顺序：直接 URL → Tavily Search API → Bing RSS → DuckDuckGo HTML；Bing 保留为 fallback。
- Retrieval Quality R2：9/9 hard gates；top-1 relevance `1.0`，relevant source recall `1.0`，expected-host precision `1.0`，重复记录率 `0`；p50 `1.993s`，p95 `6.587s`。
- 17 个已验证 Tavily 凭据参与池化，凭据不进入结果、snapshot 或文档。
- 网络 evidence 先落盘并保留 URL、provider、span 与摘要，再投影给 RWKV；不把搜索摘要伪装为模型原始输出。

### vllm-rwkv 与 state

- 本地可修改的 vllm-rwkv 按相同配置运行，R7 数值/输出门已通过。
- G3/G6 可在同一 13.3B 服务中按 task 绑定不同 state；绑定由请求身份和 SHA 验证，run 内 switch 为 0。
- 产品 18070 保持旧服务连续性；当前最佳实验预览使用 18075，经本地 29613 访问。两者均在
  远端物理 GPU0，互不替换；本地 2.9B Selector 使用本机物理 GPU0。

## 2026-08-30 Harness bug 整改

冻结 10 题 Agent Ladder 基线为 strict `0/10`：7 题在任何 RWKV 请求前因 Planner HTTP 500 失败；3 题进入 RWKV 后出现零 mutation 或多写根不完整却被提交的问题。

本轮已完成：

- capability projection v3；写根决定最低动作预算。
- mutator 必须有成功 path mutation 且覆盖每个声明写根，否则 fail-closed。
- Planner 预算必须覆盖写根数。
- Planner 路由恢复为 `gpt-5.4-mini + reasoning=none`；修复 `none` 重试被提升为 `low`。
- 三题真实 GPU0 canary 结构门通过：Planner failure 0/3；40/40 v3 atom；预算不可行 0；10 次 transaction fail-closed；69 次 raw generation 哈希/字节一致；state switch 0；产品 18070 健康。
- 严格能力仍为 0/3，原样保留。剩余失败是 Selector 过早 Final/误选只读操作，以及 Executor 未完成多写根，不再是 Harness 假完成。
- 全项目：`uv run pytest -s -q` → `635 passed, 1 warning`。

详细结果见 [`REMEDIATION_RESULT.md`](../data/experiments/AGENT_HARNESS_TRANSACTION_REMEDIATION_V1_20260830/REMEDIATION_RESULT.md)。

## 2026-08-30 Harness 因果闭环 P1/P2 复审整改

独立只读审查又发现 4 个 P1 和 3 个 P2。它们不推翻 E1 两个离线 scheduler canary 的窄结论，因为那两例
没有进入 finalizer、最终呈现、联网、exclusive command、崩溃恢复或 State Router；但它们会阻止把系统
称为“完整闭环”或直接运行完整联网消融。因此完整 E1 已暂停，先完成本轮系统性整改。

现已完成并通过失败注入：

- frozen/replacement finalizer 的依赖机械覆盖全部已完成 work node；联网证据可从 child outcome 有界交接；
  correction work 会失效旧 finalizer。
- `EXECUTION_EVIDENCE` 通过后仍不能直接完成；exact RWKV Final 必须再通过独立
  `FINAL_PRESENTATION` review，Reviewer/Controller 均不改写原文。
- workspace 来源扫描的预算耗尽、跳过目录、遍历或读取失败统一产生 `unknown`，`auto_public` fail-closed。
- 所有 exclusive atom 都在隔离快照执行；只有成功时全快照事务提交，失败命令的写入不污染父 workspace。
- supervisor pending 有显式 resolved 生命周期，并覆盖响应提交/resolve 之间进程丢失；主动任务只看当前
  unresolved 集合。
- child action 半提交按 attempt ID 幂等恢复；State Router Shadow 使用统一 child/direct activity 投影。

固定矩阵 7/7 全过；相关回归 `177 passed`；全项目 `684 passed, 1 warning`；`git diff --check` 通过；
产品 `127.0.0.1:29610` 返回鉴权型 HTTP 401，说明隧道/服务可达且未被替换。本轮没有启动模型、占用 GPU、
训练 state 或改变任何 RWKV raw output。完整记录见
[`RESULT.md`](../data/experiments/HARNESS_CAUSAL_CLOSURE_P1P2_V1_20260830/RESULT.md)。

## 2026-08-31 快速收口与 S71 state 消融

- 复核确认 4 个 P1、3 个 P2 的系统性修复仍在当前代码中；相关闭环回归为 `180 passed`。
- 当前完整单元测试为 `706 passed, 1 warning`，`git diff --check` 通过；唯一 warning 仍为 Python 3.13
  多线程进程内 `fork()` 的既有弃用提示。
- S71 固定 2K train、500 visible dev、500 全新 locked test；zero state dev 为
  `0.922 / 0.920506 / 0.50`。
- 2.9B state tuning 完成 2000 步并固定比较 ST500/1000/1500/2000。最佳 ST500 仅为
  `0.920 / 0.918819 / 0.50`，其余更低；四候选全部拒绝，locked test 保持未读取。
- 结果排除“同一目标只需更多训练步数”这一解释：四个 head 对 train 均为 `1.0 / 1.0 / 1.0`，
  dev 错误稳定集中在工具效果边界。S71 不得上线，正式 Selector 继续使用 S60。
- state/hidden/raw logits/trainer log 均完整保留；没有修改或替换 RWKV 输出。仅使用 GPU0，训练与消融
  进程已退出；随后 18075 重新部署为最佳 G3/G6 预览服务，远端产品 18070 仍健康，GPU1/2 未触碰。

完整记录见
[`RESULT.md`](../data/experiments/NETWORK_SELECTOR_DIVERSE_BOUNDARY_S71_V1_20260831/RESULT.md)。

## 2026-08-31 当前最佳真实 Agent canary

在任一模型请求前固定三题：L1 通用 bug 修复、L4 个人记账中型网页、L5 真实联网资料项目；
固定 `gpt-5.4-mini + S60 zero + G3/G6`、Contract Graph、progressive disclosure、并发 1、
max transitions 300，关闭 Planner cache，0.4B Shadow 不启动。

- 结果：completed `0/3`、external `0/3`、strict `0/3`，未达到预注册 3/3 发布门。
- Planner 请求 21 次，transport failure 0；13.3B generation 242 次；Action 73；
  protocol rejection 144。
- 242/242 RWKV raw generation 的 byte/SHA 一致且 `postprocessed=false`；
  227/227 Selector handoff 都是 eligible raw-logit argmax，无后处理替换。
- L1 把 read 目标误选为 `date_diff/calculator`，并用 `write_json` 把 Python 写成 JSON；
  L4 多轮重复 `write_json`，没有覆盖四个项目写根；失败 snapshot 均未合并。
- L5 的 7/7 次 `web_search` 成功，Reviewer 收到真实 BlinkDL evidence；但 mutation 未覆盖
  六个写根，父工作区只保留 verifier。证明“联网内核可用”不等于“联网项目闭环”。
- G3/G6 三题 state switch 均为 0；旧 18070 和最佳 18075 在运行后均健康，未启动训练进程。

完整记录见
[`RESULT.md`](../data/experiments/FAST_AGENT_CAPABILITY_CANARY_V1_20260831/RESULT.md)。

当前最佳实验预览已完整部署在 `http://127.0.0.1:8766`（RWKV Goal Studio）：2.9B Selector、Web、worker 均由
stack 精确拥有，13.3B `29613` 和旧产品 `29610` 健康；前端已移除 Shadow，并默认测试
`contract_graph + auto_public`。能力卡固定展示本节 0/3 结果。

真实 Web POST 首次发现 Supervisor `.env` 把旧 `RWKV_TOOL_DISCLOSURE_MODE=full` 污染到
产品进程；现已把 Supervisor loader 隔离为 `SUPERVISOR_*` 命名空间，并在产品配置显式固定
`progressive`。修复后 `UI-20260830-233140-0dadf4` 完成 `calculator → final_answer`：2/2
Selector 为原始 eligible argmax、2/2 Executor raw byte/SHA 一致、Harness action 成功、最终
`4` 未被 Controller 改写。它只验证部署闭环，不覆盖 0/3 canary。证据见
[`DEPLOYMENT_SMOKE.md`](../data/experiments/FAST_AGENT_CAPABILITY_CANARY_V1_20260831/DEPLOYMENT_SMOKE.md)。

## 当前产品判断

- 联网检索内核可作为第一版组件投入使用：来源相关性、去重、延迟、证据和凭据隔离均通过冻结门。
- 整体 Agent 还不能称为第一正式版本：新的真实 Ladder 当前没有严格通过，尤其是多文件/多写根事务。
- 当前系统能实际运行项目生成、bug 修复、命令与网络工作流，也能拒绝不完整结果；但当前三题
  canary 为 0/3，不能把“进入过这些流程”写成“已经可靠完成这些能力”。

## 下一执行顺序

1. 当前最佳实验预览保持 `gpt-5.4-mini + S60 zero + G3/G6`，供前端手工测试；任何手工成功
   都不能覆盖 0/3 canary。
2. 从 242-generation 真实残差提取通用错误簇，不把 Ladder 请求/路径/verifier 放入训练：
   read 与 calculator/date、write_file 与 write_json、missing-file create/read、多写根持续推进、
   final 边界。
3. 使用不同实体、路径和措辞构建约 2K Selector/Executor 数据，冻结 byte 5-gram 0.95 去重门。
4. 固定比较 Selector zero/tuned × Executor G3/G6 或新 transaction state；先证明联动因果，再只
   保留提升真实轨迹且不损害联网/工程留存集的最少 state。
5. 只有代表性 canary 通过后才运行固定 10 题完整 Ladder，并据此决定第一正式版本。

执行交接见 [CURRENT_HANDOFF.zh-CN.md](CURRENT_HANDOFF.zh-CN.md)。
