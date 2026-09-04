# RWKV Stateful Goal Loop v2 实施预注册

- 实验 ID：`RWKV_STATEFUL_GOAL_LOOP_V2_IMPLEMENTATION_20260831`
- 冻结日期：2026-08-31（Asia/Shanghai）
- 分支：`chase/hybrid-product-v1`
- Git HEAD：`683528577298258d12d7ed0e09c3ae57aa8bbf16`
- 实施性质：系统架构整改；不得以单用例特判替代根因修复。

## 冻结基线

- 当前完整单元回归：`737 passed, 1 warning in 184.29s`，命令为 `uv run pytest -s -q`。
- 最新固定 3 用例能力 canary：completed/external/strict 均为 `0/3`。
- 纯 RWKV 历史固定 90 用例基线：strict `36/90`（Round126）。
- 首个强模型混合架构固定 90 用例：strict `17/90`（Round134）。
- 强模型并行 atom 历史峰值：strict `41/90`，但使用 521 次 supervisor 调用（Round148）。
- 后续强模型 contract 架构：strict `19/90`（Round165）。

基线证据只用于对照，实施后不得修改评价口径或移除失败样本。

## 冻结源码摘要

| 文件 | SHA-256 |
|---|---|
| `rwkv_lh/controller.py` | `068463...` |
| `rwkv_lh/model.py` | `c86322...` |
| `rwkv_lh/model_session.py` | `5f27a6...` |
| `rwkv_lh/product_runtime.py` | `dd14bb...` |
| `rwkv_lh/parallel_atoms.py` | `8eea0b...` |
| `rwkv_lh/supervisor.py` | `881da7...` |
| `rwkv_lh/supervisor_openai.py` | `917224...` |
| `rwkv_lh/contract_graph.py` | `6fb22a...` |

上述前缀来自实施前工作树；最终记录必须补充完整摘要及 dirty diff 状态。

## 架构不变量

1. 一个顶层 Goal 仅有一条权威 13.3B 主 State；工具观察、计划增量、审核结论和最终答复都沿这条 State 因果推进。
2. 2.9B selector 仅输出候选工具 Top-K 与分数，不决定最终操作；13.3B 在候选 schema 中决定操作与参数。
3. 审核由同一个 13.3B profile 的临时 fork 完成。审核 fork 不合并 WKV；只把经过内核验证的审核结论作为有界事件追加回主 State。
4. 审核至少发生在：变更事务结束、工具失败、frontier 耗尽、停滞、最终答复前。Harness 的一个 mutation action 视为一个事务边界。
5. 最终答复必须通过 RWKV 审核及确定性证据检查；预算耗尽只 yield，不得伪造 Goal 终止。
6. 强模型不是执行依赖，不拥有动作、状态、完成判定或审核权限；旧 contract/atom 路径仅兼容保留。
7. 不再为每个并行 atom 创建独立权威 13.3B session；v2 中 mutation 串行，只有无副作用读取允许并行。
8. 计划采用滚动 `PlanPatch`，只允许追加/更新未完成步骤，不得重写已完成事实。

## 固定协议

- `PlanPatch`：版本、patch id、目标摘要、步骤、依赖、成功证据与原因。
- `AuditDecision`：`continue | repair | ready_for_final`、step id、证据引用、缺口、完成步骤。
- selector 默认 `K=3`；候选不足时使用全部合格候选。
- 相似度算法固定为 `utf8-byte-5gram-cosine.v1`。
- 与 Agent Ladder 隔离阈值固定为最大相似度 `< 0.95`。

## 实施范围

1. 新增结构化 PlanPatch/Audit 协议与校验。
2. 新增 13.3B 审核 lane、session fork 审核、审核结论回写主 State。
3. selector Top-K handoff，13.3B 完成最终工具选择及参数生成。
4. 新增 `stateful_goal` 控制器模式并设为产品/CLI/UI 默认；`contract_graph` 保持显式兼容。
5. 建立由真实失败轨迹生成、经修正执行验证的 state-tuning 数据规范和生成器；Ladder 数据保持 holdout。
6. 增加协议、状态推进、审核、Top-K、产品路由、失败数据构造测试。

## 固定验收门槛

- 全单元回归不得低于实施前 737 项，且所有已有测试通过。
- 固定 3 用例能力 canary：completed/external/strict 必须达到 `3/3` 才可进入完整 Ladder 验证。
- 13.3B state-tuning 离线门槛：operation exact `>=0.96`，arguments exact `>=0.95`，audit false-ready `=0`，gap recall `>=0.95`。
- 2.9B selector 门槛：top-1 accuracy `>=0.96`，macro-F1 `>=0.96`，minimum class recall `>=0.90`，top-3 recall `>=0.995`。
- 全量数据、同类错误、边界、异常和历史回归均须执行；未达门槛时报告为未解决，不修改阈值。

## State-tuning 冻结配额

13.3B 目标为 train/eval `2000/480`：

- PlanPatch：`240/60`
- operation + arguments：`900/220`
- observation → repair：`360/90`
- audit：`360/90`
- continue/final：`140/20`

2.9B selector 目标为 train/eval `6000/750`：25 个标签，每标签 `240/30`，保存完整 25 类 logits/listwise 目标。

## 数据标签规则

失败样本必须保留原始输入、原始输出和错误结果；定位最早因果偏离点后，在干净快照执行修正轨迹。只有 Harness、测试或可见确定性 verifier 通过，修正输出才能成为正标签。强模型可以提出候选修正，但不得成为标签真值。Agent Ladder 的精确请求、路径和隐藏 verifier 不得进入训练集，只允许使用抽象错误分类生成不同项目族的同类场景。
