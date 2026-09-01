# RWKV Goal Loop v2 审核与整改结果

日期：2026-09-01

## 最早可证实失败

最早失败不是 `PlanPatch`、JSON parser 或传输格式。

- trace：`data/experiments/G1J_STATEFUL_GOAL_LOOP_V2_WEIGHT_SWAP_20260901/run_g1j_s60_h64_dev_selection_r2/DEV_PREDICTIONS.jsonl`
- 记录：`dataset_id=s39`、`sample_id=S60-10c5f52faf65e25fa6c4f124`
- 具体字段：`label=list_directory`，`selected=read_file`，`raw_argmax=read_file`，`exact=false`，`postprocessed=false`

该记录已经有完整 logits 和最终选择，证明失败发生在 2.9B Selector 分类层。更上游的工程原因是 v7 把完整多步骤 Goal 放在语义尾，当前 frontier 放在更前位置，迫使 Selector 重新推断任务顺序。

S39 固定 dev 结果：accuracy `0.9509918094`、macro-F1 `0.9492750664`，均未达到 `0.96` gate。下游 13.3B 尚未执行，因此该条 trace 没有下游继承错误。

## 另外证实的工程缺陷

1. 2.9B 只给候选、13.3B 再 Top-K 复选，造成工具选择职责重叠。
2. Auditor 从 Executor checkpoint fork，retry feedback 会污染 Executor State。
3. Auditor prompt 暴露禁止模型输出的 kernel 字段名。
4. Auditor 只收到 evidence refs，没有对应 Harness action/result/artifact 事实。
5. Auditor role 默认错误继承 Executor State profile。
6. rolling plan 只能追加，不能真正 replace/discard 未完成步骤；旧 action 也没有 step revision 隔离。
7. 模型可见阶段格式与 committed trace 格式不一致：响应嵌套、事件展平。
8. Stage `repair` 已提交但 Planner 暂不可用时，恢复链可能跳过未完成修订。
9. Stage Checker 原先只有 action 状态/引用，没有有界参数和结果投影，无法做可信语义检查。

## 当前整改

- Strong Planner 输出 `rwkv-lh.goal-plan-patch.v2`：`add_stages/replace_stages -> [{stage, steps[]}]` 与 `discard_step_ids`。
- v1 平面事件只读兼容；v2 模型响应、committed event 和 UI 都保持嵌套阶段格式。
- 阶段内步骤同级；依赖只能来自更早阶段；读/写和写/写根冲突在提交前拒绝。
- 当前 frontier 只来自最早未完成阶段；整个阶段完成后才进入 Strong Stage Checker。
- Stage Checker 只输出 `verdict/gaps/reason`；身份、stage、step IDs、evidence refs 由 Controller 绑定。
- repair feedback 与后续 Planner patch 通过 durable source ID 关联；恢复时必须先完成未关联 repair。
- 2.9B Selector v8 只看一个 frontier，并拥有唯一工具选择权；13.3B 不再复选工具。
- Executor 一次只接收一个步骤和一个已选工具 schema。
- Auditor 每次 clean State；WKV 不 merge，retry 不写入 Executor；prompt 不再展示内核绑定字段。
- Auditor 与 Stage Checker 都获得有界 Harness action/argument/result/artifact 事实。
- 产品 runtime、CLI 和 Web 只接受 `stateful_goal`。
- Planner、Selector、Executor、Auditor 通过 `.env` 按角色替换；Auditor 未配置时复用 13.3B 部署但不继承 Executor State profile。

## G1J 模型对照

2.9B Selector 在同一 S60/V7 dev 的 2571 条逐样本配对中，G1J 相对 G1I 修复 10 条、
新增回归 29 条、共同错误 29 条；整体 accuracy 从 `0.984831` 降为 `0.977441`。净退化
19 条主要来自 S39 多步骤上下文（净 `-16`）。这是“各自基座 + 各自匹配 h64 Head”对比，
不是裸模型或 V8 frontier-only 对比。完整样本表见
`data/experiments/G1J_VS_G1I_ROLE_COMPARISON_20260901/RESULT.md`。

同一最新 Audit 模板、zero-State、证据事实和 stop suffix：

| 模型 | 结果 | 格式错误 | 语义错误 | 额外驻留 |
|---|---:|---:|---:|---:|
| G1J 13.3B | `2/2` | 0 | 0 | 0（复用 Executor 权重） |
| G1J 7.2B | `0/2` | 0 | 2 | 约 16.1 GiB |

13.3B 另有当前 selected-`write_file` 参数例 `1/1`。7.2B 能输出合法字段，但两例都忽略 `complete=true/truncated=false/eof=true` 并错误要求 repair。默认 Auditor 因此复用 13.3B。

模型测试期间只使用服务器 GPU 0（G1J 13.3B，`18230`）和 GPU 3（G1J 2.9B，
`18232`）；GPU 1/2 未触碰，7.2B 对照完成后停止。最终交接复核时 `18230/18232`
均已不监听，GPU 0/3 无本任务计算进程；唯一可见 VLLM 进程位于用户的 GPU 2，未操作。

## 并发边界

当前已经实现阶段协议、屏障、冲突门和 Strong Stage Checker，但运行时仍是一条持久 Executor State，阶段内顺序执行。不能把协议并行性冒充成运行时并发。

下一实现固定为每步隔离 Executor session/State、独立 Audit boundary；只合并 Harness/Artifact/Evidence 事实，不合并 WKV。全局写和外部副作用保持串行。

## State Tuning 判断

不启动 State Tuning。

Selector v8 改变了 portable input identity，必须先用同一固定数据重新抽取 G1J zero-State 特征并训练匹配 Head。该工作是分类 Head 适配，不是 State Tuning。只有 v8 + matched Head 和最新角色链仍在固定同类样本上重复出现模型能力缺口，才把错误输出与人工审核正确输出登记为 tuning 数据。

## 验证

- 当前 WSL 工作区核心链定向：`240 passed`，耗时 `13.33s`。
- 当前 WSL 工作区完整 suite：`771 passed, 1 warning`，耗时 `103.34s`。
- 干净提交快照核心链定向：`240 passed`，耗时 `13.17s`。
- 干净提交快照完整 suite：`615 passed, 147 failed, 1 warning`，耗时 `50.75s`。
- warning：Python 3.13 多线程进程调用 `fork()` 的既有弃用提示。
- `git diff --check`：通过。
- Python compile：通过。

干净快照的 147 项失败属于仓库打包/基础设施缺口：测试直接读取未纳入 Git 的
`data/datasets/` 或 `data/experiments/` 冻结产物。抽查的具体缺件包括
`rwkv_lh_exact_tool_coverage_v1/preflight.jsonl`、旧 Selector `selector_head.json`、
`rwkv_state_tuning_adapter_sitecustomize.py`、Router `test.jsonl` 和
`state_router_head.json`。本次提交没有为追求全绿而加入大量旧 State Tuning/Router 数据，
也没有将缺件测试改成 skip。核心最新链在同一干净快照上 240/240 通过，但仓库整体仍不是
clean-clone 自包含；这是一项独立基础设施缺陷。

## raw trace 需求

确认最早 Selector 失败不需要打开更完整 raw trace；上述预测记录已含 label、raw logits、argmax、selected 和后处理标志。若要判断某条真实 Goal 在 Selector 错误后，Executor、Audit 或 Stage Checker 是否又产生新的独立错误，必须打开该 Goal 的完整 causal raw trace。
