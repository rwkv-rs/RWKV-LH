# Round138 GPT-5.4 在线微任务 + RWKV 波次 Full90 分析

日期：2026-08-22

## 结论

Round138 完成固定 RWKV-E2E-90 的 90/90 用例，但未通过预注册晋级门槛，不能替换
R126 canonical baseline。

在线 Planner/Reviewer 方向不是无效：相对 R132 canonical，本轮出现 10 个 `FP→TP` 和 2 个
`OTHER→TP`。但是 29 个 Supervisor 终止性失败、20 个错误 acceptance、以及仍然严重的 RWKV
重复读/无进展循环抵消了收益。当前实现只验证了“每题一个顺序 RWKV worker，题间并发 6”，还没有
实现或验证“一个任务内由 GPT 调度多个并发 RWKV worker”的目标架构。

因此下一步先修控制面和任务图，不开始生成训练数据，也不以本轮结果替换基线。修复后先跑固定
targeted canary，再决定是否重跑 Full90。训练只解决清洁状态下的 RWKV 选工具、执行和完成判断，不能
代替 Supervisor 协议、调度、持久化与并发隔离的系统修复。

## 运行有效性

- 运行目录：`Round138_online_gpt54_protocol_wave_full90_20260822/`
- 固定 suite：90/90 有结果，0 running；Basic30 / Medium30 / Hard18 / Long-horizon12。
- 时间：2026-08-22 02:15:47 UTC 至 04:05:23 UTC，约 1 小时 49 分 36 秒。
- case 并发：6；每题独立 workspace/store。
- Worker：`rwkv7-g1i-13.3b-20260805-ctx16384`，3056 次请求，0 个 model transport failure
  event。
- Supervisor：OpenAI-compatible `gpt-5.4`，在线 `online_microtask`。
- GPT 工具执行数为 0；728 条已提交指令均登记 `supervisor_action_executed=false`。
- 56 个完成态 Final 全部是 byte-exact raw RWKV output；controller 改写数 0。
- hidden acceptance 未进入模型/Supervisor trace；anti-cheating/case infrastructure failure 为 0。
- `run_started` 正确登记在线架构，但 `action_session_started` 仍错误投影
  `online_task_graph=false, reviewer=false`。实际在线指令行为和 `RUN_PROTOCOL.architecture` 均可复核，
  因而这不改变本轮分数，但属于必须修复的审计元数据缺陷。

## 预注册门槛

| 指标 | 门槛 | Round138 | 结论 |
| --- | ---: | ---: | --- |
| Strict TP | > 36 | 36 | FAIL |
| FP | ≤ 24 | 20 | PASS |
| FN | ≤ 1 | 3 | FAIL |
| byte-precision | 5/5 | 4/5 | FAIL |
| 分层无 completion collapse | 全部通过 | Hard 1 TP；Long-horizon 0 TP | FAIL |
| 完整性/非干预 | 必须通过 | 通过 | PASS |

总体分类：`TP 36 / FP 20 / FN 3 / OTHER 31`；Agent completed 56，external passed 39。
完成候选的实际 precision 为 `36/56 = 64.29%`，20/56（35.71%）是 Reviewer 错误接受。

分层结果：

| Native level | TP | FP | FN | OTHER |
| --- | ---: | ---: | ---: | ---: |
| Basic | 25 | 3 | 1 | 1 |
| Medium | 10 | 9 | 2 | 9 |
| Hard | 1 | 3 | 0 | 14 |
| Long-horizon | 0 | 5 | 0 | 7 |

byte-precision 固定用例：B01 TP、B06 TP、B13 OTHER、B19 TP、B28 TP。B13 不是字节生成错误，
而是 Supervisor 返回空 `disposition` 后整题中断；按预注册口径仍必须计为 4/5。

## 与既有轮次比较

| 轮次 | 架构 | TP | FP | FN | OTHER | RWKV requests | Actions | GPT calls |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R126 official | canonical baseline | 36 | 30 | 0 | 24 | - | - | 0 |
| R132 canonical | R126 路径复测 | 34 | 30 | 0 | 26 | 3504 | 3171 | 0 |
| Round134 | 静态 Plan + terminal review | 17 | 5 | 10 | 58 | 4936 | 4441 | 165 |
| Round138 | 在线单微任务 + action/protocol waves | 36 | 20 | 3 | 31 | 3056 | 2695 | 757 |

相对错误的 Round134 静态变体，Round138 增加 19 TP、减少 27 OTHER，RWKV requests 减少
38.1%，actions 减少 39.3%，证明“执行期间在线纠偏”比“一次静态 Plan + 只审 Final”更符合目标。
代价是 GPT 调用从 165 增至 757，总 token 从 483,527 增至 10,896,497（22.54 倍）。

