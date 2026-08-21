# R131 repaired Full90 — Final-Operation Confidence Deferral 因果结案

日期：2026-08-21  
协议：`Round131_FINAL_OPERATION_CONFIDENCE_DEFERRAL_PROTOCOL.md`  
冻结源：`Round131_repaired_source_manifest_20260821.json`，source tree SHA-256
`9a8e7c1a32ccea73e0e6edf37f944e03322e34173982eb7424d0ec443e217f9e`  
最终判定：**REVERT；R132 EXCLUDED。**

## 1. 运行有效性

- 固定 RWKV-E2E-90，concurrency 1，max-transitions 200，逐用例 spawned worker 回收。
- 90/90 结题，0 running；90/90 Final 非空，90/90 delivered Final 与所选 RWKV 原始
  Final 一致。
- source manifest 66 项复核 zero mismatch；运行输出中 56 个源文件与冻结清单逐文件
  hash zero mismatch。
- 服务按基准 runner 约定以 exit 2 结束（存在评分失败），不是运行崩溃。CPU 31m21s，
  MemoryPeak 12.0 GB，MemorySwapPeak 4.1 GB；高峰均来自单题大型审计导出，worker 更换后
  回落到约 0.4 GB。

首次 Full90 因 stop 后缀正文与 logprob 尾部 offset 不一致而 70/70 eligible Final
元数据误判缺失，已在同级目录的首次运行 `MANUAL_CAUSAL_ANALYSIS.md` 标为
`INVALID_IMPLEMENTATION`。本 repaired run 没有改阈值、数据、评分、采样、提示或机制规则；
只同步裁掉正文外的尾部 logprob token，121 项离线回归通过后重新冻结源。

## 2. 固定口径结果

| 指标 | R130 repaired canonical baseline | R131 repaired | Delta |
|---|---:|---:|---:|
| Strict / TP | 35 | **35** | 0 |
| FP | 29 | **29** | 0 |
| FN | 0 | **0** | 0 |
| OTHER | 26 | **26** | 0 |
| Agent completed | 64 | **64** | 0 |
| Interrupted | 26 | **26** | 0 |
| Model requests | 2,844 | **2,796** | -48 |
| Executed actions | 2,494 | **2,493** | -1 |
| Protocol rejections | 248 | **197** | -51 |

分组：basic 24 TP / 4 FP / 2 OTHER；medium 7 TP / 16 FP / 7 OTHER；hard
4 TP / 9 FP / 17 OTHER。byte-precision B01/B06/B13/B19/B28 = 5/5。

重建 R126 official TP 保留 33/36，损失 M06、M21、M24；R128 proxy 保留 27/31，
损失 LH10、M11、M21、M24。

## 3. 机制完整性

- 73 个 eligible normal Final：73/73 `metadata_available=true`，0 missing。
- 9 个 run 触发延迟，每个 run 最多 1 次；全部 metric 严格小于冻结阈值
  `-0.40040510160761184`。
- 28 个 forced terminal Final：28/28 `eligible_lane=false`、0 deferral。
- 非 Final operation 没有被延迟；阈值、span、比较符和一轮一次 cap 均与协议一致。

因此 G6 在修复重跑中真实通过，机制不是 no-fire。

## 4. firing 因果审计

| Case | Baseline→R131 | metric | deferral 后到 Final 的 accepted operation | 结论 |
|---|---|---:|---|---|
| B06 | TP→TP | -0.501728 | `final_answer` | 无新增动作；TP 保留 |
| B08 | TP→TP | -0.443627 | `final_answer` | 预注册 canary；无新增动作；TP 保留 |
| M06 | FP→FP | -0.406726 | `final_answer` | 目标 firing，无帮助 |
| H08 | FP→FP | -0.545048 | `final_answer` | 目标 firing，无帮助 |
| M14 | OTHER→FP | -0.468203 | `final_answer` | 仍非 Strict；无新增动作 |
| M18 | FP→FP | -0.419239 | `final_answer` | 无帮助 |
| M22 | FP→FP | -0.409058 | `final_answer` | 无帮助 |
| M23 | FP→FP | -0.430869 | `final_answer` | 目标 firing，无帮助 |
| M26 | FP→FP | -0.438854 | `final_answer` | 目标 firing，无帮助 |

所有 9 次延迟后，RWKV 都没有选择 read/write/verify 等直接操作，而是立即再次 Final。
所以机制实际只是一次终局 veto，没有产生协议假设中的“补一个动作再 Final”路径。

预注册帮助切片 M06/H08/M23/M26 均 firing 但 FP→FP；M15 本次未 crossing。预注册风险
canary B08 firing 后 TP→TP；M11 未 firing 而 TP→OTHER，属于随机路径/retention 损失，
不能归因于机制。**Attributable FP→TP = 0。**

全量相对 R130 repaired 的 churn：TP→TP 33、TP→OTHER 2；FP→TP 1、FP→FP 25、
FP→OTHER 3；OTHER→TP 1、OTHER→FP 4、OTHER→OTHER 21。唯一 FP→TP 没有 firing，
唯一 OTHER→TP 也没有 firing，都是非机制方差。

## 5. 冻结门判定

| Gate | 结果 | 证据 |
|---|---:|---|
| G1 byte 5/5 | PASS | 5/5 |
| G2 Strict ≥34 | PASS | 35 |
| G3 FP≤30/FN≤1/OTHER≤24 | **FAIL** | FP 29、FN 0、OTHER **26** |
| G4 90 valid、zero running | PASS | 90/90、0 running |
| G5 retention loss≤2 | **FAIL** | R126 loss 3；R128 loss 4 |
| G6 confidence integrity | PASS | 73/73 metadata；max 1；forced 0 firing |
| Attributable FP→TP | **FAIL** | 0 |

虽然 Strict 35 / FP 29 单看达到了协议中的方向性数值条件，但 KEEP 要求所有 G1–G6
通过且至少一个 attributable FP→TP。本轮 G3、G5 和因果归因失败，所以必须 REVERT。

## 6. 全局结论与风险

置信度信号能够稳定识别低概率 `final_answer` 边界，但“只告诉同一 RWKV 上一 Final 被
延迟”不足以改变下一步操作选择；模型 9/9 立即重申 Final。继续叠加同类 veto、重复校验
或 reviewer 只会增加状态机复杂度，不能替代 RWKV 的动作选择能力。

R131 代码保持 generic default-off，仅供实验复核；R132 不得包含该机制。R129、R130、
R131 均已 EXCLUDED，因此按锁定 R132 §3 执行空池 fallback：byte-/behavior-fidelity 的
R126 canonical best-baseline 新鲜 Full90，不发明任何新机制。
