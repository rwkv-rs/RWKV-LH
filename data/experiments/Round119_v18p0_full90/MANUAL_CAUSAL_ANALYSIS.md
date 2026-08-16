# Round119 v18-P0 Full90 人工因果分析

日期：2026-08-16

状态：运行后人工分析；冻结 manifest 复核 48/48 一致，运行中未改源码/数据/口径。
预注册协议：`data/experiments/Round119_V18P0_FACT_INTEGRITY_PROTOCOL.md`。

## 一、结论与判定

**判定：KEEP。** Round119 v18-P0 的三项事实完整性机制全部按假设生效，Full90 从
Round118 的 Strict `25/90` 恢复到 **`30/90`**，FN 从 2 降到 **0**，且 90/90 全部落入
终态（0 个 `running`、0 个空 Final）。预注册 KEEP 红线全部满足：

| 红线 | 要求 | 实际 | 判定 |
| --- | --- | --- | --- |
| Strict | >= 25 | 30 | 通过 |
| Round46 TP 保留 | >= 18/31 | 21/31 | 通过 |
| FN | <= 4 | 0 | 通过 |
| Final 完整性 | 90/90 非空或 failed+terminal | 90/90 非空 | 通过 |
| terminal running | 0 | 0 | 通过 |

尚未超过 Round46 的 31/90，未达成整体目标；FP 从 35 升至 36、prompt tokens 从
16.88M 升至 18.64M。剩余失败高度集中在两个未处理缺口：**行动意图/未完成义务缺失**
与**成功观察循环**——即预注册拆分中留给 Round120 的缺陷 1+2。

## 二、固定指标块

| 指标 | Round46 | Round118 v17 | **Round119 v18-P0** |
| --- | ---: | ---: | ---: |
| Strict / External / Agent | 31 / 32 / 55 | 25 / 27 / 60 | **30 / 30 / 66** |
| FP / FN | 24 / 1 | 35 / 2 | **36 / 0** |
| Basic | 24 (FP1/FN0) | 19 (FP9/FN1) | **21 (FP9/FN0)** |
| Medium | 5 (FP12/FN0) | 5 (FP15/FN1) | **6 (FP17/FN0)** |
| Hard(H+LH) | 2 (FP11/FN1) | 1 (FP11/FN0) | **3 (FP10/FN0)** |
| Round46 TP 保留 | — | 18/31 | **21/31** |
| 上一轮 TP 保留 | — | — | **24/25** |
| prompt tokens | 3.50M | 16.88M | **18.64M** |
| 均值/请求 | ~2160 | ~8650 | **9047** |
| requests / actions / rejects | 1622/—/— | 1952/1557/299 | **2060/1698/264** |
| >=20 action 用例 | — | 18 | **17** |
| 最大相同观察重复 | — | —（无计数） | **194 (LH02)** |
| rollovers | — | 129 | **168** |
| transport failures | — | —（逸出） | **0** |
| status running / 空 Final | — | 3 / 3 | **0 / 0** |

LH10 是全部历史版本中 long-horizon 组的第一个 Strict PASS（Round46 的 LH04 属
crash-recovery 骨架题）。

## 三、三个预注册假设的逐一检验

### H1 观察指纹与预算重绑：成立

- M24：Round118 中 50 个 failure key 全部 count=1、103 个 Action 后中断；本轮同一
  测试失败在第 5 次识别为相同事实，15 个 Action 终止（`identical_failure_budget_
  exhausted`），Final 如实报告测试仍失败。类别 TN 不变，成本 103→15。
- H11：153→19 Actions，同理。新触发预算终止的还有 H07/H15/LH12/M09，全部是
  Round118 中的同类循环 TN；没有任何 Round118 TP 被预算终止（B10 的 4 次近似失败
  各不相同，未触发，仍 TP）。
- 成功观察计数已进入模型可见 Observation（`identical_result_count`），LH02 中值达
  194——事实可见但模型在 rollover 上下文中仍持续重复，证明**计数本身不足以打破
  成功循环**（见 §五）。

### H2 终止事务：成立

- 90/90 全部有 terminal causal event；`status=running` 与空 Final 均为 0（Round118
  为 3/3）。本轮无真实 endpoint 中断（transport failures = 0），M16/M17/M21 的历史
  逸出路径由回归测试覆盖（模拟 OutcomeUnknown → `run_failed(model_transport_
  unavailable)`）。
- 副作用：M16 从"挂死 TN"变为"完成但 schema 错误的 FP"——终态保障使过松的完成
  边界显形，这是 Round120 的靶点而非本轮回归。

### H3 通用能力补全：2/3 成立

- B08 FN→TP：模型本轮用 `check_command+sha256sum` 独立核对 digest（甚至未用新
  `file_digest`），12 次 `verify_checksum` 未注册循环消失。
- M30 FN→TP：`timeout_ms→timeout` 透明转换生效（7 请求 0 拒绝），业务产物本就正确。
- M28 仍 TN：`move_file` 已在 catalog，模型 85 个 Action 全部是 list/read（同一文件
  最多读 40 次），从未产生任何 mutation 意图，Final 声称"状态已符合要求"。能力缺口
  已补，剩余是意图/义务缺口（Round120）。

## 四、flip 详析（相对 Round118，11 题变化）

