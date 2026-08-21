# Round121 v18-P2 Identical-Success Repeat Guard 预注册协议

日期：2026-08-16（实现前预注册；运行后不得修改口径、门槛或变量定义）

## 决策来源

- Round119（KEEP，Strict 30/90）：`identical_result_count` 已作为事实呈现给模型，
  但 LH02 仍相同读取 194 次、M21 相同写入 94 次、M28 相同读取 40 次——计数可见无效。
- Round120（REVERT，Strict 22/90）：全量覆盖投影 + step 意图同时可见，LH03 仍重复到
  200，且 step 回显制造了新的重复吸引子（B03 同一 verify step 重复 199 次）。
- 两轮共同否证了"更多/更好的事实进上下文能打破循环"的假设家族。13B RWKV 不会主动
  消费这些事实；打破循环必须是机制（预算/拒绝），如同 Round119 已验证的失败侧预算
  （M24 103→15 Actions）。

## 假设

对**完全相同的调用**（相同 operation + 相同全部参数）在已经连续产生字节相同的成功
结果 K 次之后，拒绝再次执行并把最近一次的完整结果原样回显给模型，可以：

1. 打破成功观察循环（B03-R120 型 verify 循环、LH02/LH03/M28/H12/H13/H14 型集合重读、
   M21 型重复写），把浪费的 Action 转化为分歧或诚实 Final；
2. 大幅降低 prompt tokens 与 rollover 次数（循环是 token 爆炸的首因）；
3. 可能解锁部分集合题（模型被迫从重读转向聚合/写出）。

## 精确变更（全局机制，无单题特判）

### C1 guard 规则（rwkv_lh/controller.py）

1. 在执行前检查：候选调用的 `action_fingerprint`（operation+全部参数的既有摘要）在
   历史 Action 中已有 **>= 3 次 SUCCEEDED 且其中最近三次的 observation_fingerprint
   完全相同**时，不执行该调用。
2. 拒绝以新 causal event `identical_call_repeat_rejected` 持久化（新注册 payload schema
   `rwkv-lh.identical-call-repeat.v1`），并把以下事实作为 ModelEvent 回显给同一 RWKV：
   operation、显式参数、已成功次数、**最近一次完整 exact result（原样，含既有 6000
   字符截断规则）**、说明文字（"该调用已第 N 次返回逐字节相同的成功结果，最近结果
   已在此原样回显；请选择不同的操作/参数，或用 final_answer 结束"）。
3. Controller 不建议替代操作、不改参数、不生成答案；模型换任何一个参数即可绕开
   guard（那本身就是分歧）。
4. `RunState` 新增投影计数 `repeat_guard_rejections`（fold 自新事件类型），预算
   `_MAX_REPEAT_GUARD_REJECTIONS = 12`；耗尽后 `terminal_reason =
   "repeat_guard_budget_exhausted"`，仍由 RWKV 生成 terminal `final_answer`。
5. guard 拒绝消耗 transition（与协议拒绝一致），不消耗失败预算；失败调用不受 guard
   影响（失败侧已有 Round119 预算）。
6. `RUN_SCHEMA_VERSION` 升为 `long-horizon.run.v19`（新增投影字段），旧状态不静默迁移。

### 明确不改

- 不加 step contract、progress projection、reviewer、Task DAG（Round120 已回退）。
- 不改 `_assignment`/rollover/采样/其他预算；Round119 的观察指纹、终止事务、
  move_file/file_digest/timeout_ms 全部保留。
- 官方 v1 验收、数据集、相似度口径不变。

## 预期影响与非回归

- 预期受益：LH02/LH03/M17/M21/M28/H12/H13/H14/B03 型循环（token 与 Action 大降）、
  部分集合题可能 TN→TP。
- **预注册风险披露**：H04 在 Round119 靠 33 次相同 list 后写出正确产物（TP）；guard
  会在第 4 次相同 list 时打断，H04 可能翻转为失败。B29 有 2 次相同 list（低于阈值，
  不受影响）。
- **KEEP 红线**：Strict >= 30；Round119 的 30 个 TP 保留 >= 28/30；FN <= 2；
  90/90 终态完整（0 running、0 空 Final）。
- 期望（非 KEEP 条件）：Strict > 31、FP <= 24、FN <= 1（若同时达成则追加 confirmatory
  Full90）；prompt tokens < 12M；最大相同观察重复 <= 6；>=20 Action 用例 < 12。

## 冻结参数

与 Round118/119/120 完全一致：model `rwkv7-g1i-13.3b-20260805-ctx16384`、endpoint
`http://127.0.0.1:29610/v1`、temperature 0.05、top-p 1.0、top-k 0、penalties 不变、
max-transitions 200、concurrency 1、uv 0.12.5、suite all（90）。

## 流程

1. 实现 C1；新增离线回归：第 4 次相同成功调用被拒且回显最近完整结果、参数变化不
   触发 guard、失败调用不触发 guard、12 次坚持后 interrupted 且 RWKV 生成 Final、
   新计数器 fold/reload 一致、Round119 全部既有回归不回退。
2. 离线门：全量 pytest、catalog 90/90、compileall、`git diff --check`。
3. 冻结只读 source manifest → 运行完整 Full90 一次。
4. 产出 `Round121_v18p2_full90/`：REPORT、results、RUN_PROTOCOL、cases、
   MANUAL_CAUSAL_ANALYSIS（全 90 首次偏离 + 对 Round119/Round46 双 flip 矩阵 +
   固定指标块）。
5. 按红线判 KEEP/REVERT；达到 Strict > 31 且 FP <= 24 且 FN <= 1 时不改源码追加
   confirmatory Full90，两轮均过才可 checkpoint 为新基线。
