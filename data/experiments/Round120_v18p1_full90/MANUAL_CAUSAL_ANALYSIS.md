# Round120 v18-P1 Full90 人工因果分析

日期：2026-08-16

状态：运行后人工分析；manifest 复核 49/49 一致，运行中未改源码/数据/口径。
预注册协议：`data/experiments/Round120_V18P1_STEP_AND_PROGRESS_PROTOCOL.md`。

## 一、结论与判定

**判定：REVERT。** Strict `22/90` 低于红线（>=30），Round119 TP 保留 `16/30` 低于红线
（>=27），FN `7` 超过红线（<=2）。按预注册规则整体回退 C1（step contract）+ C2
（progress projection），回退后以 Round119 冻结 manifest 逐文件哈希验证恢复。

这不是一次无信息的失败：step contract 表现为**双刃**——它把 FP 压到 `22`（首次低于
Round46 的 24），新增 6 个 TP（含老大难 M21/M24），但它的回显在 prompt replay 中
形成**自我强化的重复吸引子**，把大量简单题变成 200-Action 循环，总 prompt tokens
暴涨至 66.9M（Round119 的 3.6 倍）。

## 二、固定指标块

| 指标 | Round46 | Round119 | **Round120** |
| --- | ---: | ---: | ---: |
| Strict / External / Agent | 31 / 32 / 55 | 30 / 30 / 66 | **22 / 29 / 44** |
| FP / FN | 24 / 1 | 36 / 0 | **22 / 7** |
| Basic / Medium / Hard Strict | 24 / 5 / 2 | 21 / 6 / 3 | **16 / 5 / 1** |
| Round46 TP 保留 | — | 21/31 | **17/31** |
| Round119 TP 保留 | — | — | **16/30** |
| prompt tokens / 均值 | 3.5M / ~2160 | 18.6M / 9047 | **66.9M / 9410** |
| requests / actions / rejects | 1622/—/— | 2060/1698/264 | **7109/6812/142** |
| >=20 action 用例 | — | 17 | **39** |
| 最大相同观察重复 | — | 194 | **200 (LH03)** |
| rollovers | — | 168 | **695** |
| 终态完整 | — | 90/90 | **90/90**（0 running、0 空 Final 保持） |
| 中断原因 | — | — | transition 26、protocol 6、identical-failure 8、terminal-protocol 8 |

## 三、机制归因（trace 级证据）

### 3.1 首因：step 回显的重复吸引子（预测失误的修正）

中期我假设失败来自"step 必填的格式拒绝"。**终盘 trace 否证了这个假设**：全轮协议
拒绝只有 142 次（比 Round119 的 264 还少）——13B 模型完全能维持三键 envelope。
真正的机制是：

- **B03（TP→TN，200 Actions）**：A00001 用 write_json 一步写入（但跳过了先读，
  丢失无关字段），A00002 起 step 变为 "Verify config.json contains ..."，随后**同一
  step、同一 read_json 重复 199 次**。step 文本通过 Observation 回显 + 投影
  `current_step` 反复出现在 transcript 中，prompt replay 的续写倾向使"重复上一步"
  成为最强吸引子。done_when 早已满足，但没有任何结构把模型推出该 step。
- 同型：LH03 重复到 200、B06/B13/B14/B26 等原快题全部变成 >=20 Action 循环；
  39 个用例进入长尾（Round119 为 17 个），transition 预算耗尽成为最大中断原因（26 例）。
- Round46 的"意图"之所以有效，是因为**任务结构会在动作间切换**（系统进入下一局部
  Task，意图随之更新）；R120 的 step 完全由模型自更新，粘滞的 step = 无限循环。

### 3.2 step 的正面效应（必须记录，供后续设计复用）

- 新增 TP：M21（旧 94 次重复写循环→正确合并 records）、M24（coding 老大难→测试
  通过）、B11/B17/M03/M29（精确变换类）。
- FP 从 36 降到 22：一次成功 mutation 后直接谎报完成的模式明显减少；Agent completed
  从 66 降到 44，完成边界事实上收紧。
- 结论：**意图绑定对语义质量有真实收益，但注入方式不能是模型自维护的必填输出**。

### 3.3 write-first 退化

B03/B25/M05 等题跳过"先读再写"（A00001 直接 write），推测与 bootstrap 中投影/指令
占位改变了采样轨迹有关。B03 因此丢失无关字段；B25/M05 同型 FP。

### 3.4 FN=7 的构成

B29/M02/M20/B04/M01/M06/M30：外部验收已通过（工作实际完成），但模型陷入循环未
宣布完成，或在 terminal 边界协议耗尽（8 例 `rwkv_terminal_answer_protocol_exhausted`，
run_failed 但 Final 非空保障保持）。工作是对的，完成宣告被循环吞掉。

### 3.5 投影未能刹车

覆盖事实、`identical_result_count`、`repeated_identical_observations` 全部可见的情况下，
LH03 仍重复到 200。**"更多/更好的事实进上下文"这一假设家族至此被两轮数据否证**
（R119 计数可见无效，R120 全量投影+意图仍无效）。13B 模型不会主动消费这些事实；
打破循环必须依靠机制（预算/拒绝），而不是提示。

## 四、Round121 设计推论

1. 整体回退 C1+C2（本轮）。
2. 下一个单变量：**成功侧相同观察防重复 guard**——与失败预算对偶：同一
   observation fingerprint 的成功结果重复达到阈值后，拒绝再次执行完全相同的调用，
   拒绝信息只陈述事实（"该调用已第 N 次返回逐字节相同结果"）并要求换操作或
   final_answer。Controller 不选择替代操作、不改参数、不改答案。
   - 直接靶点：B03 型 199 次验证读、LH02/LH03 型集合重读、M28 型 40 次重读、
     M21 型 94 次重写（R119 残留）。
   - 已知风险（预注册披露）：H04 在 Round119 靠 33 次相同 list 后偶然写出正确产物；
     guard 会更早打断该循环，H04 可能翻转。
3. step 的正面效应（FP 下降、M21/M24 解锁）记录为后续独立变量的方向：意图必须由
   **结构**承载（例如系统在 Observation 回显中机械附上"你上一步调用是 X"），而非
   模型自维护的必填字段；本轮不与 guard 混合。

## 五、审计材料

- 官方输出：本目录 REPORT.md、results.json、RUN_PROTOCOL.json、90 cases。
- 冻结 manifest：`Round120_v18p1_source_manifest.json`（运行后复核 49/49）。
- flip 与统计脚本（只读）：`temp/analyze_round119_full90.py`（传入本目录）。
- 关键 trace：B03/B10 的逐 Action step 记录（本文件 §3.1 引用），由
  `cases/E2E-B03/audit.json` 原始数据逐条人工复核。
