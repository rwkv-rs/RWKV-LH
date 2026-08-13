# Round23 全 90 题跨层因果综合

## 1. 证据边界

本综合只连接已经冻结的四组逐题盲审、四组标准答案后复核、独立参考答案与 Round22/Round23
结果；不改写这些冻结材料。每个 case 的原始模型输入、raw 输出、协议转换、Controller 事件、Harness
结果、workspace revision 和外部验收定位仍以逐题文档及
`../Round23/blind_lifecycle_fact_index.json` 为准。

本文件不是关键词聚合。下面的归因由逐题回读后再跨 case 对齐，区分：

1. 最早可观察偏离；
2. 后续把局部偏离升级为全局错误的结构环节；
3. 即使修复结构仍必须由 RWKV 自己完成的语义决定。

Round23 冻结结果为 Strict `0/90`、Agent completed `0/90`、External `17/90`。17 个 External
正确 case 全部是假阴性；其余 73 个 case 至少缺一个真实 artifact、行为或生命周期条件。

## 2. 90 题最早断点矩阵

下表给每题指定一个**主要最早断点**。这不是说后续只有一个问题；重叠的放大环节在第 3 节列出。

| 主要最早断点 | Case |
| --- | --- |
| Goal 过度生成、固定 cardinality 或双事实源 | B11, B12, B18, B24, B29, M03, M06, M19, M20, H11, LH03, LH12 |
| 静态 Plan 的顺序、依赖、复合/抽象 node 或全图长度 | B01, B07, B09, B14, B15, B21, M08, M09, M10, H01, H02, H10, LH01, LH10, LH11 |
| 缺少 member/phase/collection 身份与增量展开 | B26, M01, M11, M17, M23, M26, M28, H05, H13, H14, LH02, LH05 |
| 缺少 typed negative outcome、分支或生命周期状态 | B23, M16, H08, H09, H16, H17, LH04, LH08, LH09 |
| RWKV 直接 action、计算、代码、schema、path 或 policy 错误 | B10, B25, M02, M04, M05, M07, M13, M15, M22, M25, M27, M29, H03, H12, H15, H18, LH06, LH07 |
| action effect 被过早提升为 Task 完成，或同目标 revision 被后写破坏 | B16, B22, B27, M12, M14, M21, M24, H06, H07 |
| production 正确但 proof/completion 链假阴性 | B02, B03, B04, B05, B06, B08, B13, B17, B19, B20, B28, M18, H04 |
| runtime/protocol/recovery 局部闭环错误 | B30, M30 |

矩阵恰好覆盖 90 题一次。它只用于定位首断点；例如 H06 的 writer-before-reader 首先是 Plan
排序问题，但最终不可恢复是同目标 revision 没有来源身份；LH09 首先缺 lifecycle replay node，之后又被十个
同义 reader 放大。

## 3. 从前向后的共同放大链

### 3.1 Goal：模型错误被不可变状态永久放大

- B12、M03、M06、M19、M20、H11、LH03、LH12 在 Goal 阶段因模型给出 6–9 个 criterion，
  固定 `max 5` 直接使 8 题零执行。这些题没有测到下游能力。
- B11、B18、B24、B29 证明 Goal projection 会复制 system wording、生成用户没有要求的条件，或和原始请求形成
  两个事实源。下游即使写对 artifact，也无法闭合被发明的 obligation。
- 放大环节是：自由 Goal 摘要 → immutable digest → Plan/Proof 全部服从该摘要。immutable 本身正确，错误在于
  未保存“原始请求中哪段文字支持哪个 criterion”的 provenance，也没有让 RWKV 在局部协议错误后只修字段。

结构结论：Goal 不能被 Controller 重写，也不能由规则替 RWKV 合并 criterion；需要 model-authored provenance、
typed protocol correction，以及在不改变语义的前提下允许 criterion 数量反映真实任务。

### 3.2 Plan：静态全图不是可执行因果图

- B01 的 verifier 因 priority 先跑，writer 永远未执行；B07/B09/B15/B21 把“选择、计算、验证”之类抽象或复合
  步骤当成单 action node；M08/M09/M10、H06 让 reader/producer 顺序反转。
- H02、LH11 的全图在执行前截断；M01 扩张到 40 task、M11 到 59 task，说明“先预测完整 workflow”把弱模型的
  一次局部错误复制到了整个 DAG。
