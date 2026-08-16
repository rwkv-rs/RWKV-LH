# Round119 v18-P0 Fact Integrity 预注册协议

日期：2026-08-15（实现前预注册；运行后不得修改本文件的口径、门槛或变量定义）

## 决策来源

Round118 v17 Full90 diagnostic：Strict `25/90`、External `27/90`、Agent `60/90`、
FP `35`、FN `2`。逐题反向因果分析（`Round118_v17_full90_diagnostic/MANUAL_CAUSAL_ANALYSIS.md`）
确定五层无状态放大链；其中三层属于"链路事实完整性"，与在线行为变量（step contract、
progress projection）机械可分，按 `V18_PLAN_AND_GOAL_PROMPT_20260815.md` 的推荐拆分
先行实施。全部证据已用原始 `results.json`/`audit.json`/`causal_ledger.json` 独立重算复核
（见该文件 §〇）。

## 假设

三项事实完整性缺陷是独立于模型能力的系统放大器。修复后：

- H1（观察指纹）：相同失败不再因 workspace digest/参数易变而被当成新失败；
  `_MAX_IDENTICAL_FAILURES=5` 预算真实生效，M24 型 50 次同一失败循环被截断为 ≤5 次后
  由 RWKV 收尾；相同成功观察的 exact repeat count 成为模型可见事实，
  H04/B08/B29 型重复有客观计数（本轮不据此改变 controller 行为）。
- H2（终止事务）：generation outcome unknown 不再逸出 `run()`；M16/M17/M21 型
  运行必然落入 completed/interrupted/failed 终态并追加 terminal causal event；
  90/90 无 `running` 残留。
- H3（通用能力）：B08（file digest）、M28（move）、M30（timeout_ms）三个接口性
  失败消除；对应外部正确的工作可以完成。

## 精确变更（全部为全局机制，无单题特判）

### C1 观察指纹与预算重绑（rwkv_lh/controller.py、rwkv_lh/schema.py）

1. `ActionRecord` 新增 `observation_fingerprint: str`，对每个终态 Action（成功与失败）
   计算：`digest({operation, target(path|destination|argv|cwd 中显式存在者), outcome_type,
   exit_code, error, output})`。不含 workspace digest、artifact revision、易变非目标参数。
2. 失败 Action 的 `failure_key` 值改为该 observation_fingerprint（字段名保留）；
   `_MAX_IDENTICAL_FAILURES=5` 语义不变，但现在跨 workspace 变化/参数变化累计。
3. `RunState` 新增投影 `observation_counts: dict[fingerprint,int]`，由 `action_finished`
   事件 fold 重建，进入 `projection_payload`；`RUN_SCHEMA_VERSION` 升为
   `long-horizon.run.v18`，旧状态不静默迁移。
4. 模型可见 Observation payload（`_action_observation_event`）：新增
   `observation_fingerprint` 与 `identical_result_count`（含本次的精确重复计数，
   成功与失败都有）；移除 `failure_count_for_same_causal_key`（其值并入前者语义）。
   Controller 不据计数选工具、改参数、否决 Final。

### C2 终止事务（rwkv_lh/controller.py）

1. `run()` 主循环捕获 `RWKVRuntimeError`（含 OutcomeUnknown/Transport/HTTP/Protocol
   运行时错误）：持久化 `model_transport_failure` causal event（新注册
   payload schema `rwkv-lh.model-transport-failure.v1`），控制器级有界重试
   （8 次，指数退避封顶 60s；prompt-replay 下重发生成安全）。
2. 重试耗尽 → `terminal_reason="model_transport_unavailable"` 进入 `_terminal_output`；
   `_terminal_output` 同样捕获 `RWKVRuntimeError`，其终态回落路径为
   `run_failed`（reason `model_transport_unavailable`，`final_output=""`，
   `controller_rewritten=False`）。任何退出路径都追加 terminal causal event；
   禁止 Controller 合成用户答案。

### C3 通用能力（rwkv_lh/harness.py、rwkv_lh/model.py）

1. 注册 `move_file`（source,destination；side_effect、非幂等；postcondition
   destination file_exists + source file_absent）。
2. 注册 `file_digest`（path；read-only、幂等；输出 sha256 与 size_bytes）。
3. `run_command/check_command` 透明转换 `timeout_ms→timeout`（毫秒→秒；
   与显式 `timeout` 冲突时拒绝；trace 记录 raw/normalized）。
4. 两个新操作进入统一 catalog（preferred order：`file_digest` 紧随 `read_json`，
   `move_file` 紧随 `copy_file`）。无题目专属操作。

### 明确不改

- 不加 step contract、progress projection、rollover 策略（Round120 变量）。
- 不改 `_assignment` 的 recent-12 结构、采样、预算常量、`_MAX_PROTOCOL_REJECTIONS`。
- 不改官方 v1 验收、数据集、相似度算法。architecture-neutral v2 验收本轮不建
  （留待独立登记，避免与本轮变量混淆）。

## 预期影响与非回归

- 预期直接受益：M24/H11（失败预算生效）、M16/M17/M21（终态）、B08/M28/M30（能力）。
- 预期风险：识别失败预算生效后，B10 型"多次同错误重试后偶然修复"的路径会更早终止；
  这是预注册接受的行为（同一失败 5 次即由 RWKV 收尾）。
- 非回归红线（KEEP 条件）：Full90 Strict 不得低于 25；Round46-TP 保留不得低于
  Round118 的 18/31；FN 不得高于 4；90/90 Final 非空或 status=failed 且有 terminal
  event；0 个 `running`。
- KEEP 之外的期望（不作为 KEEP 条件，仅记录）：Strict > 25，FP < 35。

## 冻结参数

model `rwkv7-g1i-13.3b-20260805-ctx16384`；endpoint `http://127.0.0.1:29610/v1`；
temperature 0.05、top-p 1.0、top-k 0、penalties 同 Round118；max-transitions 200；
concurrency 1；uv 0.12.5；suite all（core30 + LH12 + extension48，共 90）。

## 流程

1. 实现 C1–C3；新增/更新离线回归（指纹稳定性、成功计数、transport 终态、
   move/digest/timeout_ms、fold/reload 一致性、crash recovery 非幂等 move 不重放）。
2. 离线门：全量 pytest、E2E catalog 90/90、compileall、`git diff --check`。
3. 首次模型请求前生成只读 source manifest；运行完整 Full90 一次。
4. 产出 `Round119_v18p0_full90/`：REPORT.md、results.json、RUN_PROTOCOL.json、
   逐题 cases、MANUAL_CAUSAL_ANALYSIS.md（全部 90 题首次偏离 + 对 Round118/Round46
   的完整 flip 矩阵 + 固定指标块）。
5. 按非回归红线判 KEEP/REVERT；REVERT 则整体回退本轮代码后再进入 Round120 设计。
