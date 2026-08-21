# Round123 v18-P4 Rebuilt Working Set — INVALID（实现故障，非计分 REVERT）

日期：2026-08-16　判定：**INVALID / ABORTED**（可审计的架构-实现故障条款）
基线：Round119（Strict 30/36FP/0FN）。本轮**未产生对假设的有效测量**，
不进入 KEEP/REVERT 计分，不占用正式轮次槽位。源码已按 R119 manifest 逐字回退
（`rwkv_lh/model.py` sha256 `49dea587…`，全树 --check 0 mismatch，107 tests green）。

## 一、观测事实（原始数据，非叙述）

停机时完成 29 个案例（第 30 例 H10 中断，未落盘）：

| 指标 | 值 |
|---|---|
| passed | **0 / 29** |
| status 分布 | `failed` × 29（全部）|
| 单算子死循环案例（≥50 actions 且 ≥90% 同一算子）| **29 / 29** |
| 平均 actions/案例 | **200**（= max-transitions 上限，全部撞顶）|

B01（"写一个问候文件"，最简单的 Basic 题）逐帧：

- actions：200 个，**全部是 `list_directory`**；protocol_rejections = 0。
- gen[0]：`{"function":"list_directory","params":{"path":".","max_entries":1024,"max_tokens":4096}}`
- gen[1..205]：**逐字节相同**的 `list_directory`（仅 envelope 从 `params` 漂移到
  `arguments` 别名、把默认值显式展开，语义完全一致）。
- 终局：terminal_answer 也在同一 working-set 形状下继续吐 `list_directory`
  函数调用而非 final 文本 → 终局协议耗尽 → `run_failed`（last_raw 为函数调用）。

## 二、根因：无状态重构 + 确定性解码 = 保证不动点

架构循环本身（状态压缩→删竞争信息→重申身份→义务搬末端→单步→执行→再压缩）
**没有错**，那是项目所有者确立的 RWKV 目标架构。错的是 **prompt_replay 层的朴素实现**：

1. 每个请求都从 `_assignment` 重新 bootstrap 一个全新的
   `User: {working-set JSON}\nAssistant: ```json\n` 回合。
2. 当一个动作**不改变可见世界**时（B01 工作区起始为空，`list_directory` 空目录
   返回空，`workspace_manifest` 保持空），下一个 working set 与上一个**近乎逐字节相同**。
3. 输入近乎相同 + temperature 0.05 解码 → 输出**逐字节相同**。
   模型永远重发同一个 `list_directory`。这是一个数学不动点：
   `input(t+1) ≈ input(t) ⟹ output(t+1) = output(t)`。
4. 唯一的增量是 `recent_exact_action_records` 里的 `identical_result_count` 1→2→3…，
   但——与 R119（重复计数被忽略）、R120（覆盖投影被忽略）一致——
   **模型对这个计数器无反应**。已被证伪的"更多事实能打断循环"家族再+1 例。

对照 append 架构（R119）为何无此病：R119 的输入是**不断增长的对话 transcript**，
每回合都在尾部追加模型自己上一条 Assistant tool 调用 + Function 输出。所以
(a) 输入每回合都不同，不构成不动点；(b) 续写点紧跟模型**自己**的上一步，模型
"继续"而非"重答一个新 User 问题"。R123 把 rollover 连同这条隐式连续性一起删了。

## 三、可迁移的教训（写入纪律）

1. **固定态模型 + 近似不变输入 + 近零温 = 死循环，与题目难度无关**（29/29、
   连最简单的 B01 都中招）。任何"每请求重构短工作集"的设计必须显式打破这个不动点。
2. 打破不动点的两条正交手段（未来纠正版设计的候选，均须各自预注册）：
   - **保留模型自身连续性**：把最近动作渲染成真实的 Assistant/Function 回合
     （模型看到的是"我刚调用了 X，得到 Y"），而非塞进 User 消息里的 JSON 数据块；
     续写点跟在 Function 输出后 → 模型继续而非重答。
   - **随世界不变而升随机性**：检测到"世界未变 + 动作重复"时抬高
     temperature/penalty（正是 Round124 stuck-escalation 采样的机理）。采样升温
     是这个不动点的**直接解药**——世界不变时，只有解码发散能逃逸（与 R122 结论
     "insistence 稳定，只有解码发散能帮上忙"完全吻合）。
3. `workspace_manifest` 为空时，working set 几乎不携带状态差分——空/不变工作区
     是最脆弱的场景，任何重构式设计都要先在空工作区探针上验证。

## 四、处置

- 源码回退：`model.py`、`tests/test_unified_controller.py` 从
  `baseline/round119-v18p0` 逐字恢复；R123 测试文件移入
  `temp/quarantined_tests/`；全树 R119 manifest --check = 0 mismatch；pytest 107 green。
- 本目录 = 诊断留存（29 例原始 audit），**不计分**。
- 下一步顺序由证据决定：本轮死循环由"世界不变→输入不变→输出不变"驱动，
  直接指向 **Round124 stuck-escalation 采样**（重复检测后升温，temp 0.05 恒定条款
  已经项目所有者授权修订为请求级两档：默认 0.4/0.6/50，卡住升 0.8+penalties）。
  纠正版重构工作集（Assistant/Function 连续性形状）作为后续独立轮次候选保留。
