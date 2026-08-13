# Round22 Hard 30题人工因果合成

## 1. 范围、结果与解释边界

本文件合成`E2E-H01`–`E2E-H18`与`E2E-LH01`–`E2E-LH12`的30份逐题记录。每个结论都先由visible input、RWKV raw、
parsed/normalized payload、真实Harness observation、workspace revision及恢复事件建立，再连接External与历史轮次。它不是标签聚合器输出，
也不把最后一个exception当成根因。

- Hard 30题只有H04 External PASS；它仍未agent completed，是正确安全artifact的completion false negative。其余29题External FAIL。
- 共产生253个materialized Tasks、173次Harness attempts和519次结果口径model requests；agent completed仍为0。
- 六题零attempt：H02、H11、LH05、LH07、LH11、LH12。其中H11/LH12死在Goal，H02/LH05/LH07/LH11死在Plan。
- H12/H14/H17/LH06以`interrupted`结束，24题`blocked`，H11/LH12 `not_created`。这些terminal status不能说明首因所在层：H12在proof
  budget中断前已有错误criterion owner，H14在failure schema中断前根本没有producer，H17/LH06在priority类型crash前artifact已错。
- Hard中存在多条明确正向证据：H01、H15、LH10与历史LH12的parser在直接contract/test grounding下写对；H06只在有对应source的dev上精确迁移；
  H03六级内容传递和真实中断恢复正确；H04抵抗真实prompt injection；LH02 Round21生成15/15正确checkpoint；LH09完成真实API lifecycle的核心state。
  这些能力不能被最终0分抹掉。

## 2. 30题首因链总表

