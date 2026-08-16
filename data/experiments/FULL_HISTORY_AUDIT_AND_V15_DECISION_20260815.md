# RWKV-LH 全历史复核与 v15 下一步决策

日期：2026-08-15

状态：历史审计与预注册设计；没有修改运行时代码，没有宣称问题已解决。

## 一、结论先行

当前不应继续围绕单题补 completion gate、reviewer、frontier role、证据类型或
recovery 分支。历史最高完整结果仍是 Round46 上传基线：Strict `31/90`、
External `32/90`、Agent completed `55/90`、FP `24`、FN `1`。最后一次完整
E2E-90 是 Round101：Strict `12/90`、External `21/90`、Agent `32/90`、
FP `20`、FN `9`。之后只有更小的 Basic30、14 题、单题和两题 canary，没有
新的完整 90 题证据可以推翻这个排序。

下一项优化应是一个明确的 Task 边界消融：在当前单一 v14 代码脊柱上重建
Round46 已证实的“局部 Task → 一次完整 Action → 真实 Observation →
decision-last Task commit”，同时保留当前架构已经做对的 verbatim Goal、
direct registered call、ModelSession 审计、workset 数据结构、uv Python 环境、
workspace scope 和 raw Final。

具体而言：删除在线 Task proposal 中由 RWKV 预猜的
`evidence_kind/evidence_subject`，普通 Task revision 最多执行一个成功 Harness
Action；runtime 从实际 ActionResult 机械登记 operation、target、attempt、artifact
version 和 observation refs。Task 完成仍由 RWKV 在真实 observation 之后判断，
Controller 不计算业务答案。集合任务随后通过同一原子脊柱上的 workset/member
ledger 扩展，不恢复旧 proof/witness 多角色系统。

## 二、审计范围和可复核性

### 2.1 覆盖材料

- `data/experiments/` 共 `2249` 个文件。
- `329` 份 `REPORT.md`、`311` 份 `results.json`、`168` 份
  `RUN_PROTOCOL.json`、`164` 份源码 manifest、`68` 份人工因果分析。
- 项目根目录有 `111` 份 Round 级预注册协议，覆盖 Round4–115；Round0–3
  由参考项目分析、架构消融记录和全量因果分析补齐。
- Git 正式 checkpoint 共 12 个，最后三个质量节点是 Round2 `b5aa2b2`、
  Round24 `fef3a3b`、Round46 `14d864d`。Round47–115 主要存在于未提交工作树
  和实验 manifest 中，因此不能只用 Git log 代替实验历史。
- 全量比较只使用相同 RWKV-E2E-90：Basic/Medium/Hard 各 30；小 canary
  只用于定位链路，不用于宣布整体架构更优。

临时索引脚本为
`temp/analyze_full_history_metrics_20260815.py`。它只读取报告和结果，不写实验
数据，不自动生成因果结论。

### 2.2 数据完整性

当前 E2E-90 的六个可见/隐藏 catalog 摘要和冻结 manifest 完全一致；Codex
参考答案摘要仍为
`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`。
因此 Round46、Round50–53、Round80/81/85、Round101 的主指标可直接比较。

发现一个必须在下一轮前处理的口径缺口：
`benchmarks/architecture_regression/lh_control_30/tasks.json` 已从登记的
`0606877c...` 改为 `a1449dc3...`，修改了 LH-M04 的协议语义，但仍标
`lh-control-30.v1`。历史 LH-Control 结果不能与当前文件混算。应先把当前版本
登记为新 dataset version，或者明确恢复并使用冻结副本
`data/datasets/rwkv_lh_e2e_v1/lh_control_30.tasks.json`。

当前源码的 controller/model/model_io/model_session/schema/task_graph/harness
摘要与 Round115 manifest 一致。当前离线回归为 `112 passed`，E2E catalog
校验为 `90/90 catalog_valid`。这些只证明实现自洽，不证明在线质量达到门槛。

