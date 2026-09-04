# B01 Selector next-state 与工具描述投影诊断

## 结论

`PUBLIC-CANARY-B01-S20260902` 完整运行到了预设 Goal transition budget 上限，但没有生成 `final_answer`，因此按协议保持 `status=running` 并判定失败。

本次失败不是输出锚点、强模型请求参数、随机采样或工具未注册造成的。可复核的首要根因是：拥有独占工具选择权的 G1J Selector 每个边界都从初始 State 启动，而当前轮投影没有携带上一动作 observation、Harness 错误、Auditor 缺口或 Planner 的 `read_roots`。工具描述虽然 25/25 均存在且非空，但只在 bootstrap 中整体出现；当前 `eligible_labels` 仅含工具名，没有把候选工具描述与当前目标、路径类型和失败反馈绑定。

因此，这次运行可以作为“当前整套 Agent 架构失败”的有效证据，但不能作为后续 StateTune 对比所需的“纯模型 all-zero State 能力基线”。继续运行其余公开 Canary 和 7 个完整 Planner 用例只会重复同一系统性污染，现阶段应暂停。

## 范围与约束

- 执行环境：WSL `UbuntuRecovered`，工程路径 `/home/chase/GitHub/RWKV-LH`。
- 固定用例路径：`data/experiments/LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_g1j_zero_state_public_dev_canary_b01_b14_p01_p07_v1/public_dev/seed_20260902/cases/PUBLIC-CANARY-B01-S20260902`。
- 本轮所有 Selector、Executor、Step Auditor、Finalizer 和 Final Auditor State SHA-256 均为 64 个零。
- 没有训练，没有修改 train/dev，没有人工注入动作，没有隐藏重试。
- 本诊断阶段只读取运行产物并新增本记录；没有修改任何运行代码或模型参数。

## 运行结果

| 指标 | 值 |
| --- | ---: |
| `passed` | `false` |
| `agent_completed` | `false` |
| `external_passed` | `false` |
| `final_output_nonempty` | `false` |
| `status` | `running` |
| 模型请求 | 239 |
| 已执行动作 | 64 |
| 协议拒绝 | 170 |
| Selector 决策 | 175 |
| Goal continuation | 9 |
| Goal transition budget | 240/240，已耗尽 |
| 人工干预 | 0 |
| 隐藏重试 | 0 |

`status=running` 是正确的 fail-closed 行为：当前 Goal 协议只有 RWKV 输出并通过审核的 `final_answer` 才能停止，本次从未进入 Finalizer/Final Auditor。

## 输入格式完整性

当前 G1J 生成角色只使用已经固定的一套续写格式：

````text
PromptV1: {...}

**Tool Call:**

```json
````

B01 中未发现旧式 `Assistant: ```json` 锚点混入，也未发现两套格式拼接。Step Auditor 的原始 `{name,arguments}` 通过既定归一化层转换为 `{function,params}`；该转换没有补造语义字段。由此排除“当前格式仍然混用”作为本次循环的根因。

## 工具描述检查

- Selector bootstrap 注册 25 个工具。
- 25/25 个工具描述均为非空。
- 例如 `list_directory` 明确说明它列出有界路径、类型和大小，不读取文件内容。
- 例如 `read_file` 明确说明它读取一个本地非 JSON UTF-8 文件的有界字节范围。
- 当前轮 `eligible_labels` 只有名称，不带与候选名称绑定的描述、参数 schema 或路径适用条件。
- Executor 在 Selector 选定工具后才获得该单个工具的参数 schema；Executor 无权改选工具。

所以问题不是“完全没有工具描述”，而是描述投影位置和决策时机不对：描述存在于 bootstrap，但当前拥有工具选择权的边界看不到与最新状态绑定的可执行差异。

## next-state 检查

### Executor 状态