| Case | 最早决定性偏差 | 主要放大环节 | 终止/外部表现 |
|---|---|---|---|
| H01 | 正确代码完成后，测试action外壳与runtime未闭合 | 局部T5 block升级全run，独立ready artifact writer未运行 | tests后验PASS，example artifact缺失 |
| H02 | 完整21-node `task_graph.tasks` Plan被已识别却未闭环的schema拒绝 | 泛化error+截断旧输出使第二轮复现，rejected Plan在终态变空图 | 0 action，aggregate缺失 |
| H03 | Goal把`stages/stageN`降为根路径并漏resume invariant | claim全空；稳定workspace因内部history增长被误判为新观察，32个reader扩张 | 内容递推正确但路径全错，budget耗尽 |
| H04 | 正确producer没有Goal-literal独立expected，witness选择同源且协议截断 | 118 handles与capsule echo；proof error升级全局block | artifact和scope全对，completion false negative |
| H05 | “读50文件/读所有匹配项”各压成一次read，纯sort无typed result | 未读成员可进入producer；self-payload验证；错误artifact成为事实 | 猜doc01–03，后续错误writer外壳block |
| H06 | 三个环境writer共用唯一dev source | per-member ownership缺失；prod/stage模板化；验证block阻断独立report | dev精确，prod/stage/report失败 |
| H07 | expected-failing baseline被建模为必须exit0的Task | launch/test verdict/observation success混同；新bug输出与旧ENOENT并列，恢复复读 | 获取真实duplicate failure后仍不解锁fix |
| H08 | pure dedup compute Task没有合法typed output/action | RWKV三次用read_json读文本；同media failure无策略转换 | producer从未运行，ledger缺失 |
| H09 | Goal发明`source_payload`，Plan又省略全部dependencies | 缺字段默认`[]`；无first-success branch；正确backup action因外壳令全run停 | fallback未materialize，selected缺失 |
| H10 | 复合双source read不可达，首次实际又用read_json读CSV | failure/choice/materialization三次模型决定互相否定；相同失败因可选参数分裂 | 三次JSONDecodeError，零producer |
| H11 | 8个原子要求被任意max-5整体拒绝，且发明四个错误文件locator | 全对象correction逐字复现；禁止改verifier未成typed policy | 0 action，代码能力完全未测 |
| H12 | list一次被当“读全部15 shards”，compute提前拥有artifact criteria | proof catalog越过action ownership读取未观察文件，821 handles耗尽frame | event43 context interruption，aggregate缺失 |
| H13 | phase scan用一次doc01 read完成，随后把batch membership当priority | write payload同时作expected，错误checkpoint completed；相邻协议字段漂移 | phase01错误，其余缺失 |
| H14 | Goal把global total发明成per-entry；Plan完全没有index producer | 复合recursive readers假完成；failure analysis生成未grounded大payload并截断 | artifact不存在，recovery protocol interrupted |
| H15 | analyzer writer没有直接REQUIREMENTS/tests contract | direct-only状态只给example+parser write；RWKV发明错误API；局部wrapper全局停机 | parser正确，analyzer后全部缺失 |
| H16 | 完整source可见时RWKV仍提前错误rollback workers并漏runtime | multi-target apply只写一文件；self-payload使错误transaction completed；无条件补偿分支 | 首次check尚未真实启动，协议block |
| H17 | 全Plan dependencies缺失并静默默认空 | 无source时虚构ledger；“no replay verifier”反复写subject；workspace自变使obligation不停 | artifact多次被验证系统覆盖，priority类型crash |
| H18 | validator Task漏release producer dependencies，高priority先执行 | claims全空；conditional no-op无typed verdict；同ENOENT action重复三次 | release producers饿死，recovery budget耗尽 |
| LH01 | contract reader被priority修复Tasks抢跑，四writer只依赖旧pipeline | same-path stale writers、no-change自证完成、缺逐stage run与artifact producer | 四次原样覆盖，最终action wrapper block |
| LH02 | Goal缺15-member collection invariant并错绑criterion owner | proof对简单relation展开195 handles；正确step02 action仅因wrapper停止 | Round22只step01；Round21产物全对但proof FN |
| LH03 | static Task用重复root read冒充recursive discovery | 无frontier/visited/base path；空aggregate自证；obligation复制末端validators | empty index落盘后protocol block |
| LH04 | Goal objective复制prompt scaffold，并在读source前冻结错误schema | 错artifact自证；lifecycle invariant交给普通reader；obligation churn | crash恢复实际安全，ledger语义错且未completed |
| LH05 | Goal在观察前猜primary20/fallback0并漏total/source/hash语义；Plan外壳连续拒绝 | 一次性discovery/aggregate/seal缺渐进成员状态 | 0 action，未测真实shard能力 |
| LH06 | 六节点Plan全部省略dependencies并默认空，三次read压成单Task | writer无approved source而虚构；恶意note从未进validator；self-derived proof；priority crash | candidate错误，security verdict无因果source |
| LH07 | 8-service完整Plan被`task_graph.tasks`/schema外壳拒绝 | 若放行仍有8 reads/8 writes压成单actions、priority使特殊迁移分支饿死 | 0 action，Round21只处理service01 |
| LH08 | 三配置apply被压成一Task且实际只写a；expected failure/compensation不是一等状态 | runtime capability缺失；failure后action wrapper block；member barrier缺失 | requested full state从未建立，补偿未测 |
| LH09 | 初始Plan把API operations变成伪request JSON并提前猜result | obligation后置执行真实effects；无external effect cardinality，整套API重复三轮 | remote state正确但409 duplicates=8，result错误 |
| LH10 | 正确code后T4选择部分suite和不可用`python` | recovery无新capability，重复argv并用错误外壳；局部block阻断独立README/manifest | External tests PASS，docs/manifest缺失 |
| LH11 | 一次性完整46+原子动作DAG contract与输出预算冲突 | 历史要么枚举到length，要么把8 reads压一Task；纠错逐字复现fragment | Round3–22全部0 Task，memory能力从未测试 |
| LH12 | 7项完整但有重叠的Goal被max-5整体拒绝 | 19/20轮入口死锁；唯一Round13又因contract只直达parser、runtime恢复错误而停 | Round22 0 action；Round13 parser正确、后续错误/缺失 |

这张表说明Hard失败不存在一个“加某工具”即可解决的共同根因。相同terminal `protocol block`前可能分别是正确producer（H01/H04/LH02/LH10）、
错误producer（H05/H15/LH03）、根本无producer（H14）或零Plan（H02/LH07）。下一结构必须按最早未建立层路由，不能按最后exception统一恢复。

## 3. Hard对RWKV真实能力的更精确测量

### 3.1 直接grounding显著提高producer质量