## 三、完整历史轨迹

### 3.1 Round 前消融：正确方向最早已经出现

固定 Basic-10 的早期消融结果：

| 方案 | Strict | External | 请求数 | 结论 |
| --- | ---: | ---: | ---: | --- |
| baseline | 1/10 | 3/10 | 337 | Task/Goal 作用域混合 |
| 去 mandatory cross-check | 5/10 | 6/10 | 194 | 减少错误拒绝，但不是完整结构 |
| 去 failure-analysis | 3/10 | 5/10 | 174 | 元分析开销大，但不能只删除 |
| minimal validation+recovery | 4/10 | 5/10 | 224 | 两项删除不能简单叠加 |
| **Task-local validation** | **8/10** | **8/10** | 359 | 第一个明确有效的状态边界 |
| prompt 分离 progress/satisfaction | 3/10 | 5/10 | 191 | 自由 JSON 不能稳定维护状态不变量 |

这已经说明：收益来自把 RWKV 的当前判断限制在当前 Task 和真实 observation，
不是增加一个更聪明的全局 judge。

### 3.2 Round1–26：接口和 proof 系统扩大，但完成链长期为零

完整 90 题的主线如下：

| 轮次 | Strict | External | Agent | 核心变化/首因 |
| --- | ---: | ---: | ---: | --- |
| R1 | 5 | 7 | 11 | 大量 Task/function 外壳和 Goal coverage gate |
| R2 | 7 | 8 | 19 | 透明展开完整 Task 外壳；格式收益伴随 FP 上升 |
| R3 | 2 | 4 | 11 | unchanged gate 未实际产生收益 |
| R4–R23 | **全部 0** | 最高 24 | 通常 0 | criterion proof、assertion、witness、obligation、provenance 生命周期持续增加；正确 workspace 大量成为 FN |
| R25 | 0 | 0 | 0 | Goal quote、v3 registry 和宽 Task schema 在执行前阻断 |
| R26 | 0 | 0 | 0 | 89/90 在 Task 物化前失败；冗余 edges/dependencies/expected/verifier 字段相互污染 |

R4–22 的 External 一度上升到 24，但 Strict 始终为 0。这不是 Agent 质量
提升，而是“模型有时已经把 workspace 做对，证明/完成系统却不允许完成”。
R25/26 又证明宽规划接口可以让全部下游能力不可达。

### 3.3 Round27–46：缩小协议后稳定爬升到历史最佳

| 轮次 | 样本 | Strict | 核心变化 |
| --- | ---: | ---: | --- |
| R27–31 | B02 单题 | 0 | criterion/provenance commit 仍不稳定 |
| R32 | B02 单题 | 1/1 | 紧凑 causal replan 首次接通 |
| R33 | Basic30 | 5 | Goal frontier |
| R35 | Basic30 | 10 | phase-local compact capsule |
| R36 | Basic30 | 14 | `tool+args` 透明格式层 |
| R39 | Basic30 | 14 | 已选单工具 schema correction |
| R40 | Basic30 | 14 | criterion-local Goal 判断，FN 仍高 |
| R41 | Basic30 | 17 | canonical evidence roles |
| R42 | 10 题 | 0 | focused comparison 失败并回退 |
| R43 | 10 题 | 1 | focused pass audit 仍退化 |
| R44 | 10 题 | 4 | observation view |
| R45 | 10 题 | 7 | RWKV owns Task verification |
| R46 Basic | 30 | 23 | reason-first/decision-last + 精确常见格式归一 |
| **R46 full** | **90** | **31** | Basic 24、Medium 5、Hard 2 |

Round46 不是在 R4–22 的 proof 系统上继续叠加得到的。真正的增长发生在协议
重新缩为五字段局部 Task、完整 direct action、phase-local evidence 和动作后
Task commit 之后。

### 3.4 Round47–53：在最佳基线上增加元边界，完整分数立即下降

