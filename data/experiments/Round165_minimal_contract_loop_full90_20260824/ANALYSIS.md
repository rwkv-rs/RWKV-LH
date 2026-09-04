# Round165 Minimal Contract Loop Full90 全量分析

日期：2026-08-24  
性质：固定 90 例、预注册阈值、运行后只读分析；不调用模型、不训练、不修改 acceptance。

## 结论

本轮不能晋级，也不能替换 R126 canonical baseline。完整口径为 **19 TP / 3 FP / 3 FN / 65 OTHER**，
只通过了 13/21 个预注册门。Round164 的最小闭环确实降低了单位 TP 的强模型成本，
并消除了已知 artifact binding、content shadow、transaction integrity 和 Final 改写问题；但 Full90 暴露出
两个主导瓶颈：**Planner 中转不可用**与**不可执行的语义契约/纠错循环**。

不能把 19 TP 解释为 RWKV 的纯能力上限：36/90 条在初始 Plan 阶段因 primary 与 fallback
均失败而终止，另有 3/90 条 Plan 通过传输但未通过 schema/语义校验；这 39 条全部为
0 RWKV action。反过来，也不能把失败全归因于中转：进入闭环后仍有
16 条 evidence stagnant、
12 条 correction repeated，以及 3 个确定的 FP。

## 全量质量

| 层级 | TP | FP | FN | OTHER |
| --- | ---: | ---: | ---: | ---: |
| B | 15 | 2 | 2 | 11 |
| M | 3 | 1 | 1 | 25 |
| H | 1 | 0 | 0 | 17 |
| LH | 0 | 0 | 0 | 12 |

- completed=22，external passed=22，strict TP=19。
- TP：E2E-B01, E2E-B02, E2E-B04, E2E-B06, E2E-B07, E2E-B08, E2E-B09, E2E-B11, E2E-B14, E2E-B15, E2E-B17, E2E-B19, E2E-B23, E2E-B28, E2E-B29, E2E-H09, E2E-M02, E2E-M07, E2E-M25。
- FP：E2E-B12, E2E-B25, E2E-M29。
- FN：E2E-B03, E2E-B05, E2E-M09。
- R126 36 个 TP 仅保留 **15/36**；保留：E2E-B01, E2E-B02, E2E-B06, E2E-B07, E2E-B08, E2E-B09, E2E-B11, E2E-B14, E2E-B15, E2E-B17, E2E-B19, E2E-B23, E2E-B28, E2E-M02, E2E-M07。
- R126 丢失 21 条：E2E-B03, E2E-B10, E2E-B12, E2E-B13, E2E-B20, E2E-B21, E2E-B25, E2E-B26, E2E-B27, E2E-B30, E2E-H04, E2E-H10, E2E-LH09, E2E-M03, E2E-M05, E2E-M06, E2E-M12, E2E-M20, E2E-M21, E2E-M24, E2E-M30。

### 三种“通过”口径

- **实际产物通过（hidden external acceptance）**：22/90 =
  24.4%。这是回答“任务实际上做对了多少”的口径，即 TP+FN。
- **系统宣告完成**：22/90。其中 19 条确实正确，3 条是 FP。
- **严格端到端通过**：19/90 = 21.1%。
  这个口径要求产物正确且控制器正确结束，即 TP。

所以实际做对的是 **22 条**。19 不是实际产物上限，而是控制器同时判对的数量。当前 completion precision=
86.4%，completion recall=86.4%；二者恰好相同，
是因为本轮 agent completed 和 external passed 都是 22，但两组各有 3 条不重合。

### 3 条假阴性

1. **E2E-B03**：`config.json` 已精确得到 `name=alpha`、`feature.enabled=true`、
   `feature.mode=safe`、`retries=4`，hidden JSON equality 通过。Reviewer 只看到了修改后的文件，缺少修改前
   snapshot，因而无法证明 unrelated fields 被保留；第二次得到相同纠错签名后以
   `contract_graph_correction_repeated` 停止。
2. **E2E-B05**：`app.env` 已精确变成 `name=demo\nport=8080\nmode=prod\n`，两个 hidden check
   都通过。Reviewer 同样缺少原文件 snapshot，不能证明“只删除 deprecated 行且其他文本顺序不变”，连续两轮
   无新证据后以 `contract_graph_evidence_stagnant` 停止。
3. **E2E-M09**：API 替换、`new_api(value) -> value * 2`、移除旧定义和 unittest 都已通过；注释与字符串也保留。
   最终 4/5 obligation 已 satisfied，唯一未满足的是“相对修改前，注释和字符串未改变”。由于没有 baseline
   comparison evidence，重复纠错后停止。

