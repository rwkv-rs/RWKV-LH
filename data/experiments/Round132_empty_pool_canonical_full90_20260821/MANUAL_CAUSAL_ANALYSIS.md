# R132 empty-pool canonical Full90 — 终局因果结案

日期：2026-08-21  
协议：`../Round132_TERMINAL_COMBINATION_RECORD_ATTEMPT_PROTOCOL.md`  
冻结源：`../Round132_source_manifest_20260821.json`，source tree SHA-256
`4a51629f4387160d86fb30e29aa59277b3b1fab50b29ec1a7fe521099b82864b`  
最终判定：**REVERT；TERMINAL SUCCESS 未达到；确认 Full90 不启动。**

## 1. 运行有效性

- R129–R131 全部被锁定选择规则排除，R132 因此机械执行 EMPTY-POOL FALLBACK；active
  ingredient 为空，没有新增机制。
- 固定 RWKV-E2E-90、模型、采样、concurrency 1、max-transitions 200、prompt replay 和逐题
  spawned-worker 回收均未改变。
- 90/90 结题、0 running；90/90 Final 非空，90/90 delivered Final 与所选原始 RWKV Final
  一致。不存在 controller 改写答案或 hidden acceptance 介入生成。
- frozen manifest 67 项复核 0 mismatch；运行目录的 56 项 `source_tree_manifest.json` 与冻结
  manifest 的 `source_files` 完全一致。
- 服务因 56 个评分失败按 runner 约定 exit 2，不是运行崩溃。Wall 3h45m18s、CPU
  43m42s、MemoryPeak 12.0 GB、MemorySwapPeak 7.8 GB；逐题 worker 回收持续有效。

## 2. 固定口径结果

| 指标 | R126 official B | R126 confirmatory floor | R130 repaired canonical | R132 | 相对 R130 repaired |
|---|---:|---:|---:|---:|---:|
| Strict / TP | 36 | 34 | 35 | **34** | -1 |
| FP | 30 | 31 | 29 | **30** | +1 |
| FN | 0 | 0 | 0 | **0** | 0 |
| OTHER | 24 | 25 | 26 | **26** | 0 |
| Agent completed | 66 | 65 | 64 | **64** | 0 |
| Interrupted | 24 | 25 | 26 | **26** | 0 |
| Model requests | — | — | 2,844 | **3,504** | +660 |
| Executed actions | — | — | 2,494 | **3,171** | +677 |
| Protocol rejections | — | — | 248 | **235** | -13 |

分组：basic 23 TP / 7 FP；medium 8 TP / 16 FP / 6 OTHER；hard（含 LH）3 TP /
7 FP / 20 OTHER。byte-precision B01/B06/B13/B19/B28 = **5/5**。

重建 R126 official TP 保留 33/36，损失 LH09、M06、M24；锁定 R128 proxy 保留 28/31，
损失 B29、M11、M24。两个集合都损失 3 题，超过“至多损失 2 题”的 G5 操作化门槛。

## 3. 空池与 default-off 完整性

R132 的 runner 与 R130 repaired canonical byte-identical；B01 bootstrap 的 reference/current
SHA-256 均为 `5225e07a0d686b343072e7c6cb446b04dc80fa5983e1aee4362efedfac922564`，
9,587 chars、2,177 local tokens、全部 bytes 相同。

对全部 3,504 次 generation 的审计：

- order ensemble `enabled=true` 0 次，非 canonical generation 0 次；
- confidence deferral `enabled=true` 0 次、`should_defer=true` 0 次；
- logprobs 请求/返回均 0 次；transcript override 0 次；
- 每次 ensemble audit 都只有一次 canonical generation。

因此 dormant R130/R131 plumbing 没有替代或掩盖 RWKV 能力；本轮观测到的变化只能是同一
canonical RWKV 路径的运行方差，不能归因于被拒绝机制。

## 4. 全量 churn 与因果解释

相对 R130 repaired canonical：TP→TP 32、TP→FP 1、TP→OTHER 2；FP→FP 25、
FP→OTHER 4；OTHER→TP 2、OTHER→FP 4、OTHER→OTHER 20。没有任何实验变量 firing，故两个
OTHER→TP 与其他 churn 都不能作为新机制的 attributable win。

R132 以 Strict 34 落在已经登记的 R126 canonical 34–36 单轮方差带下沿；FP 30、FN 0
也复现了 canonical baseline 的整体形态。它没有产生新架构证据，只再次确认残余问题集中在
RWKV 深层动作选择和最终形状投影，而不是 transport、Final 改写、实验开关泄漏或评分器。

## 5. 锁定 gate 判定

| Gate | 结果 | 证据 |
|---|---:|---|
| G1 byte 5/5 | PASS | 5/5 |
| G2 Strict ≥ confirmed floor 34 | PASS | 34 |
| G3 FN≤1 且 OTHER 不高于 B | **FAIL** | FN 0；OTHER 26 > official 24，也 > confirmatory 25 |
| G4 90 valid、zero running | PASS | 90/90、0 running |
| G5 R126 TP retention | **FAIL** | 33/36；proxy 28/31；均损失 3 题 |
| G6 Strict ≥ best single prior 36 | **FAIL** | 34 < 36；空池下 interaction attribution 本身不适用 |

Terminal thresholds：Strict 34 > 31、FN 0 ≤ 1、90/90 valid、0 running 均通过；**FP 30 >
24，差 6 题**。所以首个 source-frozen Full90 没有达到 terminal precondition，协议中的
confirmatory Full90 必须跳过，不能通过额外随机轮“试到过线”。G3/G5/G6 也独立要求 REVERT。

R132 没有 active diff 可撤；当前 generic 运行路径继续保持 R126 canonical behavior，两个
被拒绝机制只在 default-off 边界后保留审计代码。由于既非 TERMINAL SUCCESS，也不满足全部
G1–G6 的 NON-TERMINAL KEEP，**不创建 git checkpoint**。

## 6. 根因、全局影响与回归风险

R129 证明同类项拆分会导致 completion collapse；R130 证明 K=3 order ensemble 成本暴增且
损害 byte/retention；R131 证明 confidence veto 触发后 RWKV 9/9 立即重复 Final，不能诱导
一个直接动作。三条剩余 admissible 路径都没有把目标 FP 类转成可归因 TP，故 R132 的 eligible
pool 为空。这是系统级负证据，不是个别题特判。

剩余 FP 的根因仍是 RWKV 在深层状态中把自然语言交付约束投影为精确 envelope/字节输出时的
动作选择错误；generic controller 无法在不解析题意、不生成业务答案、不引入 reviewer 的红线内
替模型补齐语义参数。继续增加 veto、重复校验或状态机只会提高复杂度，不能替代 RWKV 核心能力。

主要回归风险是未来 generic constructor 意外重新启用 order ensemble 或 confidence deferral。
全套 121 tests、bootstrap fidelity、3,504 次 runtime audit 与 source manifest 的组合验证覆盖了
这条边界。最终固定数据、全流程、边界、异常、历史 completion-collapse 和开关泄漏路径均已复核。