- 当前 dependency 只表达“前置 Task completed”，不能表达 member、phase、revision、expected failure、alternate
  branch 或 lifecycle commit。因此图在语法上无环，语义上仍不是因果图。

结构结论：Plan 必须改成有界 causal frontier。每个 node 由 RWKV 明确声明 observable operation、subject/member、
effect target 和直接依赖；Controller 只检查声明的一致性，不生成 target、member 或答案。后续 frontier 只在最新状态
胶囊上展开，不能反复重放完整历史。

### 3.3 Action：两段式决定重复语义，action 成功又被误当任务成功

- M30 的 action-choice raw 已经同时包含合理 tool name 和完整 arguments，但第一阶段协议只允许 action type，
  有用语义被丢弃，第二次请求没有到 producer。H12 等题在 action type 与 arguments 两次决定之间发生漂移。
- B16/B27/B26、M17/M23/M26/M28、H13 证明一次 replace/mkdir/member action 的 observable success 被直接升级为
  “normalize all / create all / migrate all / finish phase”。
- 当前状态转换把 required action postconditions 通过后直接设置 Task `completed`；Task 的语义 postcondition 与 Goal
  evidence 并不是独立状态。

结构结论：action proposal 必须是 RWKV 一次性提交的原子 `{name, arguments}` 决定，或者在保留渐进披露时把第一阶段
语义承诺原样带入第二阶段且不能丢字段。更关键的是建立三层状态：`action_effect_observed`、
`task_postcondition_committed`、`goal_evidence_verified`。Controller 不得把第一层自动提升到第二或第三层。

### 3.4 Revision：后写不是进展，可能是回归

- B22、M12、M21 都存在较早的正确 revision，后续 whole-file writer 将它破坏；M21 从完整 records 退化为仅
  `record_count` 是最清晰证据。
- H06 writer 覆盖 source 后，后来的 reader 只能看到模型自己生成的值；M14 的两个 companion artifact 不属于同一
  committed revision；H07 的 stale whole writers 相互覆盖。
- action hash 和 artifact hash 能证明“写了什么”，不能证明该 revision 是 task/Goal 的有效进展。

结构结论：同一 subject/target 必须有 append-only revision lineage。最新字节、最新 RWKV-committed task revision、最新
Goal-proof revision是三个不同指针。Controller 不能选择“看起来最对”的旧 revision，更不能回滚或修改 RWKV 输出；只有
RWKV 提交 task postcondition或显式选择补偿 action 后，指针才前进。

### 3.5 Collection/phase：单成员成功不能代表全称完成

- M17 只迁移 core、M23 只创建一个 artifact、M28 只 copy 一个文件；H13 每 phase 只读首成员；LH02 因 step12
  identity 漂到 step13，最终只差一个 checkpoint。
- 当前 Task 没有稳定 member key、phase key、expected/observed member ledger。标题里的复数没有机器可追溯身份，
  后续 action 也无法证明自己仍操作相同成员。

结构结论：member/phase identity 必须由 RWKV 在 causal frontier 中显式提交并被 Controller 原样保存。集合完成只能由
全部已提交 member outcome 聚合，不能从一个 action success 推断；未知 fan-out 必须先 observation，再增量展开。

### 3.6 Negative outcome/lifecycle：失败目前只有“重试或阻断”

- B23、M16、H09、LH05 中 `not_found` 或 invalid JSON 是选择 fallback 的合法分支结果，却被当普通失败重试。
- H16/LH08 需要“verifier 按预期失败 → compensation → final pass”；当前 verifier 只允许 exit 0，阶段顺序也会漂移。
- H17/LH04/LH09 需要 post-effect crash、resume、duplicate replay、conflict observation 等 lifecycle event；把这些写成
  普通 artifact task 不能证明真实 lifecycle。

结构结论：action result 必须有 typed outcome，依赖边必须可引用 RWKV 预先声明的 outcome。Controller 只匹配真实返回类型
并调度模型已声明的分支，不能替 RWKV 选择 fallback、compensation 或重放参数。

### 3.7 Memory/proof：全历史不是更完整，而是因果污染

- B03、LH02、LH09 等在正确生产后被重复 reader、全部 task/artifact/history 展开推到 context overflow或 schema 漂移。
- 当前 working memory 按通用 relevance/evidence 打包；Goal obligation capsule同时携带 active task index、最近 24 个详细
  task、32 个 action observation、64 个 artifact、32 个 criterion evidence和 workspace manifest。它是 bounded history，
  不是 current-state projection。
