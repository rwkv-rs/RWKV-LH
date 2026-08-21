# Round120 v18-P1 Causal Step Contract + Progress Projection 预注册协议

日期：2026-08-16（实现前预注册；运行后不得修改口径、门槛或变量定义）

## 决策来源

Round119 v18-P0 判定 KEEP：Strict `30/90`、FP `36`、FN `0`、90/90 终态完整。
其人工分析（`Round119_v18p0_full90/MANUAL_CAUSAL_ANALYSIS.md` §五）确认剩余失败
集中于两个互相耦合的缺口，与 Round118 Full90 分析 §5.3/5.4 一致：

1. **成功观察循环无界**：LH02 相同读取 194 次、M21 相同写入 94 次、LH03 137、
   M17 51、M28 40。`identical_result_count` 已可见但不足以打破循环——rollover 只保留
   最近 12 条近同 Action，覆盖事实在长任务中反复丢失重演。
2. **行动意图与义务缺失**：每轮只有 `{function,params}`；M28 85 个只读 Action 后宣布
   无需改动、M06 未复制即称已复制、H18 完成 2/3 产物后放弃第三个、M16 覆盖正确但
   输出 schema 错。模型从不声明本步目标与完成条件，多输出义务随上下文滚动消失。

这是一个缺口的两面（行动没有当前意图；观察没有跨滚动的事实投影），按
`V18_PLAN_AND_GOAL_PROMPT_20260815.md` P1 与 Round118 分析 §6 预注册为单一结构变量。

## 假设

- H1（step contract）：RWKV 在同一次生成中声明 `step.objective/done_when` 后，
  一次成功 mutation 不再被直接等同于全部义务完成；工具漂移（B12 型）与提前 Final
  （M06/H18 型）减少。
- H2（progress projection）：bootstrap 与每次 rollover 从全量 causal ledger 生成
  确定性进度投影（per-path 读/写计数与 mutation 后是否再观察、list 成员的已读/未读
  覆盖事实、fingerprint 重复计数、当前 step 原文）后，"全部读完再从头重读"
  （H12/H13/H14/LH03/LH11 型）与成功循环（LH02/M21 型）显著缩短；prompt tokens
  总量下降。

## 精确变更（全局机制，无单题特判）

### C1 统一因果步 contract

1. wire 协议：普通操作调用必须为
   `{"step": {"objective": "...", "done_when": "..."}, "function": "<op>", "params": {...}}`；
   step 与调用同一次模型生成。`final_answer` 的 step 可选。
2. `model_io.parse_model_command_with_trace` 接受 envelope 级 `step` 字段：两字段均为
   非空字符串（各 ≤ 500 字符防失控）；缺失/非法时 ModelIOError 拒绝，错误文本给出
   完整期望 envelope；已选 operation 的精确 schema 反馈机制不变。
3. step 不进入 `ModelCommand`（commit 一致性检查不变），经
   `ModelCommandNormalization.step` → `ActionDecision.step` → `ActionRecord.step`
   原样登记；`action_started` payload 与模型可见 Observation payload 携带该 step。
4. Controller/投影不解析、不评分、不依据 step gate 任何 Action 或 Final；step 仅为
   RWKV 自己的意图事实。

### C2 CausalProgressProjection

1. `LongHorizonModel._assignment` 由"最近 N 条完整 Action 记录"改为确定性投影：
   - `paths`：每个被观察/变更的 path 的 reads/mutations 计数、最后 outcome、最后
     result digest（12 hex）、`read_after_last_mutation` 布尔（机械事实）；容量上限 48
     （最近触达优先，截断时注明 truncated）。
   - `list_coverage`：每个成功 list_directory 目录（取最新一次结果）的成员、其中已有
     read observation 的成员与尚无 read observation 的成员（集合差为机械事实，不判断
     业务目标）；每目录成员上限 80。
   - `repeated_observations`：fingerprint 重复计数 ≥3 的 operation/target/最后 outcome/
     计数，上限 16，按计数降序。
   - `current_step`：最近一个 Action 的 step 原文。
   - `last_protocol_rejection`：最近一次拒绝的错误文本（如有）。
   - `recent_results`：最近 4 条完整 exact ActionResult（原样，含 output 截断规则）。
2. `_rollover_if_needed` 保留序列改为 `(4, 2, 0)`；每次 rollover 的 assignment 均含
   最新投影。投影不解析隐藏验收、不算业务汇总、不标注"应该选择"的成员、不生成
   expected 值。
3. bootstrap instruction 同步更新：说明调用 envelope 与 progress 字段为机械事实。

### 明确不改

- 不加 reviewer、Task DAG、成功侧预算（若成功循环仍在，作为 Round121 独立变量）、
  语义 completion gate。
- 不改官方 v1 验收、数据集、相似度口径、采样、`_MAX_*` 预算常量。
- Round119 的观察指纹/终止事务/通用能力全部保留。
- `RUN_SCHEMA_VERSION` 升为 `long-horizon.run.v19`（ActionRecord 新增 step 字段），
  旧状态不静默迁移。

## 预期影响与非回归

- 预期受益：LH02/LH03/M17/M21/M28/H12/H13/H14（循环缩短）、M06/H18/M16（义务保持）、
  B12/B29 型工具/格式漂移。
- 风险：step 必填增加格式拒绝；预注册接受一次性拒绝换取意图绑定（B16/B17 已证明
  精确 schema 反馈单次恢复）。
- **KEEP 红线**：Strict >= 30；Round119 的 30 个 TP 保留 >= 27；FN <= 2；
  90/90 终态完整（0 running、0 空 Final）。
- 期望（非 KEEP 条件）：Strict > 31（超过 Round46）、FP < 36、prompt tokens < 18.6M、
  最大相同观察重复 < 50。

## 冻结参数

与 Round118/119 完全一致：model `rwkv7-g1i-13.3b-20260805-ctx16384`、endpoint
`http://127.0.0.1:29610/v1`、temperature 0.05、top-p 1.0、top-k 0、penalties 不变、
max-transitions 200、concurrency 1、uv 0.12.5、suite all（90）。

## 流程

1. 实现 C1+C2；新增离线回归：envelope step 解析/拒绝/登记/回显、final_answer 无 step
   可接受、投影确定性（同状态两次构建一致、reload 后一致）、覆盖集合差正确、
   `read_after_last_mutation` 正确、rollover 保留 ≤4 条且含投影；更新既有测试的调用
   格式。
2. 离线门：全量 pytest、catalog 90/90、compileall、`git diff --check` 全绿。
3. 冻结只读 source manifest → 运行完整 Full90 一次。
4. 产出 `Round120_v18p1_full90/`：REPORT、results、RUN_PROTOCOL、cases、
   MANUAL_CAUSAL_ANALYSIS（全 90 首次偏离 + 对 Round119/Round46 双 flip 矩阵 +
   固定指标块）。
5. 按红线判 KEEP/REVERT；REVERT 则整体回退 C1+C2 后重新设计。若 Strict > 31 且
   FP <= 24 且 FN <= 1，则不改源码追加 confirmatory Full90。
