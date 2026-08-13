# Basic B01–B20 非最终因果图

## 边界

本文件只连接已完成人工审阅的20题，不提前选择Round23方案。数字由冻结audit核对，因果判断来自逐题raw prompt、
raw output、parsed/normalized payload、event邻接、workspace bytes和standard acceptance；聚合数字不用于替代逐题归因。

- 20题中External PASS 14、External FAIL 6、agent completed 0。
- 共154个materialized task、636个独立model request；B04单题166次，是明显recovery explosion离群点。
- 14个External PASS全部是completion false negative；6个External FAIL分别是B04/B09/B11/B12/B14/B16。

## 从后向前的终态分解

### A. External FAIL：不能先怪最终verifier

| Case | 最终错态 | 第一个生产偏离 | 后续放大 |
| --- | --- | --- | --- |
| B04 | 正确manifest被改成JSON string | 后置T8把vague verification实现为`write_json`并覆盖正确T4 | action-derived verifier只对T8自身payload自洽；134+ recovery级事件继续扩张 |
| B09 | CSV summary逻辑错误/未完成 | plan明确把header当data，与用户目标矛盾 | 先选`read_json`读CSV失败；failure analysis又建议不存在的`read_csv`，最后correction才转read_text |
| B11 | source被改坏、目标缺失 | Goal objective复制prompt instruction；T2直接mutation source且replace无pre-snapshot | T3看不到可用current bytes并猜不存在old text，串行错误继续 |
| B12 | 无artifact | Goal把一个outcome拆成8 criteria，超过max5 | correction重放完整错误结构，RWKV逐字段重复；hard gate在0 action处终止 |
| B14 | merged多一个尾换行 | T3保留right既有尾换行后又加一个 | action self-check通过错误payload；witness同源；replan priority类型崩溃 |
| B16 | env仍有blank line | T2的单次`remove_line`只删comment，未完成“comment+blank”task | T3 action与reorder意图错位、T4重复MODE、T5 empty append；错误状态被逐级标completed |

这6题说明production error分布在Goal、Plan、Action和后置overwrite，不存在一个“最终验证太严”单因。尤其B04证明
正确中间产物仍可能被后继task破坏；B16证明generic action success会把未完成的中间意图变成下游权威状态。

### B. External PASS但未完成：生产与证明必须分开

14题已经产生标准答案，却全部无法登记完整Goal evidence。它们可再分为：

1. **可行proof没有被调度**：B19的T5同时依赖source与manifest，且SHA operator存在，但所有task只advance不satisfy，
   witness一次都未启动；B15/B18/B20也保存了partial/zero satisfaction coverage的初始plan。
2. **所需关系在当前proof vocabulary不可表达**：B02的parse+multiply、B06/B14的concat与exactly-one-newline、B07的
   negative absence、B13的JSON exclude-path diff、B15的stable unique、B17的filter/project、B18的multiply/subtract/
   round。
3. **operator存在但RWKV无法从catalog稳定选对**：B08有source SHA和manifest leaf却选择stale failed result；B13对
   leaf goal values选择path_exists对整JSON；B19更早在coverage层就错过可行SHA proof。
4. **后继只拿到model-written current target**：B06/B07/B13/B15/B16/B17/B18的reader把当前output与前一个当前output
   比较，same-target-lineage gate正确拒绝；问题起源多在plan dependency没有保留immutable source/pre-state。

因此“External正确→放宽same-target/goal quote gate”不是有效结论。那些gate阻止了自证；应追查为什么RWKV没有获得或
选择独立证据，以及关系是否根本不可表达。

## 分阶段重复缺陷

### 1. Goal层：单一事实源尚未建立

- B11/B18的objective复制系统prompt；B03产生非原文goal quote；B12忽略criterion数量/compactness correction。
- B18依靠Controller强制保留的correct original_request做对算术，而materialized objective已经污染，形成两个冲突目标源。
- 多题把input prerequisite或“verify”拆成独立criterion（B06/B15/B17/B18），扩大后续claim数量但不增加outcome信息。
- 目前只校验schema/数量，不校验objective是否由original request grounded，也不校验criteria是否覆盖核心关系；但由
  Controller自动重写/合并会改变RWKV决策，不能作为合规修复。

### 2. Plan层：prompt/runtime、依赖与粒度三类问题叠加

- plan prompt声明required criterion必须出现在`satisfies_criteria`，代码初始decompose实际调用
  `require_coverage=False`。B05/B15/B16/B18/B19/B20因此接受empty/partial coverage；问题直到执行末尾才暴露。
- B10/B20均规划read tests，却不给implementation/test-run添加该依赖；priority又让实现/测试越过pending reader。
- B13把preservation proof交给看不到T1 pre-state的T3–T5；B15/B17/B18也让source-derived verifier只依赖model output。
- B16的一个task包含comment+blank两类删除，最直接`remove_line`无法单action完成；B02又把atomic JSON写拆成两次whole-file
  write。TaskGraph通过DAG/schema并不代表每个node与一个action/observable postcondition语义闭合。
- B17的scratch files显示“更多步骤”不天然帮助弱模型：没有information gain或independent ownership的中间artifact只会
  增加model-written lineage、请求数和恢复面。

### 3. Action/Task状态层：`executed`被过早提升为`completed`