三条的共同根因是 **pre-mutation baseline provenance 缺失**：执行本身正确，external acceptance 能看到最终状态，
但内部 Reviewer 无法比较修改前后。因此这是确认的系统性假阴性根因，应通过 mutation 前自动快照/摘要与
before-after assertion 修复，不应放宽 Reviewer 或针对这三条特判。

Round162 是 14/3/21/52，本轮是 19/3/3/65：TP +5、FP 不变、FN -18、OTHER +13。但按实际产物
`TP+FN` 计算，Round162 为 **35/90**，本轮只有 **22/90**，下降 13 条。因此 FN 减少不能解读为能力提升：
其中大量任务不是从 FN 变成 TP，而是受 Planner 不可用等影响落入 OTHER。
迁移中有 FN→TP 10、OTHER→TP 2，但同时有 TP→OTHER 5、TP→FP 1、TP→FN 1；波动主要来自
Planner 可用性，而不是全局能力稳定上升。

## 终止原因和中转站证据

- completed=22。
- contract_plan_unavailable=39：其中 transport
  36，semantic 3。
- contract_graph_evidence_stagnant=16。
- contract_graph_correction_repeated=12。
- contract_graph_runtime_failure=1（E2E-LH04 的注入式 post-effect crash）。

强模型共 325 个 logical request、
588 个 HTTP attempt、
239 个成功返回、86 个失败。
路由返回率：terra Planner 117/166=70.5%，sol Planner 12/49=24.5%，
terra Reviewer 110/110=100%。全部 request failure 都发生在 Plan：terra 49、sol 37，均为 HTTP 500。
因此证据支持“当前中转/路由对长 Planner 请求不稳定”，但不支持“换中转即可解决全部问题”。

成功请求延迟 median=86.3s，
p95=115.3s；返回请求累计等待
20015.9s。reasoning fallback=150，
model fallback=49，semantic reject=18，
cache store=113，cache hit=0。

Planner 输入平均 6115 chars、最大 18169；成功 Plan 输出 token
median=809、p95=1376、
max=1487，而配置上限为 4000。这证明 4000
明显高于观测需要，可把下一轮 Planner cap 预注册为 1800–2000；但“cap 导致 HTTP 500”目前仍只是待验证假设，
不能在本轮报告里当作已证因果。

## 强模型成本

- prompt=1,563,392，completion=146,327，
  total=1,709,719，reasoning=44,807，
  cached=390,400。
- 相对 Round162：logical 373→325（-12.9%），
  physical 629→588（-6.5%），
  total token 1,727,942→1,709,719（-1.1%）。
- 每 TP：logical 26.6→
  17.1；token
  123424→89985。
- correction repeated + evidence stagnant 合计消耗 178/325 logical calls
  (54.8%)、1,290,914/1,709,719 tokens
  (75.5%)、262/393 actions
  (66.7%)。这是当前最大的可控浪费源。

Round164 21 例 Canary 上看到的大幅 token 降幅没有在 Full90 复现；全量只降低 1.1%。最小批次身份载荷变小是
真的，但复杂题里的多轮 Plan/Review 仍吞掉了节省量。

## RWKV 执行与并行度

- RWKV model requests=755，actions=393，protocol rejects=81。
- planned nodes=367；atom outcomes completed=223，
  interrupted=56。
- 实际出现时间重叠的只有 10 个 case：E2E-B04, E2E-B14, E2E-B23, E2E-B26, E2E-B29, E2E-H01, E2E-M07, E2E-M14, E2E-M29, E2E-M30。
- execution batch 共 261 个：1-node=244，
  2-node=15，3-node=2；
  单节点占 93.5%。
- minimal batch canonical payload 共 69,117 bytes，
  平均 264.8 bytes，legacy process/review/node/prompt fields=0。

因此“GPT 拆成原子、多个 RWKV 并行执行”的边界已经实现，但 Planner 实际产生的依赖图高度串行：只有
17 个多节点 batch。下一步应改善**计划图的依赖表达与 ready-set 宽度**，而不是再加一层
并行管理器。

## Typed evidence 与 Reviewer

- obligations=110，assertions=288；assertion kinds：
  `{"artifact_exists": 57, "command_succeeded": 13, "digest_equal": 10, "json_exact_keys": 17, "json_required_keys": 8, "json_value_equals": 8, "json_value_from_source": 12, "numeric_aggregate": 11, "semantic_review": 105, "sequence_sorted": 11, "text_contains": 7, "text_exact": 10, "text_excludes": 3, "text_template": 1, "trailing_newline": 15}`。
- review rounds=110；local-only=2，
  mixed Reviewer=108。
- typed obligation resolutions=47，exception Reviewer resolutions=
  222；verdicts：
  `{"contradicted": 57, "insufficient": 126, "satisfied": 86}`。