| 轮次 | Strict | External | Agent | FP | FN | 变量 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| R46 | 31 | 32 | 55 | 24 | 1 | 局部 Task、direct action、decision-last |
| R50 | 6 | 11 | 14 | 8 | 5 | 两阶段 tool name→arguments |
| R51 | 17 | 22 | 39 | 22 | 5 | 只修 `tool_name→name` 即恢复 11 题 |
| R52 | 3 | 3 | 17 | 14 | 0 | 强制整批单层 frontier |
| R53 | 23 | 24 | 43 | 20 | 1 | 同一 RWKV pre-action reviewer |

R53 比 R46 少 8 个 Strict，只减少 4 个 FP。reviewer 没有新增事实，只增加一个
弱模型必须正确通过的语义边界。

### 3.5 Round54–77：围绕症状迭代，canary 长期低于旧基线

- R54 让 RWKV 先判断 Task 是否 atomic，`0/15`；单题产生数百递归 Task，
  没有执行动作。
- R55 允许 Task 内多 action，`3/15`；H12 顺序读到 7 个成员后自由文本却声称
  15 个全部完成，证明 collection 需要 ledger，而不是更长 history。
- R56–60 反复拆分 evidence source selection、semantic adjudication、reselection、
  reason-first 和 Task handoff，Strict 为 `3,2,1,1,4/15`。FP 有时降到 0，
  但 FN 和正确动作被阻断增加。
- R61–67 的 Task effect scope、continuation、single-owner、direct action、
  collection/recovery 仍只有 `1–4/15`。
- R68–71 的 quality-first review pipeline、typed echo、fixed review tools、
  compact boundaries 为 `0,0,1,0/15`；R68 有 14/15 在 run 创建前失败。
- R72 为 `2/15`，R73 为 `1/14`；R73 的 LH02 在人工中断时已有 494 请求、
  88 Tasks、112 Attempts 和 2.1GB SQLite，显示状态累积已经成为一等质量问题。
- R74–77 short7 为 `2,1,0,0/7`。其中 R75 明确观察到完整 action 已经在第一次
  RWKV 输出里，却因 action identity/arguments 被拆成两次请求而丢失；R77 又确认
  collection Task 与单成员 action 不同构。

### 3.6 Round78–101：统一 lane 重写修复接口，但完整分布仍未恢复

- R78 清理格式、Task/Goal evidence、workset 和 recovery；short7 最高 `2/7`。
- R79 引入单一 G1i `{function,params}`、ModelSession lane/checkpoint、workset、
  chunk/reduce，并删除旧 memory/proof/tool-protocol 多角色路径；short7 仍未过门。
- R80/R81 同源码完整 90 均为 `0/90`、External `10/90`。71/90 的最终断点
  是 direct call 与 selector/params 协议不一致；相同 aggregate 的两轮只有
  8/12 external-pass case 重叠，说明一次跑分也不稳定。
- R83–92 围绕四题把 canary 从 0 推到 `3/4`。
- R93–99 主要围绕 B02 单题修 completion、Goal correction、frontier projection、
  task id、evidence subject 和 tool applicability。
- R100 达到 `4/4`；R101 同四题全部保持 TP，但完整 90 只有 `12/90`。

这证明微型 canary 只确认局部路径已接通，不能替代全分布架构验证。

### 3.7 Round102–115：样本继续缩小，未产生新的整体最佳证据

- R102 `0/10`，R103 `2/5`。
- R104–110 逐步缩至三题、两题、单题；多数为 0。结构性 replacement amplification
  被修掉，但实际业务正确率没有随请求下降而提高。
- R109 单题完成但 external fail；R110 新增 frontier role 后阻止该 FP。
- R112 Basic30 只有 `6/30`，相对 R101 同 Basic30 的 `10/30` 更差，且 FP
  从 6 增到 9。frontier role 既制造 FN，又未阻止错误 deliverable，已被否证。