相对 R132，Round138 的净变化是 `TP +2 / FP -10 / FN +3 / OTHER +5`。其中 FP 下降不能全部
解释为修复：7 个 R132 FP 只是变成了 OTHER。

R132→Round138 的非对角翻转：

- `FP→TP`（10）：B05、B16、B18、B22、B24、B29、M04、M06、M22、M27。
- `OTHER→TP`（2）：M01、M09。
- `TP→FP`（4）：B14、B27、M03、LH10。
- `TP→FN`（2）：B03、M30。
- `TP→OTHER`（4）：B13、H10、M02、M21。
- `FP→OTHER`（7）：H03、H06、M10、M14、M15、M19、M25。
- `OTHER→FP`（3）：LH02、LH06、M28。
- `OTHER→FN`（1）：M11。

12 个正向 TP 翻转说明在线拆解存在真实信号；10 个 TP 损失都有可定位的控制面、目标保持或循环
原因，因此不能把本轮净分简单解释成 RWKV 能力上限。

## 根因一：Supervisor 可用性和返回协议

34 个未完成用例中，29 个最终原因是 `supervisor_directive_unavailable`，3 个是
`protocol_rejection_budget_exhausted`，2 个是 `transition_budget_exhausted`。

29 个终止性 Supervisor 失败：

| 错误 | 数量 |
| --- | ---: |
| 非 initial outcome 返回 `review_status=initial` | 11 |
| HTTP ReadTimeout | 6 |
| 空 disposition | 3 |
| 空 review_summary | 2 |
| 空 review_status | 2 |
| content 不是单一 JSON object | 2 |
| 没有当前 Final 却 accept_final | 1 |
| initial/satisfied 带 issues | 1 |
| continue 但 completion_checks 为空 | 1 |

其中 8 个是请求层失败（6 ReadTimeout、2 malformed content），21 个是 API 已返回后未通过本地
语义校验。虽然请求发送了 `response_format.json_schema.strict=true`，provider 仍返回违反 enum、
minLength 或条件约束的内容，证明当前兼容网关不能作为 schema enforcement boundary。

B03、M11、M30 三个 FN 的外部工作区验证已经通过，只是分别因空 completion checks、错误 initial
review status、以及在非当前 candidate 上 accept 而中断。它们直接证明“Supervisor 一次坏响应就
fail-closed 终止整题”会丢弃正确的 RWKV 工作结果。

必须先做的系统修复：

1. 客户端独立执行完整 JSON Schema 校验；使用条件 schema/`oneOf` 表达 continue、accept_final、
   initial、satisfied、needs_correction 的互斥约束，不能依赖兼容网关。
2. 对可修复的结构/语义错误，发起带精确 validation error 的有界 repair；不能直接中断，也不能让
   controller 猜测或补全业务内容。
3. Supervisor 是无副作用控制调用，ReadTimeout 可以使用稳定 request digest 有界重试；增加全局
   Supervisor semaphore、指数退避和 jitter，将 GPT 控制面并发与廉价 RWKV worker 并发分开。
4. 持久化 `supervisor_pending` 边界。API 暂时不可用时可恢复重试，不应把已有正确 artifact 变成 FN。

## 根因二：Reviewer 丢失不可变目标，20 次错误接受

20 个 FP 都能仅依据公开 user request、公开 action/artifact 和 workspace 证据识别，不需要 hidden
verifier。它们不是“外部 verifier 才知道”的模糊差异。

- 精确文本/字节契约错误（5）：B04、B14、B27、M08、M23。包括多写 JSON 引号、额外空行、
  漏替换子串、缺 final newline、改变声明内容的 JSON 空格。
- 结构/schema/路径/计算错误（10）：M03、M13、M16、M18、M26、M28、M29、H08、LH04、LH06。
  包括保留 obsolete 字段、算术错误、错误字段名/嵌套、错误相对路径、移动到错误目录、输出过度扩展。
- 编排/恢复/API/完成性错误（5）：H09、H17、LH02、LH09、LH10。包括未形成所需事件证据、错误
  resume 语义、checkpoint 集合错误、重复 API side effect 达 9 次、以及 Reviewer 明知 35 action
  耗尽且代码未修仍接受“未完成报告”。

典型目标漂移：

- B04 的 Supervisor completion check 把“路径文本后跟一个 newline”改写成带引号的
  `"archive/2026/source.txt\\n"`，RWKV 精确执行了错误的改写契约，Reviewer 又按该改写契约通过。
- B27 把“every complete occurrence of protocol=v1”缩窄成“完整行”，因此保留了
  `fallback_protocol=v1`。