- H01同时看到source+tests后一次实现正确CSV loader/summary；LH10同样一次修对两个math函数。
- H15 parser直接看到REQUIREMENTS而正确；analyzer不再看到contract后立即发明`duration/average/max/min`通用API。
- LH12 Round13 parser看到完整REQUIREMENTS而正确；analyzer只看到`file written`后把`summarize(lines)`改成`analyze(parsed)`；reporter再沿错误接口扩张。
- H06同一个Goal/同一种transform，dev writer有dev source而exact PASS，prod/stage没有各自source而猜值、丢字段、跨成员复制。
- H03每一级拿到直接前驱snapshot后六级递推都正确；Round21缺这条投影时从第二级开始丢prefix。

这些同run或跨轮对照建立的不是“相关性”：输入可见性是唯一显著变化，输出质量同步变化。下一步结构应优先保护contract/source到producer的因果路径，
而不是先增加更多后置评分规则。

### 3.2 完整输入可见时RWKV仍会真的做错

- H05看到doc01明确`PRIORITY:no`仍把它纳入，且虚构未读doc02/doc03；这是model factual error加未观察成员无gate。
- H16看到request/policy/both configs仍选workers4/memory40，提前回滚最高优先级且漏runtime；这是实际decision error。
- LH04看到完整events仍稳定选择per-id occurrence/amount aggregation，而非冻结顶层unique schema；可见措辞有歧义，但模型choice确实记录为错误候选。
- LH09在真实API lifecycle中能正确创建/查询/更新/finalize，但初始result仍虚构ID/shape，503后提前声称已成功并改变payload，之后反复重放effects。

架构不能替模型改这些值、schema或分支。它应让错误更早以source relation、transaction coverage、typed HTTP transition等真实反馈显现，并让RWKV提交修正。

### 3.3 当前仍未测到的能力不能被判“模型不会”

- H02/H11/LH05/LH07/LH11/LH12零attempt；它们分别未测20-shard aggregation、pipeline repair、resilient shards、8-service migration、
  long-context fact retention和完整mini-project。
- H14从未有writer；H08从未到dedup producer；H07虽拿到duplicate test failure却未解锁任何fix；LH08未完成requested full state，补偿决策没有真实输入。
- LH10 README/manifest writer从未被请求；不能说模型已经写错这两个文件。External“missing”只证明调度/协议链未到达。

后续消融应统计每层reachability和首次有效producer质量；只看最终External会把“未测”误记为“答错”。

## 4. Hard确认的全局结构缺陷

### 4.1 Goal需要原子requirements、过程milestones与terminal evidence分层

- 任意max-5造成H11/LH12多年入口死锁，并在H15压缩时丢digest verification；同类问题已在Basic/Medium反复出现。
- H03丢typed path/resume invariant，H09发明字段，H14发明per-entry global字段，LH04复制prompt scaffold，LH05在观察前猜collection cardinality。
- H07 baseline、H16/LH08 compensation、LH09 API lifecycle、LH01 stage progression表明“发生过某过程”与“最终workspace状态”不能用同一种criterion表示。

原始request必须是权威source；RWKV projection保留raw和grounding status。Controller可以检测新增locator、prompt scaffold、计数/类型/互斥，但不能静默合并、
删除或修正语义。Goal失败也必须进入pre-run lifecycle审计。

### 4.2 一次性静态全图无法承载collection、recursive与长项目

- H02的21-node graph已接近可执行却被协议拒绝；LH11完整图至少46 actions，历史持续在output length与compound Task间摆动。
- H05/H06/H12/H13把“all/each”压成一次read；H14/LH03递归发现没有frontier；LH07把8 reads/8 writes压成少量Tasks。
- 静态Plan在观察前还会猜动态成员、fallback和schema；source到达后错误Tasks仍保持active。

需要bounded plan continuation：RWKV先声明当前可执行观察/phase，真实result进入typed frontier后，再由RWKV扩展下一批。Controller只保存member、visited、
owner和scope，不自动筛选IMPORTANT/PRIORITY、计算aggregate或补Plan edges。

### 4.3 Plan字段必须有语义，缺失不能等于显式空

- H09/H17/LH06把省略dependencies静默变成`[]`，直接造成writer source饥饿、verifier抢跑和虚构结果。
- H11/LH12的criteria count、H17/LH06的`priority:"high"`、H02/LH07的schema/envelope都显示类型/身份错误处理不一致：有的过早硬停，有的绕过schema后runtime crash。
- required criterion coverage只写在Prompt却未执行，H03/H06/H07/H10/H17/H18等大量图所有`satisfies_criteria`为空；H12又是错误full coverage。

