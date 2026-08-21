# RWKV-LH 历史架构轨迹与下一步方向

日期：2026-08-15

状态：只读历史复核与设计结论；本报告不修改运行时代码，不把聚合脚本当作因果分析。

## 结论

当前不应继续围绕某一道失败题给 v14 增加 completion gate、reviewer、role、
recovery 分支或提示补丁。历史证据已经足够说明，项目从 Round46 之后反复把
一个真实失败抽象成新的模型元决策，模型需要先判断“如何工作”，再执行工作，
最后再判断自己是否判断正确。弱模型在这些额外边界上损失的正确决定，已经多于
这些边界阻止的错误决定。

下一项应当优化的不是 B10 的具体算法，也不是再增加一个验证规则，而是恢复
Round46 最有价值的行为属性：**局部、原子、因果有序的 Task → 一次直接 Action →
真实 Observation → decision-last Task commit**。这一行为应在当前单一 v14 模块上
重建，不恢复旧兼容路径、旧 selector 或第二套状态库。

首个候选应移除 Goal 规划时要求 RWKV 预先猜测的 `evidence_kind/evidence_subject`，
让 evidence class、target、attempt、artifact version 从实际执行的 ActionResult
机械产生；同时把普通 Task 恢复为一个局部原子推进，而不是一个会越过后续 DAG
节点完成整项 Goal 的小型 Agent。集合任务随后通过同一脊柱上的 workset/member
ledger 承载，不通过递归 subagent 或 controller 拆题。

## 一、可比历史结果

| 轮次 | 主要变量 | Cases | Strict | External | Agent | FP | FN | 判断 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Round46 | 局部 Task DAG、直接 action、decision-last、透明 commit 格式 | 90 | **31** | 32 | 55 | 24 | 1 | 当前最高全量基线 |
| Round50 | 两阶段 tool-name → arguments | 90 | 6 | 11 | 14 | 8 | 5 | 大量正确 action 卡在接口 |
| Round51 | Round50 + 精确 `tool_name→name` | 90 | 17 | 22 | 39 | 22 | 5 | 单一透明别名恢复 11 题，但两阶段仍退化 |
| Round52 | 整批强制单层 frontier | 90 | 3 | 3 | 17 | 14 | 0 | 正确 DAG 被整批拒绝 |
| Round53 | 同一 RWKV pre-action reviewer | 90 | 23 | 24 | 43 | 20 | 1 | 减少 4 FP，却净丢 8 Strict |
| Round80-r2 | 统一 lane + selector | 90 | 0 | 10 | 1 | 1 | 10 | 新协议不能形成完成链 |
| Round81 | 同源码重跑 | 90 | 0 | 10 | 0 | 0 | 10 | 不是一次随机异常 |
| Round85 | 统一 lane + direct Task call | 90 | 0 | 7 | 0 | 0 | 7 | 去 selector 仍未接通全链 |
| Round101 | 多轮四题修复后的 v14 前身 | 90 | 12 | 21 | 32 | 20 | 9 | 局部回归通过，完整分布退化 |
| Round112 | frontier-role Basic30 | 30 | 6 | 12 | 15 | 9 | 6 | role 没阻止 FP，增加 FN |
| Round113 | compact chain 定向 14 题 | 14 | 4 | 7 | 9 | 5 | 3 | 同 14 题 Round46 为 8 Strict |
| Round115 | uv coding smoke | 2 | 1 | 1 | 1 | 0 | 0 | 证明 Python 链可用，不是整体分数 |

Round46 的分组是 Basic `24/30`、Medium `5/30`、Hard `2/30`。它不是一个好的
长任务 Agent，但它是唯一同时证明“简单链路高通过率”和“完整90可运行”的版本。
它的 24 个 FP 几乎全部集中在 medium/hard，说明应保留其基本因果粒度，而不能
恢复其自产自验式完成证据。

## 二、Round46 到 Round101 实际丢了什么

Round46 的 31 个 TP 在 Round101 中发生以下转移：