| 题目 | 118→119 | 反向首因 |
| --- | --- | --- |
| B08 | FN→TP | 接口循环消失；模型自选 sha256sum 独立核对。 |
| M30 | FN→TP | timeout_ms 透明转换；业务链路原本正确。 |
| B12 | TN→TP | 本轮直接 read_file→write_json，未再退化为对文本 read_json。 |
| H10 | TN→TP | 完整链：读 CSV/policy/verifier 源码→写 release→运行 verifier 通过。 |
| B14 | FP→TP | 组合字节本轮精确（R118 为多余空行）；同题波动，无系统变量可归因。 |
| LH10 | FP→TP | manifest 本轮只含要求的两文件 digest（R118 错纳测试文件）。 |
| LH02 | FP→TN | R118 提前宣布完成（FP）；本轮陷入 194 次相同读取直至 transition 预算，
Final 如实描述未完成。质量仍失败，但不再谎报。 |
| B29 | TP→FP | manifest 被写成 JSON 对象而非要求的单行文本；模型格式选择错误
（catalog 变化改变了采样轨迹，属单轮翻转噪声+模型错误）。 |
| M06 | TN→FP | R118 中断于 check_command 误用；本轮读全三个资产后只写 manifest、
未复制文件即宣布完成。前进到了真实缺陷：无义务追踪。 |
| M16 | TN→FP | R118 失去集合边界后挂死；本轮 01–05 覆盖正确、fallback 正确，
recovered.json 却用 id→item map 而非要求 schema。从挂死推进到近失。 |
| H18 | TN→FP | R118 只读不写；本轮 products.json/REPORT.md 全部正确（与 verifier
期望一致），读 digests.json 得 not_found 后仍宣布三产物齐备。2/3 完成后的义务丢失。 |

其余 79 题类别与失败检查签名与 Round118 完全一致（逐题机械比对通过，表内 `=`），
其中 24/25 个 Round118 TP 保留。R118 的首因分析对这 79 题继续有效；本轮未出现新的
失败模式。

## 五、剩余共同缺口（Round120 的直接证据）

1. **成功循环无界**：LH02 相同 read 194 次（195 Actions、31 rollovers、transition
   预算耗尽）、M21 相同 write_json 94 次、LH03 137、M17 51、M28 40、H04 29（虽 TP）。
   `identical_result_count` 已可见但不改变行为：rollover 后模型只看到"最近 12 条近同
   Action"的尾部，重复事实被反复重演。失败预算的对偶（成功侧）不存在；prompt tokens
   因此不降反升（16.88M→18.64M）。
2. **义务/意图缺失**：M06（读了不复制却称已复制）、H18（2/3 产物后放弃第三个）、
   M28（85 个只读 Action 后宣布无需改动）、M16（覆盖正确但输出 schema 错）。模型
   从不声明"本步要达成什么、看到什么才算完"，多输出任务的剩余义务在上下文滚动后
   消失。
3. 其余 FP 仍是 Round118 §4 归因的模型语义/格式错误（B04/B05/B11/B16/B17/B18/
   B22/B24/M03/M08/M13/M14/M15/M19/M22/M23/M25/M26/M27/M29/H01/H03/H06/H08/
   LH01/LH04/LH06/LH09/M04/M18），签名逐题复核一致。
4. 评分口径漂移不变：M10（`replan_applied`）、H09（`action_returned`）唯一失败项仍是
   旧架构事件名；LH02/LH11 的 `event_min_count(attempt_started)` 同类但两题另有真实
   产物失败。architecture-neutral v2 验收仍应另行版本化，与在线变量分离。

## 六、Round120 单一变量（按预注册拆分执行）

**Causal Step Contract + Progress Projection**（缺陷 1+2，一个缺口的两面）：

1. 每次普通调用 `{"step":{"objective","done_when"},"function","params"}` 同次生成；
   Controller 只登记回显，不 gate。
2. `_assignment`/`_rollover_if_needed` 改为从全量 causal ledger 确定性生成
   `CausalProgressProjection`：per-path 首次/最新观察与 mutation 后是否再观察、每个
   成功 list 的成员覆盖事实、每个 fingerprint 的 last result+repeat count（折叠而非
   重演尾部 12 条）、当前 step 原文、最后一次协议拒绝。
3. 不加 reviewer/Task DAG/成功预算（若 step+projection 后成功循环仍在，成功侧预算作
   Round121 独立变量）。

预期直接受益：LH02/LH03/M17/M21/M28/H12/H13/H14（循环）、M06/H18/M16/LH02
（义务）；非回归重点：本轮 30 个 TP、预算终止行为、B10/B26/H04 多步链。

## 七、审计材料

- 官方输出：本目录 `REPORT.md`、`results.json`、`RUN_PROTOCOL.json`、90 个 case。
- 冻结 manifest：`data/experiments/Round119_v18p0_source_manifest.json`（运行后复核
  48/48 一致，`--check` 只读模式）。
- 离线门：107 passed（含 8 个 Round119 新回归）、compileall、`git diff --check`、
  catalog 90/90。
- 分析脚本（只读）：`temp/analyze_round119_full90.py`、`temp/round119_case_digest.py`；
  逐题 flip 叙述均由原始 audit/causal_ledger 逐条复核，非分数自动生成。