- R113 移除 role 并强调端到端 Task，在定向 14 题得到 `4/14`；同 14 题
  Round46 为 `8/14`。
- R114/R115 两题只证明 uv Python 环境从接口失败修复到真实执行。R115 B30
  Strict pass；B10 获得精确 pytest 失败后仍重复同一错误算法，41 请求、25 Attempts。

当前没有 Round115 源码上的 full90。最接近的完整证据仍是 Round101 的 `12/90`；
不能把 R115 的 `1/2` 外推成架构提升。

## 四、Round46 最佳实现到底做对了什么

Round46 commit：`14d864d71bf670b479a33f4fdb63b4772b69d3c8`。

### 4.1 五字段局部 Task

在线 Task proposal 只有：

```text
local_id, title, description, dependencies, postcondition
```

prompt 明确要求一个 Task 是一个 immediate semantic step；若具体输入依赖尚未
观察的结果，只先创建读取/列目录 Task，真实 output 可见后再扩展下一 frontier。
它不要求规划时猜 evidence class、subject、verifier、expected outcome、priority、
retry policy 或 action。

### 4.2 一次直接、完整 Action

RWKV 在一个调用中同时提交工具名和全部参数。若参数 schema 错，只在固定工具的
单 schema 下纠正，不重新做 selector，也不让 reviewer 改选工具。Round50/51 的
对照证明这不是小实现细节，而是弱模型能力的一部分。

### 4.3 真实 Observation 后才提交 Task

Harness 执行动作、记录原始 result、deterministic effect check、artifact 和 post-action
snapshot；随后 RWKV 只判断当前 Task postcondition。Round45/46 的 reason-first、
decision-last 提示让 RWKV 把完整 read/list 数据当作应由自己判断的证据，消除了
大量“还需要另一个 verifier”的 FN。

### 4.4 phase-local 上下文

`WorkingMemoryBuilder` 将 action、Task validation、recovery 和 Goal evidence 分开。
Task validation 只看当前 Task、显式 dependency、当前 observation 和 compact failure；
没有把整套历史 catalog、review 对象和 recovery 状态反复塞进同一个在线 transcript。

### 4.5 它没有做对的部分

- Round46 有 24 个 FP，几乎都在 medium/hard；自产值写入后再读回，不构成独立
  语义正确性证明。
- collection、动态 fan-out、条件分支和 Goal coverage 仍弱。
- Goal criteria、proof/witness 旧模块本身复杂，不能整体恢复。
- 没有真实 native RWKV recurrent-state API；最佳行为来自紧凑结构化状态投影，
  不是服务端 state handle。

因此目标是重建行为不变量，不是 checkout Round46 后停止。

## 五、当前实现相对最佳实现的关键退化

| 边界 | Round46 | 当前 Round115 源码 |
| --- | --- | --- |
| Goal authority | 模型归一 Goal，可能发明 criteria | verbatim request；当前优点，应保留 |
| Task proposal | 5 个局部字段 | 6 字段，新增 plan-time `evidence_kind/evidence_subject` |
| Task 粒度 | immediate semantic step；正常一次 Action | prompt 偏好一个 end-to-end Task；最多 32 个成功 Action |
| Action | direct tool+arguments | direct registered call；当前优点，应保留 |
| 完成 | 动作后 reason-first Task commit | `lh_task_done` 还要通过 evidence class/subject、独立观察等结构 gate |
| 状态 | phase-local compact projection | lane transcript prompt replay；没有 native recurrent state |
| collection | 不足 | workset/member schema 已有，应保留后重接 |
| runtime | 旧 Python/scope 基础 | uv Python、bubblewrap、scope、raw Final 更完整，应保留 |