| 转移 | 数量 | Cases |
|---|---:|---|
| TP → TP | 9 | B01/B02/B03/B06/B08/B13/B14/B28/H04 |
| TP → FN | 8 | B05/B10/B12/B15/B19/B20/B26/M12 |
| TP → FP | 5 | B07/B11/B16/B25/LH04 |
| TP → TN | 9 | B09/B17/B18/B21/B24/M03/M05/M19/M24 |

Round101 只新增 3 个 TP：B29、B30、M20。净结果因此从 31 降到 12。这个转移比
单个 Round 的聚合分数更重要：当前结构不仅“更谨慎”，还同时丢失正确执行、
产生新的错误完成，并让原本可工作的代码/文件任务进入恢复循环。

### 1. 八个 FN 不是同一种模型不会做

- B05/B10/B12：前一个 Task 已经完成整个外部 Goal，但静态图继续执行冗余 Task；
  后者再选错工具或 no-op mutation，把正确 workspace 判成 blocked。
- B15/B19/B20/B26：Goal 规划时的 `evidence_kind/evidence_subject` 与真实 action
  不一致，正确读取、命令或多文件结果永久不能满足预先猜错的契约。
- M12：正确代码已写入，旧环境缺 pytest 又使前置验证永久失败；Round115 已证明
  uv 环境问题可单独解决，不能再归因于模型不会修代码。

### 2. 五个新 FP 暴露 Task 越界

- B07：在观察条件前同时建立 production/staging 两个 required 分支，后写覆盖前写。
- B25：只读验证 Task 被允许重新 `write_json`，覆盖曾经正确的结果。
- B11/B16：模型转换值错误，读回自产物只证明“它仍是自己写的值”。
- LH04：业务结构键名错误，恢复骨架通过但完成语义错误。

### 3. 九个 TP→TN 混合了模型错误和系统放大

B09/B21 是 CSV 已读后仍选 read_json；这属于模型工具错误，但恢复重复同一错误。
B18 是模型明确给出正确内容却被 `write_json.content` 接口拒绝。M19 是 EOF 被当
错误。M05 是协议说明复制进 done_when。M24 是环境/runner 阻塞。只有把首次模型
错误与后续系统放大分开，才能知道哪里值得改代码。

## 三、Round46 为什么能做对更多简单任务

### 1. Task contract 是局部行为，不预注册证据猜测

Round46 的 Task proposal 只有 `local_id/title/description/dependencies/postcondition`。
规划不要求 RWKV 在看到实际 action 前再猜一遍 evidence class 和 subject。当前
`model_io.py` 却要求每个 Task 同时生成 `evidence_kind` 和 `evidence_subject`；
Round101 的 B15/B19/B20/B26/M01 已证明，这两个字段一旦猜错，后续真实正确动作
也无法使 Task ready。

### 2. 普通 Task 只承担一次原子 Action

Round46 B10 的真实顺序是：

`read slug.py → read test_slug.py → write slug.py → python test_slug.py`

四个局部 Task、四次 Action、四个真实 observation。Round46 M12 同样是读取源码、
读取测试、两次局部 producer、运行测试。Round46 B25 的验证 Task 是 `read_json`，
没有机会再次写坏正确产物。

Round101 B10 则在“读取 slug.py”Task 内连续 read/write/test，已经完成整个 Goal；
随后静态 T2 又重新读取并误用 read_json，产生 FN。Round101 B25 的 T1 和 T4 都
执行了完整合并链，最后一个所谓验证 Task再次写坏结果。问题不是缺更多完成 gate，
而是 Task DAG 与 Task 内 Agent loop 同时存在，两套推进粒度相互叠加。

### 3. Action 是一次直接完整调用

Round50 把 action 拆为选工具与填参数后从 31 降到 6；仅补一个透明 key alias 就
回升到 17，说明弱模型的正确决定经常已经完整存在，只是被接口接缝浪费。当前应
保留 v14 的 direct registered call，不恢复 selector/reviewer。

### 4. decision-last 看真实结果，不在执行前想象结果

Round53 reviewer 会把旧失败绑定给新候选、拒绝正确修复，也会接受与自身错误理解
一致的错误动作。Round46 的 Task commit 位于动作之后；这是应恢复的时序属性。
但不能恢复“模型写入值就是 expected 值”的同源证据。

