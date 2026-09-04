# Selector V2 Eligibility Counterfactual V1 预注册

## 目的

在不重新调用模型、不修改任何 RWKV 原始输出的前提下，使用 E3 全量运行中持久化的 2.9B S66 25 维原始 logits，区分以下两类残差：

1. 当前机械 eligibility 没有表达写入根路径类型与 deadline 推进义务；
2. S66 head / zero-state 本身在 `CurrentDirectStageV2` 真实 atom 轨迹上没有把正确操作排到可用位置。

本实验只做离线反事实归因。任何 arm 即使通过，也只能授权后续真实 canary，不能直接授权产品发布。

## 固定来源

- E3 run：`data/experiments/ENGINEERING_CLOSED_LOOP_RERUN_V3_20260830/run_e3_pending_resume_full_v1`
- `results.json` SHA-256：`d7400d3bc2f9699feb3dab21ca3d7a734e159d23691b17bed191e7f14dc5c632`
- E3 strict analysis：`data/experiments/ENGINEERING_CLOSED_LOOP_RERUN_V3_20260830/analysis_e3_pending_resume_full_v1_strict/ANALYSIS.json`
- strict analysis SHA-256：`7394ab5e928d4825162a48586f7728a44d2a03076b2cc736bc6215d2eb60e367`
- E3 freeze SHA-256：`ff8fb49d435c2dee06c1255b86d449c0f9cb0c8e2b1edc8dd4dd83c81f3903b6`
- E3 protocol SHA-256：`6dcb6e99d7d35840e281cae418883be072cdec752901b96896561764efa519fb`
- Selector：RWKV7-G1I 2.9B，S66-M1 Soft-MoE h64，zero state；身份以来源 raw selection 记录为准。
- 用途：工程闭环完成后的 Selector V2 残差归因。
- 生成方式：只读解析 E3 audit 与 atom worker SQLite；以事件顺序重建每次 selection 之前的 contract progress，再在同一 logits 上执行固定 eligibility argmax。

## 固定样本与完整性

- 使用 E3 10/10 全部 case、全部已持久化 atom worker、全部 `exact_tool_selection_committed/rejected`。
- 不抽样、不去重、不删除失败选择。
- 必须逐条验证：25 类顺序、logits 长度、来源 eligible labels、来源 selected operation 与 eligible argmax 完全一致。
- 必须验证 source results/analysis SHA-256；任一不一致则实验失败，不产生归因结论。
- 原始 logits、来源 selected operation、RWKV 原始文本、事件与数据库均只读且不得改写。

## 固定类别与路径规则

- 类别顺序使用代码中的 `NETWORK_EXACT_TOOL_LABELS`。
- path mutation 集合使用代码中的 `PATH_MUTATION_OPERATIONS`。
- JSON-only mutation：`write_json`、`patch_json`。
- directory-only mutation：`make_directory`。
- destructive mutation：`delete_file`、`move_file`。
- non-destructive progress mutation：`write_file`、`write_json`、`patch_json`、`replace_text`、`remove_line`、`append_file`、`make_directory`、`copy_file`。
- `path_kind` 使用已登记算法：`.json -> json_file`；有其他扩展名 -> `non_json_file`；`.`、无扩展名或目录 -> `directory_or_extensionless`。
- compatibility：
  - `write_json/patch_json` 只兼容 `json_file`；
  - `make_directory` 只兼容 `directory_or_extensionless`；
  - 其他 path mutation 对三类根均视为潜在兼容（这是保守上界，不声称参数一定正确）。

## 固定 arms

- A `current`：来源 raw selection 的原始 `eligible_labels`。
- B `root_kind`：以 A 为基础；当 mutate atom 尚有未覆盖 write root 时，移除与所有剩余根均不兼容的 JSON-only / directory-only mutation。
- C `deadline_progress`：以 A 为基础；当 mutate atom 未完成、尚有未覆盖 write root 且 `remaining_action_budget <= remaining_required_count` 时，只保留与至少一个剩余根兼容的 path mutation 和 `ABSTAIN`。
- D `root_kind_plus_deadline`：先应用 B，再应用 C。
- 所有 arms 使用完全相同的 logits 和 class-order tie-break；禁止改 logits、重标定、温度变换或第二次模型调用。
- `ABSTAIN` 始终保留；`final_answer` 仍完全服从来源 eligibility，不另行放开。

### 有效运行前的预检修订

第一次实现预检在生成任何 `RESULT.json` 前以“反事实 eligibility 为空”失败。只读定位发现来源还包含 Harness 调用 `terminal_answer` 时显式传入的 `eligible_labels=[final_answer]`；这种记录是终端专用调用，不是普通 next-tool 菜单。若把它纳入 deadline arm，会错误地把 Harness 终端协议统计为 Selector 的非推进选择。

因此在首次有效运行前固定以下区分，后续不得再修改：

- `eligible_labels` 精确等于 `[final_answer]` 的记录标记为 `terminal_only=true`，A/B/C/D 均保持来源选择不变；
- `terminal_only` 单独计数，不进入 hard-deadline 反事实分母；
- 本文所称 `ABSTAIN` 始终保留，指普通 next-tool 菜单；终端专用菜单不新增类别；
- `physical_deadline` 仍按合同进度原样报告，`hard_deadline` 固定表示 `physical_deadline and not terminal_only`。

该修订只修正样本域，未查看任何反事实 arm 的有效结果，也不改变路径兼容算法、阈值或判定条件。

## 固定指标

每 arm 统一报告：

- selection 总数、operation 分布、相对 A 改变数/比例；
- non-JSON 根上的 JSON-only mutation 数；
- 有扩展名文件根上的 `make_directory` 数；
- hard-deadline 时未选择 compatible path mutation 的数量与比例；
- hard-deadline `ABSTAIN` 数；
- destructive mutation 数；
- hard-deadline non-destructive progress mutation 数；
- 按 task、atom kind、remaining root kind 的完整分层结果。

另外报告 A→D 变化的 raw-logit top-5、来源选择、反事实选择、progress 与 write-root kinds，作为可复核明细。

## 预注册判定

D 仅在以下条件全部满足时，才判定为 `mask_only_live_canary_eligible=true`：

1. 来源选择重建 100% 一致，raw identity 检查全部通过；
2. D 的两类路径不兼容选择均为 0；
3. D 的 hard-deadline non-progress 为 0；
4. D 的 destructive mutation 数不高于 A；
5. A→D 的 hard-deadline 改变中，至少 80% 落入 compatible non-destructive progress mutation；
6. D 对全部 selection 的改变率不高于 35%。

任一条件失败，固定结论为 `head_or_state_retraining_required=true`。即使全部通过，也必须在相同 E3 canary 上验证后才能改产品 eligibility。

## 输出

- `RESULT.json`：完整机器可读结果与逐条明细。
- `REPORT.md`：冻结指标摘要。
- `FILE_HASHES.json`：来源、脚本、预注册及结果摘要。
