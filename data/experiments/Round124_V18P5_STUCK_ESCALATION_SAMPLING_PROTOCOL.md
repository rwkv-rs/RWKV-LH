# Round124 v18-P5 采样策略 v2（默认分歧 + 重复观察升级）预注册协议（已冻结，2026-08-16）

日期：2026-08-16（实现前预注册；运行后不得修改口径、门槛或变量定义）。
本文件取代早先草案：草案把升级触发键在**失败**（failure_key ≥ 2）上；全量 90 轨迹
分析（下）证明 R119 基线上**不存在失败循环**，真正的病理是**重复的成功**，故触发条件
更正为"重复观察（observation_fingerprint 计数 ≥ 2，成功或失败）"。基线更新为 Round119
（R122 判 REVERT，guard 不在基础内；R123 判 INVALID/ABORTED，见其目录）。

## 授权记录

项目所有者于 2026-08-16 明确授权请求级采样并指定方向：**默认档即 temp 0.4 /
top_p 0.6 / top_k 50**，发现重复后升更高温度档。此授权修订十轮 goal 中"temperature
0.05 全程冻结"条款。seed 不可用（后端 vllm-rwkv rapid-sampling 拒绝 seed）。

## 决策来源（全量 90 轨迹分析 + R123 证据）

1. **R123 决定性证据（INVALID 轮）**：temp 0.05 近贪心解码下，输入不变 ⟹ 输出逐字节
   不变。当动作不改变可见世界时构成数学不动点，29/29 案例撞 200 步天花板。这直接证明
   近贪心解码是循环的主因，而非纯模型缺陷。
2. **R119 全 90 轨迹重复结构分析**（`data/experiments/Round119_v18p0_full90`）：
   - 15 个案例存在同一 observation_fingerprint 重复 ≥ 8 次；
   - **15/15 的主导重复是 SUCCESS，0 个是 FAILURE**（LH02 194×、LH03 137×、
     M21 94×、M17 51×、M28 40× …，全部 status=succeeded）；
   - 这 15 例中 14 例 benchmark 失败（仅 H04 以 29× 重复侥幸过）。
   - 结论：病理是"模型成功地重复做同一件不推进的事（反复 list/read），永不前进到
     写交付物"。**任何以失败为键的升级都不会触发**，故触发必须键在重复观察上。
3. top_p 0.6 对精确任务有内生保护：分布尖锐（照抄/精确写入）时 top token 质量 > 0.6，
   nucleus 截断后近确定；只有模型真不确定处 temp 0.4 才引入分歧。
4. presence/frequency 惩罚不进默认档：写含合法重复 token 的长内容（JSON 键、重复词）
   时惩罚会制造字节错误；仅在升级档使用。

## 假设

1. 默认分歧档（temp 0.4）降低不动点/吸引子的形成概率（循环更少发生）。
2. 重复观察升级档让"刚刚原样重复过一次"的下一决策真正换路，打断 LH02/M21 型
   成功重复循环 → 这些 TN 有机会转 TP。
3. top_p 0.6 保护下，字节精确对照组（B01/B06/B13/B19/B28）不回退。

## 精确变更（全局机制，无单题特判）

### C1 两档采样策略（仅 `rwkv_lh/model.py`）

1. **默认档（所有请求）**：`temperature 0.4 / top_p 0.6 / top_k 50 /
   presence_penalty 0 / frequency_penalty 0 / penalty_decay 0.996`。
2. **升级档触发（机械、可审计，单一条件）**：即将附带的 Observation 对应的最近动作，
   其 `observation_fingerprint` 在 `state.observation_counts` 中的计数 **≥ 2**
   （即模型刚刚产生了至少第二次逐字节相同的观察，成功或失败均计）。
3. **升级档**：`temperature 0.8 / top_p 0.6 / top_k 50 / presence_penalty 0.65 /
   frequency_penalty 0.25 / penalty_decay 0.996`。
4. 回落：天然无状态——一旦产生新的（非重复）动作，其新 fingerprint 计数为 1，
   下一请求自动回默认档；无需显式状态机。
5. terminal `final_answer` 生成**恒用默认档**（终局不升温）。
6. 每次请求的实际档位与 `policy_reason`（`default-v2` /
   `escalated:repeated_observation`）写入 TempDecision 与 causal 事件（
   model_call_accepted/rejected 已内嵌 temp_decision），全程可审计。

### 明确不做 / 红线兼容

- 升级采样只发生在新的决策点：被拒/失败/重复的尝试完整留在因果账本，不存在"第二次
  采样冒充第一次决定"；Controller 不选工具、不改参数、不改答案。
- 触发条件是客观 ledger 信号（fingerprint 计数），不解析任务文本，不读隐藏验收。
- 不加投影/意图/reviewer/Task；不改工具注册表；不改 prompt 渲染（那是 R123 变量，
  已 INVALID 回退）；transport 仍诚实标注 prompt_replay。

## KEEP 门槛（因果归因 + 噪声感知，基线 = Round119）

1. **字节精确对照组** B01/B06/B13/B19/B28 至少保住 **4/5**（默认档提温的直接风险探针；
   R119 现为 5/5）；
2. Strict **≥ 30**（= R119；单run方差 ±3，低于此不算改进）；
3. FP **≤ 38**（= R119 的 36 + 2 噪声；分歧采样不得放大错误完成）；
4. FN **≤ 1**（R119 为 0）；90/90 终态完整，0 running；
5. **升级档触发过的用例中，R119 基线 TP 的损失 ≤ 1**（升温不得打坏已过的题）。
期望（非 KEEP 条件）：LH02/LH03/M21/M17/M28 等成功重复循环题 TN→TP；Strict > 31
（则追加 unchanged-source confirmatory 再判 KEEP）。

## 前置与冻结

基线 = Round119（Strict 30 / FP 36 / FN 0；字节精确 5/5；代码链 6/6）。其余与
Round118–122 一致：model `rwkv7-g1i-13.3b-20260805-ctx16384`、endpoint
`http://127.0.0.1:29610/v1`、max-transitions 200、concurrency 1、uv 0.12.5、suite all（90）。

## 流程

1. 实现 C1（仅 model.py）；离线回归：档位切换/回落逻辑、TempDecision 审计字段、
   终局默认档、重复观察触发判定；全量 pytest、catalog 90/90、compileall、diff check。
2. 冻结只读 source manifest（temp/generate_round124_*_source_manifest.py，--check）→
   Full90 一次 → `Round124_v18p5_full90/` 完整产出（REPORT、results、cases、
   MANUAL_CAUSAL_ANALYSIS 含逐请求档位归因表 + 三向 flip + 字节精确对照组逐题核对 +
   升级触发用例清单与其 TP 影响）。