- B02/B03/B05/B06/B08/B13/B17/B19/B28/M18/H04 的 artifact 正确但 0 CriterionEvidence，说明复杂 witness/operator
  协议增加了模型决策面，仍未建立独立 expected source。

结构结论：SQLite/event log继续 append-only且完整审计；模型输入改为确定性状态胶囊，只含 Goal digest及相关原文引用、
active task contract、直接依赖的最新 committed revision、当前 member/phase ledger、最新 material failure fingerprint和允许的
action contract。相同 observation digest 下不得重复 deterministic verifier/RWKV cross-check；变化后才重新运行。

## 4. 哪些仍是 RWKV 自身错误

结构整改不能掩盖以下能力缺口：B10/M02/H15 的代码错误；M07/M29 的 merge 错误；M13/H12 的算术错误；M22 的
policy application错误；M27 的拓扑排序错误；H03/H18 的path/schema错误；LH06/LH07/LH08 的source、配置和requested-state
hallucination。新的架构只能让它们更早得到真实、局部、可恢复的反馈，并防止同一错误扩散；不能由 Controller 计算正确值、
选择标准答案、改 action arguments、改 final artifact或用 acceptance筛选输出。

## 5. 代码落点与因果关系

| 当前落点 | 当前行为 | 对应缺陷 |
| --- | --- | --- |
| `rwkv_lh/model.py::plan` | 一次生成完整静态 DAG，要求初始 coverage | 长图截断、抽象/复合 node、全图错误复制 |
| `rwkv_lh/task_graph.py::ready_tasks` | completed dependency + priority 排序 | verifier/reader 可在 producer 前运行；无 outcome/member/revision edge |
| `rwkv_lh/model.py::_choose_action_type` + `propose_action` | action type 与 arguments 两次 RWKV 请求 | M30 语义丢弃、H12 action漂移、重复上下文 |
| `rwkv_lh/controller.py::_execute_task` | action required checks通过后直接 Task completed | partial effect、plural/member假完成、错误revision继续传播 |
| `rwkv_lh/memory.py::WorkingMemoryBuilder` | dependencies + generic relevant history | stale/self evidence混入、长链重复展开 |
| `rwkv_lh/controller.py::_goal_obligation_capsule` | bounded recent-history集合 | obligation reader扩张、不是current causal state |
| `rwkv_lh/controller.py::_retry_or_replan` | 失败只有 retry/reselect/replan | 合法negative outcome和分支不可表达 |

## 6. 整改顺序

### Round24：紧凑因果 Task 契约

先建立后续所有修复的状态主干：model-authored observable task contract、原子 action commitment、
`effect observed → task postcondition committed → Goal evidence`三层状态，以及只投影直接因果状态的 execution capsule。
这一轮不实现 collection 自动展开或 negative branch，避免同时改变调度语义。

### Round25：有界 causal frontier 与 member/phase ledger

把静态全图改为小批 frontier；unknown fan-out先观察再展开。member/phase身份、expected/observed成员和revision lineage
进入状态胶囊。集合聚合不产生语义答案，只聚合 RWKV 已提交的成员状态。

### Round26：typed outcome 与真实 lifecycle

增加 `success/not_found/invalid/conflict/nonzero/post_effect_unknown` 等运行时结果类型及 model-authored outcome edge；
支持 expected-fail、compensation、resume和duplicate replay的真实事件状态。

### Round27：Goal provenance 与 proof收敛

让每个 RWKV criterion绑定原始请求引用，取消固定五项造成的零执行；简化 Goal proof为独立source的typed claim，并使用
material observation digest抑制不变验证。不得把 artifact存在或task完成当作Goal完成。

## 7. 判定标准

- 紧凑性同时用 model request数、prompt token、capsule字段/字节、重复 observation digest和全历史引用数衡量；不能只看
  token下降。
- 正确性同时报告 External、Strict、Completed、FP/FN、first producer reachability、正确revision保留、member coverage、
  typed outcome branch和CriterionEvidence。
- 任一轮都必须保留 raw/normalized/model decision/Controller transition/Harness result/revision hash；hidden acceptance只允许
  冻结后离线评分。
- 结构门禁不得根据 case ID、答案内容、External分数或参数正确性改变行为；Controller不得增删改查 RWKV 的语义 payload
  或最终输出。