当前 `_TASK_SCHEMA` 要求 RWKV 在未执行前为每个 Task 选择 evidence class 和精确
subject；`TaskNode` 又同时持有 effect status、commit status、member status、action、
criteria、revisions 等大量运行时字段。Controller 的普通 Task lane可执行最多 32 个
成功动作，同时静态 DAG 仍存在。这形成两个推进器：Task DAG 和 Task 内 mini-agent。

量化成本：

| 指标 | Round46 | Round101 | 变化 |
| --- | ---: | ---: | ---: |
| Strict | 31 | 12 | -19 |
| 模型请求 | 1622 | 2167 | 1.34x |
| Tasks | 480 | 298 | 0.62x |
| Attempts | 474 | 818 | 1.73x |
| 输入 token | 3.50M | 13.03M | 3.72x |
| 平均输入/请求 | 约 2160 | 6013 | 2.78x |

Task 数下降而 Attempt 和 prompt token 大幅上升，说明工作没有消失，而是从可见 DAG
转移到长 Task lane/recovery transcript。Round101 的 12 个 TP 只用 139 请求；9 个
FN 用 405，20 个 FP 用 503，49 个 TN 用 1120。额外计算主要消耗在失败放大，不在
正确任务上。

## 六、全数据集共同根因和影响范围

### 6.1 Task DAG 与 Task 内 Agent loop 双重推进

直接证据：B05/B10/B12 的第一个 Task 已完成整个 Goal，静态后续 Task 又失败；
B25 的验证 Task 重做全链并写坏正确结果；B06/B13/B14 只是重复写碰巧没有出错。
影响所有普通 read→transform→write→verify、代码修复和多文件任务。

### 6.2 plan-time evidence 猜测成为不可修订契约

直接证据：B15/B19/B20/B26、M01/M05/M11/M25 的真实正确观察与预先声明的
evidence kind/subject 不一致，Task 永远不能 ready。正确 ActionResult 已存在，
系统却让规划阶段的一次元分类比事实更权威。

### 6.3 collection 进度只靠自由文本就会提前完成

直接证据：M01/M06/M18、H02/H12/H13、LH03/LH05/LH11；Round55 H12 实际只读
7/15 却声称全读完。影响“大项目逐文件读取/总结”的目标场景。正确解法是显式
member ledger，不是递归 subagent 或更长 prompt。

### 6.4 结构 gate 同时制造 FP 和 FN

Round46→101：FP 仅 `24→20`，FN `1→9`，Strict `31→12`。安全阻断本身不能
作为质量提升。每个 gate 必须报告保留多少旧 TP、减少多少 FP、增加多少 FN。

### 6.5 prompt replay 不等于 RWKV 原生状态

当前 `ModelSession.transport="prompt_replay"`；`NativeRWKVModelSession` 明确拒绝
构造，因为后端没有 create/resume/fork/commit/rollback/export/import API。当前 lane
checkpoint 是可审计 transcript 状态，不是 recurrent tensor state。优化必须先减少
每个因果边界的在线状态；不能把“统一 lane”本身当成已经使用了 RWKV state 优势。

### 6.6 仍然存在真实模型语义错误

B11 的文本转换、B15 的 JSON 顶层、B18 的算术、B22 的空行、B10 的 slug 算法等
确实来自 RWKV。架构只能确保输入、实际失败和当前目标清晰可见，并要求 materially
changed correction；不能由 Controller 改答案。先移除系统放大器，才能测量剩余模型
上限。

## 七、下一步唯一候选：v15 Atomic Causal Task Spine

这是一个 Task contract 边界消融，不恢复旧多角色实现。

### 7.1 在线 Task proposal

唯一字段：

```text
key, objective, done_when, after
```

- 普通 Task 描述一个局部因果推进，其正常成功路径对应一次完整 Harness Action。
- 不能在一个普通 Task 中同时要求独立的 read+write+verify；这些由有依赖的局部
  Tasks 表达。
- 未观察到 collection/path/branch outcome 前，不规划依赖这些未知值的后续 Task。
- 删除模型生成的 `evidence_kind/evidence_subject`。旧 checkpoint 只允许离线迁移，
  不保留两套在线协议。