- B16是完整复现：只删comment、错误reorder action、already-present replacement、empty append都被generic
  `action_succeeded/file_exists/file_contains("")`标为task completed。
- B04的vague verify task被实现成mutation且覆盖正确target；B09/B11也出现task文字与action选择不对应。
- action-derived exact expected来自同一次RWKV payload（B04/B13/B14/B18等），只能证明Harness忠实执行，不能证明Goal正确。
- 现有state需要区分至少三种事实：action执行成功、task-local observable intent建立、Goal criterion独立建立；逐题记录显示
  它们当前经常被混用。

### 4. 状态投影：信息既会丢，也会过量/泄漏测量口径

- direct-only projection在B10/B13/B15/B17/B18/B20丢失测试source、pre-state或input source。
- B14以裸多行text展示dependency，尾换行与prompt delimiter边界不显式；B06相同输入写对构成反例，因此结论是表示
  不稳定性，不是模型必然不会拼接。
- B08 witness catalog保留failed/stale attempts与current success共139+ handles；audit完整性与model canonical current view未分层。
- B19在RWKV未选择hash action前，CURRENT WORKSPACE MANIFEST已暴露用户所求完整SHA。值真实且未改模型output，但混淆
  “模型选择计算”与“复制Controller预计算元数据”，需要全局统一model-observation边界而非benchmark特判。

### 5. Witness/proof协议：表达缺口与交互负担必须分开

- B03/B10/B13/B17多次在mode阶段提前输出下一阶段source/goal-literal payload；B14在selection多加reason；correction常把
  完整rejected output再次放进prompt，RWKV逐字重复。
- B08/B13表明大catalog会让弱模型选择结构上合法但语义错误的handle；B15/B19表明即使catalog能力存在，错误plan
  binding也可能让它根本不出现。
- same-target-lineage是必要anti-self-proof gate，但B17也提出尚未解决的边界：在GC1已有独立source proof后，是否允许
  同一output不同JSON paths验证`active_count == count(active_names)`这种内部invariant。现有证据不足以改规则。
- proof language缺少的不是任意Python执行，而是一组与actual task transformations相对应、由RWKV显式选择、可审计的
  deterministic expressions；是否增加以及最小集合必须等90题分类后预注册消融。

### 6. Recovery：通常在错误层修复，且协议异常会终止整个run

- obligation频繁把producer/proof缺口变成“再读一次target”：B04/B06/B13/B15/B16/B17/B18。
- unchanged-observation suppression能阻止无限重复，B13等验证了它确实识别相同workspace+fingerprint+semantic task；但
  proposal只要含一个冲突就全体拒绝，是否丢弃了有用非冲突producer需在剩余70题逐个核对，不能直接改partial selection。
- `priority:"high"`在B01/B06/B14/B19逃出model protocol boundary，`int()`抛ValueError并中断run；这是四次独立复现。
- B03/B10/B20的parser/G1i wrapper错误没有稳定完成同request-type correction；B20还在failure analysis提出python3后于
  下一action payload重新丢失修正。
- RecoveryState记录fingerprint/budget不等于知道失败发生在哪一层。当前capsule往往只说criterion unresolved/same-target，
  没有结构化区分unassigned producer、missing dependency、unexpressible relation、wrong handle、producer artifact wrong。

## 交叉反例对下一批审阅的约束

| 不能过早下的结论 | 已有反例/理由 | B21–B30继续检查什么 |
| --- | --- | --- |
| “RWKV不会concat/newline” | B06相同内容写对，B14多newline | text边界表示、action raw与输入尾字节 |
| “只要加proof operator就会完成” | B19 SHA operator可行但plan不claim；B08有operator仍选stale handle | producer claim、source reachability、catalog选择三者分别记录 |
| “same-target gate导致FN，应删除” | 多题确实在读output自证；删除会把错误B16也判对 | 独立source是否存在、内部relation是否可条件化 |
| “任务拆细能帮助弱模型” | B17 scratch、B16串行task反而增加lineage/错位 | 每个intermediate是否带来新observation/information gain |
| “External PASS说明流程基本正确” | B20没读tests/没跑通命令；B19复制预暴露hash | required process与最终artifact分别评价 |
| “terminal cause就是根因” | priority crash前已有coverage/proof缺口；B04 terminal前已overwrite | 继续固定从首次偏离向后重建，不以最后event归因 |

## 当前只确认的结构需求，不是实现顺序

1. Goal、Plan、Task、Action、Observation、CriterionEvidence必须保持不同职责和单一权威来源。
2. required criterion在执行前要有RWKV声明的producer、可达source和可表达proof；缺一项要分类记录。
3. task completed不能只等于tool returned success；no-change、already-present、vacuous postcondition需要显式状态。
4. model-visible state应同时避免丢失必要pre/source状态、堆入stale audit handles和自动暴露能力答案。
5. recovery必须回到第一个未建立的producer/task postcondition/proof关系层，而不是默认增加reader。
6. 所有模型类型/外壳错误必须留在可审计correction lifecycle，不能崩溃Controller，也不能由Controller静默改成正确答案。

这些需求仍可能互相冲突，例如hard coverage gate可能增加B12式0-action失败，扩大proof vocabulary可能增加错误选择，减少
context可能丢source。完成Basic30、Medium30、Hard30后再以全90题交叉矩阵确定最小改造和消融顺序。