- M13 的 Reviewer 声称总计与 CSV 匹配，但实际 target revenue 39.5，artifact 是 52.5。
- LH10 的最终 review 明确承认代码仍错误、README 和 manifest 缺失，却仍提交 accept_final。

下一版不能让 Planner 的自然语言改写覆盖原始目标。每个 microtask 必须携带不可变
`request_digest` 和原始 goal clause 引用；exact-output/path/schema 条件保留为 typed obligation。
Reviewer 接受时必须逐项返回 obligation→evidence refs，且只允许引用当前 artifact revision 和实际
read/check 结果，不能只复述 RWKV 的完成声明。

## 根因三：RWKV 仍存在大规模无进展循环

- 2695 actions 中仅 312 次 workspace mutation（11.58%）；2383 次不改变 workspace（88.42%）。
- 1954 个重复 action fingerprint（72.50%）；1908 个重复 observation fingerprint（70.80%）。
- 最大连续相同 action 为 23 次（M13）。
- action 类型以 `read_file=1598` 为主，其次是 `list_directory=284`、`read_json=204`；实际写入
  `write_file=203`、`write_json=189`。
- H01 199 actions 仅 1 次 mutation；M02 190 actions 仅 8 次；LH05 188 actions、0 mutation；
  LH01 148 actions、3 mutations。当前“两次完全相同且零进展则 review”只能抓连续同指纹，抓不到
  交替读、等价参数变化或跨 wave 的无新证据循环。

下一版需要按 obligation progress 而不是单 action equality 监控：一轮没有新的 artifact revision、
workspace digest、有效 evidence 或已完成 obligation 就判为 stagnant；连续两轮 stagnant 必须重规划或
终止该 microtask。并发 RWKV worker 之前必须先有此约束，否则只会并发放大循环和成本。

这些轨迹之后可以用于训练 RWKV 的 `state→next operation`、参数完整性、exact contract 保持、
完成/继续判断和 anti-loop，但只能使用通过验证的局部片段；不能把 FP 的 Planner 改写或循环轨迹直接
当正样本。

## 根因四：状态持久化仍为超线性成本

Round138 目录占用约 9.0G，其中 90 个 `long_horizon.db` 合计 8,816,021,504 bytes。最大单题：

- LH05：1,737,814,016 bytes
- H01：1,480,142,848 bytes
- M02：1,086,087,168 bytes
- LH01：766,967,808 bytes

2695 actions 产生 8.8GB DB，仍符合“每个事件重复持久化大 state JSON/trace 投影”的近二次膨胀特征。
Round134 约 17.48GB，本轮虽下降约 49.6%，但主要来自 action 减少，不代表根因已修。应将 canonical
event、artifact revision、action result 正规化存储，快照改为低频 checkpoint + delta；GPT 请求只发送
本轮 delta 和压缩 obligation ledger，而不是每次重复最近 32 个完整 action result、全部 artifacts 和
manifest。当前成功返回的 749 次 GPT 调用平均 prompt 约 14.2k tokens，重复上下文是 10.90M token
总量的主要来源。

## 目标架构应如何推进

Round138 是单 lane 在线纠偏，不是最终的多 RWKV 调度器。下一阶段建议按以下顺序，不把训练和架构
问题混在一起：

1. **P0 控制面可靠性**：条件 schema、本地校验+有界 repair、ReadTimeout 重试、GPT 全局限流、
   pending/resume、审计元数据一致性。
2. **P1 不可变 obligation ledger**：原始 request 为唯一 authority；Planner 只拆分，不得改写 exact
   contract；每个完成判断必须绑定 evidence refs。
3. **P2 依赖任务图 + RWKV worker pool**：GPT 低频生成/修订 DAG；无依赖 ready nodes 由多个 RWKV
   worker 并发。读任务可并发；写任务按路径/资源加锁或使用隔离 overlay 后确定性 merge；GPT 仍无
   Harness action authority。
4. **P3 进展和成本边界**：wave 只传 delta；跨 wave stagnant detection；修复 event-store 膨胀；
   GPT 调用按任务节点/异常里程碑触发，而不是固定每 6 actions 重放大上下文。
5. **P4 固定 canary 后再 Full90**：覆盖 Supervisor 失败（B03/B13/M11/M21/M30）、false accept
   （B04/B14/B27/M03/M13/LH10）、长循环（M02/H01/H10/LH05）和已取得的正向翻转，先证明不丢
   原有 TP、无错误 acceptance、无控制面中断，再重跑 Full90。
6. **P5 训练数据**：只在架构边界稳定后，从 TP 和已验证局部 segment 提取种子；把 20 个 FP、29 个
   Supervisor 协议失败和高重复 action 段作为对比/拒绝样本，不直接生成或训练。

当前决策：Round138 **REJECT for baseline replacement，KEEP as architecture/trace evidence**。
