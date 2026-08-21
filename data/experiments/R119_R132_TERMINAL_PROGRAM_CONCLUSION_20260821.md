# R119–R132 终局程序结案（含授权延长 R129–R132）

日期：2026-08-21  
结论：**14 轮全部完成；终局目标未达到，诚实负结果；程序在 R132 结束。**

## 1. 锁定目标与最终状态

终局目标是 source-frozen Full90 达到 `Strict > 31 ∧ FP ≤ 24 ∧ FN ≤ 1 ∧ 90/90 valid ∧
0 running`，再由 unchanged-source confirmatory Full90 达到同一阈值，最后创建本地 git
checkpoint。

R132 的 source-frozen Full90 为 **34 TP / 30 FP / 0 FN / 26 OTHER**，90/90 valid、0
running、byte 5/5。它通过 Strict、FN 与执行完整性门，但 FP 比目标多 6 题；确认轮的前置条件
没有成立，因此确认轮和 git checkpoint 都不启动。

## 2. 原十轮与四轮延长

R119–R128 的完整因果链和诚实负结果已经记录在
`R119_R128_TEN_ROUND_HONEST_NEGATIVE_RESULT.md`。这一阶段的最佳有效 KEEP 是 R126
request-last adjacency：official **36/30/0/24**，confirmatory **34/31/0/25**；它把 Strict
历史最好提高到 36，但未达到 FP≤24。

授权延长的四轮结果：

| Round | 唯一变化 / 角色 | TP | FP | FN | OTHER | 判定 | R132 资格 |
|---|---|---:|---:|---:|---:|---|---|
| R129 | homogeneous `_assignment` decomposition | 28 | 31 | 0 | 31 | REVERT | EXCLUDED：completion collapse、0 attributable target win |
| R130 | K=3 order-permutation ensemble | 33 | 31 | 1 | 25 | REVERT | EXCLUDED：byte/G2/G3/G5 失败、因果帮助未证明 |
| R131 repaired | final-operation confidence deferral | 35 | 29 | 0 | 26 | REVERT | EXCLUDED：9/9 立即重发 Final、0 attributable FP→TP |
| R132 | empty-pool canonical fallback | 34 | 30 | 0 | 26 | REVERT | 终局轮；FP/G3/G5/G6 失败 |

R130 repaired canonical validation 与 R131 repaired 都曾出现 FP 29（离目标仍差 5），但它们
不是通过全部 safety/causal gates 的新 KEEP；程序基线与终局结果仍按预注册规则停在 R126。

## 3. 为什么没有第 133 轮

R132 协议在 R129–R131 运行前已经锁定为第 14 个、最后一个 round，并禁止 R132 发明新机制。
三个候选机制均被证据排除，所以 R132 只能执行空池 baseline Full90。该 Full90 没有达到
terminal precondition，协议也没有授权失败后继续抽样或新增 R133。

额外运行 unchanged-source Full90 只是在已经测得的 ±3 方差带内继续抽样，既不能降低已登记的
因果门，也不能把失败轮变成合规确认轮。因此停止是执行锁定口径，而不是提前放弃。

## 4. 根因与全局结论

跨完整数据集和相关代码路径得到的结论一致：

1. append-only prompt replay 与 request-last-inside-JSON adjacency 是可复现的正向 RWKV
   状态几何；R126 是唯一显著且可归因的后期 KEEP。
2. 重复强调、per-turn request re-injection、request extraction 和 homogeneous decomposition
   会让 RWKV 进入 fixed point 或 completion collapse，不能再作为 FP 修复方向。
3. order ensemble 会把物理 generation 成本扩大并扰动 canonical trajectory；它真实 firing，
   但没有通过 byte/retention 安全门，也没有建立可归因 FP→TP。
4. confidence deferral 能识别低置信 Final，却不能改变 RWKV 的动作选择；9/9 firing 都在零个
   intervening direct action 后立即重发 Final。
5. 剩余 FP 主要是 RWKV 深层状态中的自然语言约束→精确 output envelope/字节投影错误。若由
   controller 解析题意、猜语义参数、改写 Final 或增加 reviewer，会让辅助模块取代模型能力，
   违反实验红线，也不能作为系统性修复。

所以 FP≤24 在当前固定模型、数据、采样、generic controller 红线下没有被已筛机制达到。这个
负结论覆盖 90 题全数据、basic/medium/hard/LH 同类场景、bootstrap/transport/action/Final
上下游路径，以及历史 fixed-point、completion-collapse、default leak 和资源稳定性风险。

## 5. 最终可复核状态

- R132：90/90、34/30/0/26、byte 5/5、90/90 raw-RWKV Final match。
- Runtime：3,504 generation；ensemble enabled 0、confidence enabled/deferral 0、logprobs 0、
  transcript override 0。
- Source：67 项冻结复核 0 mismatch；运行输出的 56 项 source manifest 与冻结清单一致；
  canonical bootstrap 与 R130 repaired byte-identical。
- Regression：`pytest` **121 passed**；`compileall` passed。
- 处置：R129/R130/R131/R132 均无可保留新机制；generic path 保持 R126 canonical behavior；
  无确认 Full90、无 R133、无新 git checkpoint、无 push。

详细 R132 数值和 gate 证据见
`Round132_empty_pool_canonical_full90_20260821/FIXED_SCORE_AUDIT.json` 与同目录
`MANUAL_CAUSAL_ANALYSIS.md`。