schema、semantic feasibility和criterion ownership需分层：字段缺失/类型/唯一透明外壳做typed protocol repair；source/effect/owner/one-action可达性只返回缺口给RWKV，
不由规则补语义。

### 4.4 `action_executed`、`task_established`、`criterion_evidenced`必须彻底拆开

- H13/H16/LH01/LH03/LH04中，write payload本身同时充当expected，错误或no-op写入都被标completed。
- H07 baseline exit1其实成功获得诊断，但被当Task失败；H08 pure compute反而没有可持久化结果；H18 conditional no-change只是read成功，没有typed verdict。
- H17“验证no replay”的Task反复改写subject，证明verify role若没有effect policy会主动破坏被证明对象。

Harness执行忠实性是必要低层事实，不是任务语义。Task要有显式typed outcome/relation；proof/verification默认read-only，producer correction必须有新revision lineage。

### 4.5 Observation store与RWKV当前投影不是同一种内存

- 全量audit必须append-only；但H07已解决ENOENT与最新functional failure并列、H12/LH02的数百handles、H03增长history改变digest，都让弱模型当前视图失焦。
- H15/LH12的直接contract消失说明投影过少；H12 proof scope-wide读取未由action观察的14个shards又说明投影越过因果ownership。
- 正确投影应保留Goal commitments、当前Task所需sources、latest-success artifact revisions、latest material failure delta及被引用的typed intermediate；历史按需展开。

这对应Prime Agent可借鉴的“状态胶囊”，但事实必须从SQLite权威state确定性生成，不能用自由摘要替代source，也不能把未观察workspace内容送入proof掩盖reader缺失。

### 4.6 Process、transaction、lifecycle与external effect需要一等ledger

- H03/LH04/H17的resume/no-repeat/byte stability必须由run epochs、attempt IDs、action keys和raw hashes证明，普通read Task无法证明“没有重跑”。
- H16/LH08需要before→requested→failure verdict→RWKV rollback→after→final pass的transaction ledger；Controller记录每个key/member，不替模型选rollback。
- LH09需要operation/request_id/payload/response/role/cardinality ledger；已有response的proof不能再次调用API，`retry_same`必须保持模型首次action identity。
- H07的test baseline、LH01的stage verifier和LH10的full suite都需要command launch、exit verdict、业务milestone三层结果。

这些ledger保存模型与环境实际发生的事，不修改模型答案；反而能阻止规则/obligation通过重复side effect“验证”出新状态。

## 5. Proof/Witness：问题不是FP gate太严，而是证据入口、范围和协议失配

### 5.1 必须保留的防作弊边界

- writer payload不能同时作actual与expected；H13/H16证明这会让明显错误自证，H04正确artifact也不能因此例外放宽。
- proof source必须来自真实causal lineage；H12自动向witness暴露未读shards会掩盖producer observation缺口。
- hidden acceptance永不进入online evidence；H13的`priority_files`/basename、LH04/LH12的冻结schema差异只能做后验评价，不能注入规则。

### 5.2 当前proof为何同时漏正确产物和放大错误图

- H04明确Goal literal没有变成独立expected，118 handles反而诱发metadata回显；LH02一个简单source→checkpoint relation展开195 handles；H12到821 handles并中断。
- H03/H17/LH03的错误或无claim Task已completed，proof失败后obligation只会追加末端reader/writer，无法回到缺source/错误producer。
- LH02 Round21外部全绿但proof始终不闭合，是最强completion FN基线；下一步不能以删除same-lineage gate解决，而要给它真实source collection relation。

Proof接口应按criterion先给有限source roles，再由RWKV选择operator/pointer；只有因果可达source可展开。明确Goal literal、artifact digest、command result、external response、
resume lineage各是不同typed source，不再混成几百个平权handles。

## 6. Recovery：应回最早缺口，而不是让内部历史制造“新进展”

- H03稳定workspace后执行32个reader；H17 verifier写subject造成自激；LH09整套API重复三轮；LH04/LH03反复末端reader；H10相同CSV error真实执行三次。
- material observation digest必须排除增长的Task/history，并包含workspace/external state、source revisions和failure class。外部/时效状态不能错误缓存。
- 相同deterministic read/pre-exec failure、同action fingerprint与同source revision时，不再调用Harness/RWKV cross-check；记录RWKV重复决定并消耗budget，要求
  改变action或恢复层。这个机制不替模型选择`read_file/python3/replan`。