Executor 的主状态确实持续更新。运行记录中可恢复出完整动作结果、Harness 错误、已接受的 Auditor 决定以及当前 Planner step；后期 checkpoint 已累积到数百个，状态体量超过 600 KiB。

### Selector 状态

G1J Selector 的生产路径在每个边界显式使用 `parent=None`，因此不会继承上一 Selector WKV State。175 次 Selector step prompt 都因计数器或摘要变化而具有不同 SHA-256，但其语义字段只包含：

- `stage_objective`
- `stage_role`
- `progress.completed_stage_count`
- `progress.action_index`
- `progress.succeeded_operations`
- `progress.failed_operations`
- `progress.protocol_rejection_count`
- `eligible_labels`

实测结果：

| 检查项 | 结果 |
| --- | ---: |
| Selector 决策数 | 175 |
| 唯一 step prompt 数 | 175 |
| 含 action observation payload | 0 |
| 含 Auditor gap payload | 0 |
| bootstrap 工具数 | 25 |
| 非空工具描述数 | 25 |

这说明“prompt 每次不同”不等于“next state 有效”。当前变化主要来自 action/rejection 计数以及成功/失败过的操作种类，不能表达刚才读到了什么、为什么失败、下一步缺少什么证据。

### 错误的阶段计数语义

`build_network_selector_input()` 当前把 `completed_stage_count` 填为 `len(actions)`。B01 只有 S1 完成，S2 尚未完成，但该字段仍从 0 随动作递增到 64。这个字段实际表达动作深度，却被命名和提示成已完成阶段数，属于旧 action-depth 语义没有完全迁入新 Goal 阶段架构。

## Planner 到 Selector 的信息丢失

强 Planner 生成了结构完整的四步计划：

- S1：读取 `probe_service`；已用证据 `A00002` 完成。
- S2：读取 `pyproject.toml`、`Makefile`；查明测试命令和 console entry。
- S3：读取 `README.md`、`tests`；检查文档与测试预期。
- S4：依赖 S1/S2/S3，汇总并处理冲突。

当前 frontier 是 S2，Planner 明确给出：

```json
{
  "read_roots": ["pyproject.toml", "Makefile"],
  "allowed_operations": []
}
```

但 `goal_frontier_selector_context()` 只投影 `objective` 和固定的 `tool_intent` role，主动丢弃 `read_roots`、constraints、success evidence 和其余 step 字段。由于 `allowed_operations` 为空，运行时又回退到 11 个宽泛只读候选，而不是形成与 S2 文件读取目标相符的候选约束。

## 可复核的循环证据

- 175/175 次 Selector argmax 都是 `list_directory`。
- 64/64 个实际动作都是 `list_directory`。
- 64 个动作只有 4 组不同参数。
- 59/64 个动作使用同一组 `probe_service` 递归列目录参数。
- 61/64 个动作产生同一 observation fingerprint。
- 动作 A00003 对 `Makefile` 调用 `list_directory`，Harness 返回 `list_directory requires a directory`。
- 动作 A00004 对 `pyproject.toml` 调用 `list_directory`，返回相同类型错误。
- 上述具体错误文本从未进入后续 Selector step input；Selector 只能看到 `failed_operations=["list_directory"]`。

原始 logits 证明不存在格式归一化或后处理偷偷改选：

| 边界 | `list_directory` logit | `read_file` logit | 选择置信度 |
| --- | ---: | ---: | ---: |
| 首次 | 5.7451 | 1.8481 | 0.8079 |
| 首次进入 S2 | 5.7232 | 2.1602 | 0.7826 |
| 末次 | 5.9679 | 1.8904 | 0.8432 |

记录同时标明 `postprocessed=false`、`generated_text=false`，Executor 没有重新选择操作。

## 根因链