### 5. 因果上下文靠近当前 Task

Round46 的 WorkingMemoryBuilder 只投影 active Task、显式 dependencies、当前 evidence
和 compact failure。后续多轮把完整 catalog、状态 capsule、review reason 和重复
历史堆到 recovery 边界，真实失败值虽然存在，却被模板回显与旧状态淹没。

## 四、Round46 哪些东西不能复制

1. 不能恢复旧多角色协议、旧 `memory.py/tool_protocol.py/proof.py` 并与 v14 并存；
   只重建行为不变量，仍保持一种当前架构。
2. 不能恢复 action 自己的写入值作为语义 expected。Round46 的 24 FP 证明
   `write → read self → complete` 对 medium/hard 不构成独立验证。
3. 不能把所有 collection Task 强制成单 Action。Round55 H12 已顺序读到 7 个 shard，
   说明多成员进度必须有结构化 ledger；自由文本计数会把 7 误报成 15。
4. 不能恢复格式失败后的整次语义重采样作为“提升质量”的方式。Round46 B10 的
   更好代码有一次来自格式拒绝后的随机重采样，这是偶然收益，不是架构能力。
5. 不能以 Basic30 代替 E2E-90。Round46 在 basic 很强，但 medium/hard 只有 7 TP、
   23 FP。

## 五、为什么后续像“无头苍蝇”

### 1. 每轮变量越来越靠后

Round47–53 依次尝试 stale frontier、noop lineage、强制 immediate frontier、两阶段
selector、格式 alias、pre-action reviewer。它们大多处理 Action 以后或执行边界的
症状，而 Task 的因果粒度与集合表示仍未解决。

### 2. 元判断替代了工作本身

- Round53：同一模型 review 自己的 action，23/90。
- Round54：让模型先判断 Task 是否 atomic；15 题生成数百 Task，0/15。
- Round68–71：增加 review pipeline/fixed semantic tools，长期接近 0。

这些层没有新增事实，只增加模型必须正确序列化的决定。

### 3. 微型 canary 被用来证明架构

Round93–100 反复围绕 B01/B02/B03/H04 修复，Round100 达到 4/4。这四题在 Round101
仍恰好全部 TP，但完整90只有12。微型 canary 证明了“这四条路径接通”，没有证明
整个 Task/Action/Recovery 表示正确。Round102–110 又逐渐缩到十题、三题、两题、
单题，多个单题仍为0，随后 Round112 Basic30 只有6。

### 4. 安全阻断被误当成质量提升

Round46→101 的 FP 只从24降到20，Strict却丢19，FN从1升到9。阻断错误动作是必要
安全属性，但它不能补偿大量正确 workspace 被判 blocked。质量 gate 必须同时看
TP 保留、FP、FN和首次偏离，不能只看“没有误报”。

## 六、下一步：v15 单一因果 Task 脊柱

这是一个行为重建，不是恢复旧实现。

### P0-A：局部 Task contract

Goal lane 的普通 Task proposal 只包含：

```text
key, objective, done_when, after
```

- `objective/done_when` 必须描述本 Task 的一个局部推进，不重复整个 Goal。
- 删除规划边界的 `evidence_kind/evidence_subject`。
- TaskNode 可以保留 runtime evidence 字段，但值只能从实际 ActionResult 的 action、
  target、attempt、artifact/hash、command result 机械登记，不能由 controller 猜答案。
- 保留完整 RWKV DAG 和 dependencies；不再强制整批无依赖，也不加 frontier role。

### P0-B：普通 Task 的原子执行

1. RWKV 从当前 direct action catalog 提交一次完整 action。
2. Harness 执行，记录 exact observation。
3. RWKV 在 observation 之后选择 Task done 或显式 repair/replacement。
4. 成功的普通 Task不继续执行第二个独立 producer/verify 阶段；后续阶段由 DAG 的
   下一个 Task承担。失败 action 可在同一 recovery lineage 内更正。
5. 不增加 selector、reviewer、judge 或第二次 completion confirmation。