### 7.2 普通 Task revision 生命周期

1. RWKV 从当前 direct action catalog 一次提交完整 operation+arguments。
2. Harness 执行并记录 exact ActionResult。
3. Runtime 机械登记 attempt ref、operation、显式 target、outcome、artifact/hash/version、
   stdout/stderr、cursor/EOF 和 effect checks；不判断自然语言 Goal。
4. 同一 RWKV Task lane在 observation 后提交 reason-first `complete|repair`。
5. `complete` 提交当前 Task revision；`repair` 回到 Goal lane生成 replacement/reopen。
6. 一个普通 Task revision 不在成功 observation 后继续第二个独立 Action。协议格式
   拒绝不算 Action，也不能触发完整语义重采样后替换原决定。
7. 分页读取的下一 cursor、条件失败后的新步骤、下一 producer/verifier 由下一局部
   Task/revision承担。

### 7.3 保留的当前能力

- verbatim immutable user request；
- 单一 `ActionDefinition` registry 和 direct registered call；
- `ModelSession` checkpoint/rollback/audit，但明确标注 prompt replay；
- raw/normalized payload 和 Final byte preservation；
- uv Python、bubblewrap、`shell=False`、workspace scope；
- tokenizer byte cursor、chunk/reduce 基础；
- 只搬运显式值的透明格式转换。

### 7.4 P1：同构 workset/member ledger

普通 Basic 基线通过后再接 collection：

- RWKV 显式声明 member id/source/target 和 sealed；
- 每个 member 使用同一“一次 Action→Observation→commit”脊柱；
- runtime 只维护 pending/attempted/observed/produced/verified 和 artifact version；
- reduce 只有在 sealed 且无 pending member 时才可由 RWKV执行；
- 不创建子 Agent，不由 Controller 生成摘要、值、路径或答案。

### 7.5 v15.1 候选：no-progress 指纹（不混入 v15-A）

从全 workspace digest 改为：Task lineage + operation/arguments + 目标 artifact hash +
最近 verifier fingerprint。cache、pytest 临时文件或无关 workspace 变化不得刷新同一
producer 的预算；supersede 链共享预算。transient/no-side-effect 失败在固定 retry
budget 内允许同动作重试。该项有独立因果变量，只有 v15-A Basic30 完成后才能另行
预注册；除兼容新 Task 生命周期所必需的机械调整外，v15-A 不改变现行 recovery
fingerprint 和预算策略。

### 7.6 v15-A 的变量边界与 artifact 事实

v15-A 只包含一个不可分割的 Task 生命周期变量：删除 plan-time evidence 猜测、把
普通 Task revision 限定为最多一次成功 Action，并把语义完成决定移动到真实
Observation 之后。它不同时新增 reviewer、Task role、workset 流程或 recovery
策略。

一次成功 Action 之后选择 `repair` 不撤销已经发生的副作用，也不丢弃 ActionResult。
runtime 必须保留该 attempt、Observation 和 artifact revision，Goal lane只能据此产生
后继或替代 Task。后续 mutation 产生新的 artifact revision；旧完成证据不得在没有
重新观察最新 revision 时继续作为当前事实。Controller 不从 objective/done_when 推断
Task 是“只读”“producer”或“verifier”，也不据此禁止模型选择某个业务 Action。

## 八、预注册验证顺序

### 8.1 先修评价登记

1. 冻结 v15 source manifest、dirty diff 和当前 E2E-90 hashes。
2. LH-Control 已分版本：历史对照使用冻结 `lh-control-30.v1`、摘要
   `060687...`；当前契约回归使用 `data/datasets/rwkv_lh_control_30_v2/tasks.json`，
   版本 `lh-control-30.v2`、摘要 `3a98077f...`。两者不得聚合或相互覆盖。
