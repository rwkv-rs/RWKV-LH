# AtomExecutionContract 全链路闭环消融 V1 预注册

日期：2026-08-30（Asia/Shanghai）

## 目的

验证真实 Harness 中 Planner、Selector、Executor、Controller、Harness、事务提交与结果回写共享一个不可变 `AtomExecutionContract` 和一个 Harness 观测 `ContractProgress` 后，是否能减少过早 `final_answer`、无效只读循环和未覆盖写根，同时不损害既有联网、工程能力及 RWKV 原始输出完整性。

本实验只衡量工程闭环是否让 RWKV 的现有能力被正确发挥，不用确定性逻辑替代 S66 的 operation 选择，不替 13.3B 生成参数或补动作。

## 固定数据

- 来源：`benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1/`。
- 版本：Agent Capability Ladder V1，固定 10 题、5 层、固定顺序。
- 用途：真实 Planner→Selector→Executor→Harness 端到端 holdout；不得用于训练。
- 生成方式：`scripts/generate_agent_capability_ladder_v1.py`；reference、acceptance 和泄漏检查沿用已冻结版本。
- 数据摘要、生成器摘要、acceptance 摘要和 manifest 摘要登记在 `EXECUTION_FREEZE.json`；运行后不得替换题目、验证器或评价口径。
- 相似度算法：`byte-5gram-cosine-v1`；若后续构建 state-tuning 数据，与本 holdout 任一请求的最大相似度必须 `< 0.95`。本次 A/B 不训练，也不读取 holdout 标签修改策略。

## 固定模型与运行身份

- Planner/Reviewer：`gpt-5.4-mini`，reasoning `none`，strict JSON，无 fallback；plan/review tokens `4000/2400`。
- Selector：2.9B S66-M1，Hidden(mean+last)+Soft-MoE h64，zero state；head SHA-256 `858982e45822b975c3c4cf0badf4a89c12b2c85a76e7157da85809a246b7c304`。
- Executor：13.3B task-level G3/G6；G3 SHA-256 `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`；G6 SHA-256 `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- 物理 GPU：只用 GPU0，UUID `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`；产品 18070 不停止、不替换。
- 实验 Executor `18075` → 本地 `29613`；Selector 本地 `29621`；并发 3；max transitions 300；progressive disclosure。
- 一个 run 内 Selector/Executor profile switch 必须为 0。

## 两个固定实验臂

| 臂 | 生产契约/安全门 | Selector stage view | Selector final eligibility |
|---|---|---|---|
| A `legacy_selector_view` | canonical contract、digest、Controller/Harness/transaction 全部启用 | `CurrentDirectStageV1`，只含最近动作结构事实 | 仅 `action_count >= contract.minimum_actions` |
| B `contract_progress` | 与 A 完全相同 | `CurrentDirectStageV2`，含同一 contract digest、预算、写根类型/覆盖、剩余义务 | `ContractProgress.completion_ready` |

A 仅由 `temp/atom_closed_loop_arm_a_sitecustomize/sitecustomize.py` 在实验子进程内 monkeypatch Selector 投影和 eligibility；不修改生产源文件，不修改 Controller/Harness 安全门，不修改任何 RWKV raw output。B 直接运行生产实现。

## 固定指标

主要真实能力指标：

1. strict pass / 10；
2. external verifier pass / 10；
3. agent completed / 10；
4. 连续能力层级。

固定过程指标：

- Planner terminal failure 数；
- Selector 调用数、`final_answer` 选择数、ABSTAIN 数；
- `final_answer` 因 contract 未完成而被拒绝的次数；
- mutate atom 数、至少一次成功 path mutation 的 mutate atom 数、全部写根覆盖的 mutate atom 数；
- transaction integrity error 数及 `no successful mutation` / `uncovered roots` 分类；
- InputBudget / protocol rejection / identical failure 分类；
- raw generation 数、原始字符串/UTF-8 bytes/SHA-256 完整性；
- exact selection handoff、contract digest、profile identity 与 run 内 switch 数；
- 产品 18070 运行前后健康。

## 预注册判定

- 基础有效性门：两个臂均 10/10 产生审计；Planner 配置、模型/state/head SHA、GPU UUID、题目顺序完全一致；contract drift 为 0；raw 完整性 100%；profile switch 0；产品 18070 前后健康。
- B 被视为闭环有效，必须同时满足：
  1. strict、external、completed 三项均不低于 A；
  2. 全写根覆盖 mutate atom 比例高于 A，或 transaction integrity error 至少相对下降 20%；
  3. B 的未完成 `final_answer` 尝试更少且 contract-advancing 成功动作不少于 A，或拒绝后出现后续 advancing 成功动作的比例高于 A；
  4. 不新增 Planner terminal failure、contract drift、raw 完整性失败或 profile switch。
- 若 B 仅增加拒绝而没有更多 advancing action，则结论是“工程安全闭合，但 S66/Executor 仍需 state tuning”，不得把 fail-closed 计为能力提升。
- 是否训练约 2K state 只由上述固定结果决定；不得在本 A/B 结果出来后修改指标或阈值。

## 完成条件

- `uv run pytest -q -s` 全量通过；边界、漂移、恢复与同源 exclusive commit 回归通过。
- A/B 全量运行、固定分析脚本、原始审计、结果 hashes 和最终报告均写入本目录。
- A/B 结束后释放实验 Executor/Selector，仅保留产品 18070；不得删除或重写任何模型原始输出。