这会消除 Round101 中“计划已经有 T2/T3/T4，但 T1 又做完整 Goal”的双重循环，
也使只读验证 Task无法在同一 Task 内先读后写整套产物。若 RWKV 认为一个 Task
需要多步，它应在 Goal/repair lane 产生由自己决定的局部 Tasks，而不是 controller
拆分。

### P0-C：保留已证实的现行基础设施

- 单一 `ModelSession` lane/checkpoint 与 prompt-replay 审计；
- 单一 `ActionDefinition` registry；
- direct registered G1i call；
- raw/normalized payload 和 Final byte preservation；
- uv Python 只读环境、bubblewrap、`shell=False`、workspace scope；
- 仅搬运显式值的简单格式转换层。

### P1：与原子 Task 同构的 workset member ledger

普通 Task 基线通过后再处理集合：

1. RWKV 通过现有 `lh_workset` 显式登记发现的 member id/source/target 并决定 sealed。
2. 每个 member 走同一条原子 action→observation→commit 脊柱，不创建子 Agent。
3. Runtime 只维护 pending/attempted/observed/produced/verified 和 artifact version；
   不选择成员内容、不生成摘要、不计算答案。
4. reduce/summary 只有在已 sealed 且 ledger 无 pending member 时才可由 RWKV执行。

这直接对应 M01/M06/M18/H02/H12/H13/LH11 和“大项目逐文件总结”的共同根因。

### P1：no-progress 使用相关状态，而不是全 workspace digest

Round115 B10 每次 pytest 都生成 cache 文件，导致全 workspace digest 变化；相同
`slug.py` producer 因而可以反复通过 unchanged guard。后续 recovery fingerprint 应
绑定：Task lineage、operation+arguments、目标 artifact hash、最近 verifier fingerprint，
而不是无关 cache/临时文件。supersede 链共享预算。失败胶囊只投影最近 actual/expected、
producer action 和目标版本，不重复整个 catalog/history。

## 七、验证顺序与停止条件

### 第一阶段：历史行为回归，不跑单题优化

固定 Basic30，重点报告 Round46 的24个 Basic TP是否保留，以及 Round101 的7个 Basic
FN是否释放。候选只有同时满足以下条件才进入下一阶段：

- Strict `>=24/30`；
- FP `<=1`；
- FN `<=1`；
- B01/B02/B03/B06/B08/B13/B14/B28 全部保留；
- B05/B10/B12/B15/B19/B20/B26 不得再因冗余 Task/错误 evidence contract 阻塞；
- 每个结果有逐题首次偏离，不以请求数替代质量。

### 第二阶段：collection/medium-hard canary

固定 M01/M06/M18/H02/H05/H12/H13/LH03/LH05/LH11，并加入成功对照 B29。验证
member completeness、基目录、sealed/barrier、artifact version 和 reduce 输入闭包。
本阶段不允许为单 case 增加规则。

### 第三阶段：完整 E2E-90

只有前两阶段通过才运行。替换并上传 Round46 的门槛保持：

- Strict `>31/90`；
- FP `<=24` 且 FN `<=1`；
- Basic/Medium/Hard 分组完整；
- 全 offline、LH-Control、边界、异常、crash/recovery 回归通过；
- raw Final 不改写；
- 失败题逐题反向归因。

### 停止规则

- tiny canary 通过不得宣称架构提升；
- 同一模型 reviewer/judge 不再作为新变量；
- controller 不从 Task 文本推断工具、成员、expected 或答案；
- 格式修复不得触发完整语义重采样后把第二个答案冒充为原答案；
- 任一候选 Basic30 低于门槛立即回退，不在其上继续叠加补丁。

## 最终判断

最合理的下一步不是继续修当前 B10 或再跑一个单题，而是先用 v14 的干净模块重建
Round46 的局部原子因果粒度，删除 plan-time evidence 猜测和普通 Task 内的重复
mini-agent loop。这个变量同时解释 Round46 的 Basic 优势、Round101 的8个 FN、
5个新 FP、Round113 的请求爆炸和 Round115 B10 的同义重复，是目前覆盖范围最大、
又不替 RWKV 生成答案的结构改造。