- 离线 exact replay：passed=94，
  contradicted=10，
  unresolved=184；semantic exceptions=
  111。

184/288 assertion（63.9%）仍不能由本地编译器确定，导致 Reviewer 既昂贵又会犯算术/结构幻觉。三项 FP 是
同一个系统性缺口的不同表现，不应做 case 特判：

1. **B12 numeric aggregate**：源整数 4,9,-2,9,5 的 sum 应为 25，产物写成 21；Reviewer 却声称 21 与源一致。
2. **B25 source-dependent JSON shape**：请求要求 `runtime.mode` 与 `runtime.retries=6`，产物误写成
   `nested` 且 retries=2；Reviewer 接受了自洽但错误的目标结构。
3. **M29 merge/preservation**：产物扁平化 translations 且 missing_keys 错误；Reviewer 幻觉式地认定已保留并回退。

共同修复方向是扩展可执行 DSL/本地 evidence compiler：优先覆盖 JSON merge/preserve、source pointer mapping、
numeric aggregate 和 exact nested shape。确定性断言一旦可执行，Reviewer 只审核 DSL 无法表达的剩余语义。

## 完整性和权限边界

- artifactless action inheritance=0，non-content shadow=0，completed transaction violation=0。
- raw terminal exactly-one=88/90；H03/H17 有 resume 前后的两个原始 terminal，但按 supersession 计算的
  authoritative terminal=90/90。
- completed Final 与 RWKV finalizer candidate byte-exact=22/22。
- supervisor action violation=0；minimal batch legacy fields=0；strong trace tool/function fields=0。
- replay 的 `known_42_semantic_defects_safe` 是 Round162 专属旧门，在 Round165 只有 3 个已知非法断言，故其
  `all_offline_gates_passed=false` 不用于本轮晋级；本轮只采用上面逐项结构指标。

## 预注册门

- PASS `cases_90`
- PASS `running_0`
- FAIL `uncaught_runtime_failure_0`
- PASS `authoritative_terminal_90_of_90`
- FAIL `strict_tp_gt_41`
- PASS `fp_lte_9`
- FAIL `fn_lte_1`
- FAIL `r126_tp_retained_gte_34`
- FAIL `layer_b_tp_gte_24`
- FAIL `layer_m_tp_gte_11`
- FAIL `layer_h_tp_gte_3`
- FAIL `layer_lh_tp_gte_1`
- PASS `artifact_inheritance_0`
- PASS `non_content_shadow_0`
- PASS `completed_transaction_violation_0`
- PASS `logical_strong_calls_lt_373`
- PASS `strong_tokens_lt_1727942`
- PASS `minimal_batch_legacy_fields_0`
- PASS `gpt_tool_trace_fields_0`
- PASS `supervisor_action_violations_0`
- PASS `completed_final_byte_exact_100pct`

总体：**FAIL**。通过项证明最小权限边界和证据隔离方向成立；失败项证明当前系统尚不能稳定处理完整数据集，
尤其不能声称 hard/LH 可用。

## 当前架构能做到什么程度

当前版本适合作为一个**可审计的实验型多代理执行内核**：强模型只生成/审核契约，RWKV 独占工具与 Final，
执行批次足够小，结果可重放，事务和证据归属已基本可靠。对文件读写、简单 JSON、排序、校验等 basic 原子任务，
在 Planner 正常返回时已经有明显可用性。

它还不适合作为稳定的通用长程代理：全量 strict success 仅 21.1%，M/H/LH 分别只有 3/1/0 TP；Planner relay
会让 40% 全量样本在 RWKV 前归零；计划图 93.5% 为单节点 batch；本地断言编译覆盖不足又把大量确定性判断
交给 Reviewer。当前上限首先受**强模型调用可靠性 + 契约可执行性**限制，其次才是 RWKV state/操作能力。

## 下一轮应做的三项全局整改

1. **Planner 可靠性与预算**：预注册 Planner cap=1800–2000，使用真实 Full90 负载验证；为初始 Plan 增加
   可恢复的延迟重试/持久 pending 状态，避免一次双路 500 把 case 永久终止。Reviewer 维持现状，因为本轮
   110/110 返回成功。
2. **确定性契约编译**：把 numeric aggregate、nested exact JSON、source pointer copy、merge/preserve 编译成本地
   assertion；本地 contradiction 必须 veto Reviewer satisfied，减少重复纠错和 FP。
3. **更宽但仍有界的原子图**：Planner 明确输出独立 read/transform/verify 的真实依赖，scheduler 继续只执行
   deterministic ready set；目标是提升 multi-node batch 和 overlap case，而不是增加 GPT 过程上下文。

完成后仍以同一固定 Full90、同一 acceptance、同一 TP/FP/FN 和成本门复测；局部用例只用于定位，不作为晋级依据。