- failure routing至少区分Goal grounding、Plan schema、Plan semantics、source missing、producer wrong/partial、capability mismatch、expected negative branch、proof source/operator、
  protocol syntax及external effect cardinality。H14缺producer不能在verify Task里reselect成writer；H07有效baseline不能继续当launch failure；LH09已有API success不能由obligation重放。

## 7. 协议与runtime的真实位置

Hard中`task_graph.tasks`、`action_type`、`action.type+arguments`、`function/function_call/tool_calls`、JSON-string arguments等稳定出现。只在selected action唯一、
字段无冲突、arguments原样保留时透明归一化，能让H02/H09/H13/H15/LH02等继续被真实测试；这不等于它们会External PASS。

协议层还需修三个系统性问题：

1. 相邻阶段不要用`action_type`/`name`表示同一概念后又惩罚模型复制前一字段；内部统一canonical protocol，provider/model适配只在边界。
2. correction返回精确field/type/path，使用局部replace/continuation，不附巨大截断旧输出；truncated outer object不能由内部arguments冒充。
3. H01/H07/H16/H18/LH08/LH10反复证明abstract command catalog不等于真实runtime。公开受限interpreter/test capability和action role，让RWKV选择；
   不由Controller把`python`静默改`python3`。

## 8. Round21→Round22必须保留的进步与必须修的回归

### 8.1 已确认进步

- H01从错误代码变成External tests PASS；H03六级递推全保留且中断后completed Task不重跑；H06 grounded dev首次精确；H07真实运行unittest并拿到bug；
  H12/H13/H15从零Plan推进到真实action；LH02第一跳正确且Round21全套产物正确；LH04 bounded witness允许crash恢复后继续；LH10源码修复正确。
- 透明function外壳和JSON-string arguments已在多题忠实工作；不能回退为“所有非canonical一律拒绝”。
- recovery budget与部分unchanged suppression减少了Round21某些几十Task风暴，但尚未按material lineage稳定工作。

### 8.2 明确回归

- H17/LH06 dependencies静默丢失；LH01从Round21的stage链退化为四个并列stale writer；LH09从Round21零duplicate变成8次；LH12长期max-5仍未解；
  LH11长期一次性Plan仍零执行。
- H12/LH02 proof catalog引入新的context failure/协议负担；H18 protocol接受率提高，却更完整执行错误依赖和同一不可用命令。

下一轮不能以“请求接受更多”“Task更少/更多”或“protocol block更少”单独判优。必须同时看Strict E2E、External、首次producer质量、source coverage、FP/FN、
material request数、side-effect cardinality和预登记相似度。

## 9. Hard阶段收敛出的结构方向（仍待全90最终排序）

Hard 30已经把Medium的八个待验证假设全部证实，并增加四个必要维度：process milestone、transaction/lifecycle ledger、external effect cardinality和pre-run audit。
结构职责可收敛为以下层次，但实现顺序仍需连接Basic/Medium全90：

1. **Requirement layer**：original request原子commitments、locator/schema grounding、protected artifacts、milestones与terminal outcomes分层。
2. **Incremental planning layer**：小批可执行Tasks、explicit semantic fields、one-action/typed-result、collection/frontier/branch continuation、artifact read/write ownership。
3. **Execution layer**：统一内部action protocol、runtime capability、raw/normalized audit、typed action result与material revision。
4. **State layer**：append-only authority加deterministic current capsule；contract/source pinning、latest failure delta、collection/transaction/effect/lifecycle ledgers。
5. **Evidence layer**：criterion owner、causal source roles、渐进operator/pointer、action fidelity/task establishment/Goal evidence三态。
6. **Recovery layer**：按最早未建立层路由、unchanged material suppression、task-local block与safe independent progress、side-effect cardinality gate。

所有层共同受一个边界约束：架构只能保存、暴露、执行、验证和反馈RWKV自己的proposal及真实环境结果；不能补任务语义、依赖、criterion、参数、成员、
分支、值、代码、答案或最终文件。下一文件将把Basic/Medium/Hard 90题连接成统一因果图，并据覆盖范围与依赖顺序给出下一步结构修改指导。