1. Planner 拥有当前阶段的具体目标和 `read_roots`，但没有给出 `allowed_operations`。
2. Goal frontier 投影把 `read_roots` 等 step 语义裁掉，只向 Selector 发送 objective/role。
3. G1J Selector 每轮从初始 State 开始，只有计数摘要和工具名，没有 observation、错误和 Auditor gap。
4. Selector 拥有独占工具选择权，持续选择 `list_directory`。
5. Executor 拥有完整状态和路径，但协议禁止它改成 `read_file`，只能为已选工具生成参数。
6. 重复动作持续扩大 Executor 上下文；达到 64 个动作后，Executor 开始大量产生截断、畸形或空输出，形成 170 次协议拒绝。
7. Goal transition budget 耗尽，仍没有 `final_answer`。

因此，后期空输出是循环放大和状态膨胀的下游症状，不是最初根因。

## 全局影响与回归风险

问题位于通用路径：

```text
Strong Planner frontier
  -> goal_frontier_selector_context
  -> build_network_selector_input
  -> independent G1J Selector
  -> exclusive selected operation
  -> Executor arguments
```

它会影响所有需要根据“刚才观察/错误/审核缺口”切换工具的多步 Goal，不只影响 B01。对单步恰好可用 `list_directory` 的题目可能表现正常，但不能证明 Agent 具备持续规划和工具切换能力。任何只围绕 B01 路径或答案的特判都不能解决该缺陷。

StateTune 也无法从当前输入中恢复被投影层删除的信息。若用这次运行直接作为训练前基线，后续提升会混合“模型 StateTune 效果”和“运行时恢复信息流”的效果，无法形成公平对比。

## 基线定性与后续门槛

- 当前定性：`architecture/projection-contaminated failure`。
- 可以报告：当前全系统在 B01 上真实失败。
- 不可以报告：该结果代表 G1J all-zero State 模型本体的能力上限。
- 不继续 B02-B14 或 P01-P07，直到全局 next-state/工具描述契约修复并用固定 B01 重跑验证。
- 修复不得训练、不得改变模型采样参数、不得改变测试数据、不得放宽评价口径、不得加入用例特判。
- 修复后的最低验证应覆盖：Planner step 字段投影、Selector 跨边界语义状态、候选工具描述绑定、文件/目录工具切换、Harness 失败反馈、Auditor gap 回流、真实阶段完成计数、唯一 `final_answer` 停止条件，以及历史协议回归。

## 证据文件与摘要

- `B01_S20260902_RESULT.json`
  - SHA-256: `add17d304db46c1d7ef4a670a19b2f2f215ccfc07ae602c9f4dc2d479c7758cf`
- `cases/PUBLIC-CANARY-B01-S20260902/audit.json`
  - SHA-256: `a2846bc4ef732f67952c24c1a293d72408706c14ac72e99c3defe48caae7dded`
- `temp/inspect_current_b01_selector_state_flow_v1.py`
  - SHA-256: `111378b08972e649b5c061118f9ef3267c188b59d19618ec58c9d91c2f8f659a`
- `temp/inspect_current_b01_action_feedback_v1.py`
  - SHA-256: `3cad5e8a8773c56619a5a45c4265a078a6c087bc147ba9b233b0223df19d56d6`
- `temp/inspect_current_b01_executor_state_feedback_v1.py`
  - SHA-256: `b620bb0e8d5813393cfc66373f72c6bc664e3c7302f8ebcd1e5f059eb6109b7d`
- `temp/inspect_current_b01_selector_logits_v1.py`
  - SHA-256: `2e4a382a93df6b9880d76d377f2d850fa03557f7ffe19d6d0bab12f7355f4db1`
- `temp/inspect_current_b01_goal_plan_v1.py`
  - SHA-256: `84aa46c696c72bc2d1ec516bb66e87b24f43bb278fb2630ac1f74224176038ac`
- `temp/inspect_current_b01_auditor_generations_v1.py`
  - SHA-256: `6ae66f82d08d00c942aa8a31e76e2bbb2cedad58c3ff2c792f9a70c499b1cbe8`
