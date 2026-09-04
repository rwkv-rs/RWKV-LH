# Round141：事务化原子图 v2 Canary 分析

## 结论

Round141 为 `0/3`，不进入 Full90。v2 解决了失败副作用污染，并成功把复杂任务拆成真实并行 RWKV scout，但还没有解决 atom 内的操作选择、输入预算和结束协议。

原始记录：

`data/experiments/Round141_transactional_atom_graph_v2_canary_B04_M16_LH06_20260822/`

## 门结果

- external pass：`0/3`，失败。
- B04、M16 均达到 12-stage 上限并 interrupted；LH06 达到 12 stage，interrupted。
- B04 有 2 个首阶段 scout 同时启动；LH06 有 4 个 scout 同时启动；M16 有 4 个 scout 同时启动。并行结构与真实时间重叠成立。
- failed/interrupted atom 不再把 snapshot 残留提交到父 workspace；事务门成立。
- atom failure、action count、stage count 和 external 质量门失败。

## v2 已解决的问题

1. **失败副作用隔离有效。** B04 的错误路径、M16 多次 snapshot 内 `recovered.json` 均未在 failed/interrupted outcome 后进入父 workspace。
2. **atom-first 任务身份有效。** M16 不再由一个 RWKV读取全部五组输入；首 stage 分成 `01–02`、`03`、`04`、`05` 四个并行 scout。
3. **动态失败依赖有效。** Planner 不再把 failed id 作为合法 dependency；只重派失败的 05 scout。
4. **finalizer 生命周期收紧有效。** 没有再出现 Round140 那种在失败物化文件上连续接受多个 finalizer 的情况。
5. **写权限工具过滤有效。** read-only atom 不再产生写越界副作用。

## 新的系统根因

### 1. 权限过滤仍然太粗，需要 Planner 级 operation contract

目前 read-only atom 仍同时看到 `list_directory/read_file/read_json/file_digest/check_command` 等全部只读操作；writer 看到全部路径写操作。结果：

- B04 archive inspector 对 `check_command` 重复调用 32 次；
- M16 的 05 scout 重复 `read_file` 25 次；
- M16 assembler 在 `read_file/read_json/write_file/check_command` 之间漂移，并多次产生 10–12 个 protocol rejection；
- B04 需要 byte-preserving copy，但所有 correction atom 选择 `write_file` 并把字面量 `source.txt` 写入目标，始终没有选择 `copy_file`。

GPT 已知道原子是什么，但没有结构化声明“这个原子只允许哪些操作”。仅靠自然语言 objective 不足以约束 RWKV 的工具选择。

### 2. Dependency handoff 太大

v2 将依赖 atom 的 recent actions、完整 result、artifact 和 candidate 一起注入。LH06 的四个并行 scout 完成后，assembler/finalizer bootstrap 多次超过本地输入上限：约 15.7k–16.3k tokens，高于 14,551 token limit，产生 `InputBudgetError`。

下游真正需要的是 compact factual handoff：candidate、最小 artifact path/hash/size 和必要观测摘要；不需要重复整个 action trace。完整 trace 继续保存在审计层，不应全部进入模型层。

### 3. 缺少 atom action budget 与强制 Final 边界

Planner 目标是 1–6 个直接操作，但运行时只设置了 40 transition 上限。RWKV可重复读同一文件或调用同一错误工具，直到几十个 action。需要由 committed atom 声明小的 `action_budget`，达到后只允许 RWKV返回 `final_answer`，不能继续选择工具。

### 4. 输出 shape 仍需进入结构化原子合同

LH06 已正确选出 requirements 内容，但写成 `authoritative_source`，目标需要 `source`。Planner objective 曾说明“authoritative source path”，但没有稳定传成明确的 JSON key contract。operation contract 应允许 GPT 明确用户蕴含的 output shape，并给 assembler 只展示 `write_json/read_json`。

## v3 整改方向

1. `SupervisorAtom` 增加 `allowed_operations`：GPT 选择 1–6 个操作名，不生成参数；RWKV只看到这些工具并独立生成参数、执行和观察。
2. `SupervisorAtom` 增加 `action_budget`：1–8 个直接 action；达到后 controller 强制进入 final-answer-only 边界。
3. Stage request 提供当前 Harness 的 operation catalog；动态 JSON schema 把 `allowed_operations` 限定为真实可用操作名。
4. 本地校验 operation 与 role/write scope 相容：finalizer 只能读，普通 scoped writer 不能选择 workspace-wide side effect。
5. dependency handoff 删除 action history，只保留 bounded candidate 与最小 artifact facts。
6. Planner明确可指定操作种类和用户蕴含的 output shape，但仍不得生成工具参数、执行工具或发明观测值。

这仍保持职责边界：GPT 决定阶段、原子、依赖、工具种类和产物合同；多个 RWKV 负责参数化工具调用、实际观察、写入和 Final。