3. 固定模型、endpoint、temperature `0.05`、top-p `1.0`、top-k `0`、并发、
   transition budget、timeout 和 runtime image。
4. 固定相似度 `utf8-byte-ngram-cosine.v1`、`n=5`、near-stable `0.95`；不在结果
   出来后改阈值。缺失 expected artifact 的单项相似度固定记为 `0`，case 和全组聚合
   规则写入 RUN_PROTOCOL；External/Strict 仍为主指标，相似度只作同版本产物比较。
5. 固定一次正式主运行；主运行过门后用完全相同配置做一次确认运行。两次均报告且
   不选择最好结果。只有可审计的 endpoint 中断、服务重启或运行器故障允许作废；
   模型协议错误、超时、blocked 和错误答案均属于有效结果。候选只有在主运行与确认
   运行都不违反核心非回归门槛时才可进入下一阶段。

### 8.2 阶段 A：Basic30，不再跑单题优化

门槛：

- Strict `>=24/30`；
- FP `<=1`、FN `<=1`；
- Round46 Basic TP 保留率 `>=23/24`；
- artifact byte-5gram mean 不低于 Round46 Basic 的 `0.984508565952`；
- B05/B10/B12 不得因冗余后续 Task阻塞；
- B15/B19/B20/B26 不得因 plan-time evidence contract阻塞；
- B04/B25 若后续 mutation 产生新 artifact revision，系统不得继续沿用 mutation 前的
  完成证据；不得通过 Controller 推断“只读/验证职责”来禁止业务 Action；
- 每题报告首次偏离和 prompt token，不以请求数下降代替质量。

任何一项失败即回退 v15，不在失败架构上继续叠加 reviewer/role/gate。

### 8.3 阶段 B：collection/medium-hard 固定组

固定：M01、M06、M11、M16、M18、H02、H05、H12、H13、H14、LH03、LH05、
LH11，并用 B29/B30 作成功对照。检查 member completeness、base directory、sealed
barrier、artifact version、reduce 输入闭包和 supersede budget。本阶段不允许为单 case
新增规则。

### 8.4 阶段 C：完整 E2E-90

只有 A/B 通过才运行。替换 Round46 的最低门槛：

- Strict `>31/90`；
- FP `<=24` 且 FN `<=1`；
- Basic `>=24`，Medium `>5`，Hard `>2`；
- 全量 mean artifact similarity 不低于 `0.861638909388`；
- prompt token 总量和每请求均值单独报告；
- 全 offline、版本化 LH-Control、边界、异常、crash/recovery、raw Final 回归通过；
- 90/90 逐题首因复核。

## 九、停止规则

- R100 的 4/4、R115 的 1/2 不能再被描述成整体架构提升。
- 同一 RWKV reviewer/judge、frontier role、plan-time evidence class 不再作为下一个
  增量补丁。
- Controller 不从 Task 文本推断工具、成员、expected、业务字段或答案。
- 格式转换不能在语义字段缺失/冲突时补值，也不能靠第二次语义采样覆盖第一次决定。
- 在真实 native state API 出现前，所有 state 结论必须写作 prompt-replay state；不得
  宣称已经利用 recurrent-state fork/commit。

## 十、最终判断

项目并非“模型越来越不会做”，而是系统逐轮增加了模型必须正确完成的元判断，同时
把真实工作压进更长的 Task/recovery transcript。Round46 和早期 Task-local 消融已经
给出同一方向的正证据；Round50、52–77、80/81、112 又给出多次反证。

所以，下一步不是继续修 B10，也不是再跑一个更小 canary，而是只做 v15 Atomic
Causal Task Spine，并用固定 Basic30 先回答一个问题：恢复局部 Task、一次 Action、
真实 Observation、decision-last commit 后，能否重新保住 Round46 的 24 个 Basic TP，
同时不恢复它的自证式 FP。这个问题通过前，不进入 collection 大改或完整 90 题。
