# Agent Harness 交易语义整改 V1 预注册

登记时间：2026-08-30（Asia/Shanghai）。登记发生在本轮核心代码修改、整改后测试和候选模型调用之前。

## 固定输入与事实边界

- 冻结真实能力基线：`LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_current_s60_g3_g6_baseline_v1_r2`。
- 基线结果 SHA-256：`8407949cb8a8b000b69b6edc5e65b171468f88bca009eda4218666c13bfaff51`。
- 固定 10 例、hidden verifier、外部检查、相似度算法、通过阈值和分母均不得修改。
- 基线包含 10 份审计、25 个直接 atom state；只读恢复结果为 `raw_rwkv_outputs_modified=false`。
- 7 例在任何 RWKV 请求前因 Planner 上游 HTTP 500 中断；仅作为控制面可用性失败，不归因于 Selector、Executor 或 state。
- 3 例进入 RWKV 后均未完成。已观测到的通用机械缺陷是：动作预算大于 1 的 capability atom 仍被标成单操作；带写入根的 capability atom可以在没有覆盖写入根的成功 mutation 时被提交；两个写入根仍投影为 `minimum_actions=1`。

## 根因整改范围

1. capability projection 升为新版本；历史 v1/v2 仍可读取。mutate atom 的机械最小动作数固定为 `max(1, len(write_roots))`，Planner 给出的 `action_budget` 低于该值时在模型执行前失败关闭并进入现有语义修复路径。
2. atom 输入中的 transaction mode 只由真实 action budget 决定：预算 1 为 single-action，预算大于 1 为 bounded multi-operation；必须保持一个 RWKV state，直到 completion checks 满足或预算耗尽。
3. 任何声明 `write_roots` 且菜单含 path mutation 的 atom，只有在每个声明根都被至少一个成功 path-mutation 参数覆盖后才允许提交 isolated workspace。未覆盖时返回显式 `transaction_integrity` 错误；不得提交、补写或改写模型输出。
4. capability atom 的 mutation 由后继 verify node负责独立验证；legacy multi-operation transaction 继续额外要求最终 mutation 之后存在公开 read/digest/check observation。
5. Planner 提示只增加机械可行性规则：每个非重叠写入根必须被预算覆盖；多个明确目标应拆成小节点。Planner仍不能选择 operation、参数、内容或执行工具。

## 明确不做

- 不对 10 个 holdout 用例、路径、字面量或 operation 写特判。
- 不屏蔽、重映射、修复、截断、删除、重排或替换 Selector argmax 与 Executor 原始输出。
- 不让 Planner/Reviewer获得 Harness authority。
- 不在本轮 Harness 修复中调整 G3/G6/Selector state；state 效果必须在修复后独立消融。
- 不把 Planner transport failure 从分母移除。

## 固定验收

1. 单元测试必须覆盖：预算 2–4 不再出现 single-operation；v2 历史可恢复；v3 两写入根投影最小动作 2；预算 1 的两根 v3 atom 失败关闭。
2. 完成但零成功 mutation 的 projected atom 必须被拒绝；只覆盖部分 write roots 也必须被拒绝；move_file 一次成功覆盖 source/destination 两根时可通过覆盖检查。
3. legacy transaction 的 post-mutation observation 回归保持通过。
4. `tests/test_parallel_atoms.py`、`tests/test_capability_projection.py`、`tests/test_contract_graph.py`、`tests/test_current_rwkv_input_layout.py` 及全部相关 Controller/Selector 回归通过。
5. `git diff --check` 与 compileall 通过。
6. 修复后必须先跑无模型脚本化 canary，再跑固定 10 例候选；评价口径仍为原预注册口径。
7. 基线与候选都必须报告 Planner transport、Selector route、Executor protocol、transaction integrity、external verifier 五类结果，不能合并成单一模型分数。

## 当前源码冻结 SHA-256

- `rwkv_lh/parallel_atoms.py`: `417723b53833d75bd889b67661426ec49923f21201c302cada7ba2264b71762e`
- `rwkv_lh/capability_projection.py`: `371c6bd95df7d2444dab9ecaede5acaf7a1bcea48a43f9c4612259640e6a85b0`
- `rwkv_lh/supervisor_openai.py`: `ef0b39e8a3b9f9e818b0bb4c67a2d711b446bae61c5c875d65b0350093a6fc1d`
- `rwkv_lh/controller.py`: `329b417f2e8f82b0cd7d6d4a632874217da281b6718b7c564c2ca6bcb3bb3380`
- `tests/test_parallel_atoms.py`: `6690ba871bbd31224b1be2169ef3c680a76edcd4c98762b8c76244ae799c4156`
- `tests/test_capability_projection.py`: `d817c81195989d11faf35d711db9040ae2a9239bd81ebc4f79bd141365261a4e`
- `tests/test_contract_graph.py`: `5d58eaa4f7be073076bc9828ea30b68417cf335ac0c80343873ee4b6ff9ab0cb`

