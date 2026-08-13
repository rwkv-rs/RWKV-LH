# Round22 全90题反向因果索引

## 读法

本索引不是重新用一个标签替代逐题记录。每行按“冻结终态 ← 主要放大 ← 最早已观察偏差”压缩一条链；详细raw、event、workspace、
External与历史对照仍以`cases/E2E-*.md`为准。`正确`只表示artifact/External，不表示内部completed。

## Basic 30

| Case | 终态 ← 放大 ← 最早偏差 |
|---|---|
| B01 | 文件正确但proof FN、priority crash ← 100+ handles与类型错误逃出协议边界 ← Plan无完整criterion owner，RWKV选错expected source |
| B02 | JSON正确但proof/obligation耗尽 ← 同target lineage正确拒绝反复reader ← proof无法表达key=value解析与`count×2`关系 |
| B03 | config正确后protocol block ← 单请求多套action schema、parser error绕过correction ← Plan漏GC1 owner，RWKV witness/quote协议错误 |
| B04 | 正确manifest被verify覆盖成JSON string ← self-payload自证、recovery只读错误target ← vague verify Task可选择破坏性writer且丢last-good revision |
| B05 | env正确但18个无关format Tasks后block ← advance-only obligation被接受、internal history改变digest ← 初始Plan全无`satisfies` owner |
| B06 | concat正确但proof FN、priority crash ← 无concat/newline relation却持续同源proof ← evidence vocabulary对实际转换不可达 |
| B07 | 正确branch output/absence但proof FN ← negative path没有visible evidence、replan只重复target reader ← Plan漏GC1/GC2 owner |
| B08 | manifest正确但proof选failed empty hash ← 139个failed/success/whole/leaf handles等权暴露 ← Plan无owner，current view未突出latest-success causal source |
| B09 | stats缺失 ← CSV action recovery发明read_csv/read_text并block ← Plan先改写header规则且pure compute无可用action落点 |
| B10 | code正确、内部测试未运行 ← test evidence丢失、pytest ENOENT后wrapper block ← Goal无来源冻结pytest，T4不依赖unittest source |
| B11 | source受损、target缺失 ← mutation后仅有“replaced”summary、后继猜bytes ← Goal prompt echo且pure transform被Plan做成source mutation |
| B12 | 0 action、stats缺失 ← correction原样回灌并逐字复现 ← 语义基本正确的8 criteria被任意max-5整体拒绝 |
| B13 | config正确但preservation proof FN ← pre-state不在后置reader直接依赖，同target自证被拒 ← criterion owner没有独立before/after source可达性 |
| B14 | concat多一尾换行 ← self-payload通过、无concat/end-boundary relation、priority crash ← RWKV在完整right尾换行后再次追加newline |
| B15 | stable-unique JSON正确但proof FN ← source在target reader依赖中消失、obligation重复GC4 ← Plan只advance不satisfy且proof无stable-unique表达 |
| B16 | env残留blank ← generic action success把半个复合Task升completed，后续vacuous no-op ← T2单次remove只完成“comment+blank”一半 |
| B17 | filter/count结果正确但proof FN ← scratch同样源自模型且增加lineage/reader ← proof两阶段echo、source filter/project relation不可表达 |
| B18 | arithmetic JSON正确但proof FN ← Goal echo与0-owner图、source丢失、final自证循环 ← required multiply/subtract/round relation未进入criterion/evidence路径 |
| B19 | digest manifest正确但proof FN/priority crash ← state manifest提前暴露最终hash且Plan不claim ← audit metadata与model observation边界不清、coverage关闭 |
| B20 | modulo代码正确、内部test失败 ← runtime capability未知，python3修正跨choice/materialization丢失 ← T2 tests不在producer/verifier依赖且priority越过required source |
| B21 | totals缺失 ← read_json(CSV)后choice/action工具类型互相冲突 ← Plan创建parse/inspect/aggregate/sort等无action可达节点并虚假claim output exists |
| B22 | target缺失 ← failure文本知道需producer但current-task reselection持续读absent target ← source→producer→verifier dependencies全缺且priority先跑verifier |
| B23 | fallback存在却final缺失 ← deterministic JSONDecodeError被当fatal并耗尽高priority分支 ← Goal/Plan没有first-success条件语义，consumer硬依赖必失败primary |
| B24 | source破坏、target缺失 ← mutation current bytes未投影，后继无输入生成长数字序列 ← pure dedup/sort被拆成破坏source的remove_line Tasks |
| B25 | nested merge被扁平 ← leaf proof若增强可能认证错误shape ← Goal首先丢`runtime.*`parent path，Plan/Action继承flatten |
| B26 | a/b有、c缺失 ← make_directory成功即完成复合Task，69 requests重复list ← T4把mkdir+write压成one-action Task |
| B27 | 只替换1/3处 ← runtime把非法`count=-1`静默coerce为1，obligation全only-advance ← action schema/validator/executor语义不一致 |
| B28 | exact typed JSON正确但proof FN ← WS/WH两层ID混淆、source-derived T2未claim ← text→typed-object relation与criterion ownership不闭合 |
| B29 | copy/manifest正确但错误GC长期未完成 ← recovery把自造“two lines”当immutable obligation ← Goal把terminating newline发明为第二行 |
| B30 | code正确、内部tests未跑 ← abstract command无真实toolchain，ENOENT恢复退化为wrapper block ← RWKV选择未协商`python` |

## Medium 30

| Case | 终态 ← 放大 ← 最早偏差 |
|---|---|
| M01 | 多配置结果错误/不全 ← 一个reader成功被当全集观察、producer猜其余成员 ← plural source Task只落实第一个action member |
| M02 | 代码保持错误 ← self-payload write仍可完成Task ← RWKV在实现与test完整可见时原样写回，真实producer能力错误 |
| M03 | 0 action ← 全对象correction复现 ← 六项requirements被max-5硬拒 |
| M04 | artifact仅格式/newline偏差且无法完成 ← proof/owner不闭合 ← exact byte boundary未成为可执行contract，Plan无terminal owner |
| M05 | source-derived文档/输出变通用模板 ← action fidelity掩盖语义错 ← RWKV在真实source可见时仍生成泛化requirements |
| M06 | 0 action ← correction复现 ← 六项Goal超过max-5 |
| M07 | merge结果漏top override/被多writer固化 ← whole-file writers无base ownership ← RWKV在完整base/override可见时关系计算错误 |
| M08 | producer无source并错误执行 ← missing dependencies静默默认`[]`、priority替代因果顺序 ← Plan省略关键data edges |
| M09 | API迁移不完整 ← Goal缩窄后续Task只改调用文本 ← RWKV看到旧import仍漏import迁移，Goal又把完整迁移缩成调用 |
| M10 | create永远未到达 ← absent reader failure垄断recovery ← lifecycle read-before-create、无producer-consumer gate |
| M11 | 多成员preservation错误 ← 单source被模板复制到其他成员 ← “read all”只执行首个member read |
| M12 | 正确zero check被后writer覆盖 ← 两个whole-file writers同旧base、无revision ownership ← Plan并列同target producers |
| M13 | CSV/排序目标缺失 ← verify/sort先于create且media/action不匹配 ← producer-consumer顺序倒置与复合Task不可达 |
| M14 | JSON正确、Markdown排序错误且proof空转 ← 双输出无共享canonical relation、claim owner缺失 ← RWKV对同一排序生成不一致views |
| M15 | line count/aggregate无法传递 ← reader冒充compute、后继只见action summary ← pure computation没有typed result channel |
| M16 | recovery选到真实path却后继仍丢失 ← choice没有commit为typed selected-state ← 分支/locator决定只留在自然语言failure reason |
| M17 | 多member保留字段错误 ← writers看不到各自pre-state、单reader假完成全集 ← collection source ownership缺失 |
| M18 | digest/output逻辑自引用或无法证明 ← Goal冲突冻结后各层任意偏向 ← RWKV把input bytes与digest-map语义绑定成自引用要求 |
| M19 | verifier/producer抢跑、输出错误或缺失 ← dependencies省略默认空、高priority先执行 ← Plan关键dataflow缺失 |
| M20 | 0 action ← correction原样复现 ← 七项Goal超过max-5 |
| M21 | exact标准答案但proof FN ← actual/expected绑定同handle，same-source gate正确拒绝 ← 正确producer没有独立source relation claim |
| M22 | config更新语义错误 ← self-payload完成、Goal冲突让proof无安全方向 ← Goal把allowed update keys误作final allowed-key set，RWKV又未应用允许值/保留untouched |
| M23 | 网页成员/内容幻觉 ← source到达后预先active guessed Tasks仍执行 ← 未观察build_plan前静态具体化index/style/script成员 |
| M24 | 公开`add`被删除、tests未运行 ← missing deps默认空、priority饿死reader、runtime失败 ← Plan dataflow缺失且多writer覆盖 |
| M25 | 只剩组内排序与newline错误、proof FN ← target read-back同lineage；unchanged suppression仅止损 ← RWKV在完整数据下局部sort/render错误，关系无独立source claim |
| M26 | validation schema/成员不完整 ← 只读records不读schema、三个whole-output writers相互覆盖 ← plural input/read和criterion scope不闭合 |
| M27 | 节点/precedence大多正确但一个ready tie-break错、proof FN ← pure state evolution无typed result、claims空 ← RWKV对动态currently-available状态更新错误，Goal压缩还丢唯一性 |
| M28 | moved/kept分类从Round21正确退化为幻觉 ← T3只依赖T2，cutoff T1不再可见 ← direct-only投影丢仍必要source |
| M29 | fallback values未materialize、missing order反向 ← reader验证target而不读base/locale、typed partition缺失 ← RWKV虽识别base-only差集但没有完成fallback relation |
| M30 | migrated config变通用timeout模板 ← compute Task无typed handoff，writer只见中间report且丢source ← 过度拆分切断MIGRATION/config contract |

## Hard 30

| Case | 终态 ← 放大 ← 最早偏差 |
|---|---|
| H01 | tests后验PASS但example缺失 ← 局部test protocol block停止独立artifact branch ← 正确code后runtime/固定action外壳未闭合 |
| H02 | 0 action、aggregate缺失 ← 泛化correction复现、rejected Plan终态变空 ← 已唯一识别的21-node `task_graph.tasks`未完成schema归一化 |
| H03 | 六级内容正确但全在错误路径、32 reader后block ← claim空+internal history绕过unchanged ← Goal丢`stages/` locator与resume invariant |
| H04 | 安全artifact exact PASS但内部FN ← 118 handles、same-source witness与capsule echo ← Goal literal未成为independent expected source |
| H05 | priority summary猜错 ← 未读member可写入+self-payload完成 ← 全50-file scan/匹配读取分别压成one-action Tasks |
| H06 | dev精确、prod/stage/report失败 ← 唯一dev source跨成员污染，local verify block全run ← per-environment source ownership缺失 |
| H07 | 真实duplicate test failure未驱动修复 ← old ENOENT与latest functional failure混杂，重复observer ← expected-failing baseline被建模为必须exit0 |
| H08 | ledger缺失 ← pure compute被迫三次read_json(text) ← 去重Task没有typed result或真实action |
| H09 | selected缺失 ← deps默认空、无typed fallback、正确backup call因wrapper全局停 ← Goal发明`source_payload`且Plan条件语义缺失 |
| H10 | producer全未执行 ← failure/choice/args三模型阶段互相否定、same error重复 ← 双source复合read不可达并选择read_json(CSV) |
| H11 | 0 action、pipeline未修 ← 8项要求整体丢弃且correction复现 ← max-5入口门与复杂任务粒度冲突、locator还被发明 |
| H12 | aggregate缺失、proof context interrupted ← 821 handles越过action ownership读取未观察shards ← list被当read-all、compute提前拥有artifact criteria |
| H13 | phase01错误、后续缺失 ← payload自证使全batch猜测completed ← 一次doc01 read完成phase scan并忽略negative observation |
| H14 | index不存在 ← compound recursive reads假完成，failure生成大未groundedpayload并截断 ← Goal per-entry schema错误且Plan无producer |
| H15 | parser正确、其余缺失 ← analyzer不见contract并发明API，局部wrapper全局停 ← code producer input refs不含REQUIREMENTS/tests |
| H16 | requested/compensation全错或缺 ← multi-target只写一file、自证transaction completed、无branch state ← 完整source下RWKV仍提前错误rollback最高priority |
| H17 | ledger虚构并被verifiers反复覆盖、priority crash ← verify role可写subject、obligation自激 ← dependencies全部省略并默认空 |
| H18 | release全缺 ← priority先跑validator、runtime ENOENT相同action三次 ← validator漏producer deps且claims全空 |
| LH01 | pipeline四次no-op、zero stage attempts ← stale whole-file writers+self-payload/no-change completed ← priority抢跑contract reader且Plan丢fix→run milestones |
| LH02 | Round22止于step02前；Round21 artifacts全对但proof FN ← 195 handles/错误claim owner/production与evidence耦合 ← Goal缺15-member collection invariant、read-before-plan未兑现 |
| LH03 | empty index落盘 ← recursive Tasks重复root、empty自证、末端validator复制 ← 无dynamic frontier/visited/base-path state |
| LH04 | crash恢复安全但ledger schema错、未completed ← lifecycle交给readers、proof churn ← Goal scaffold echo并在source前冻结错误aggregation schema |
| LH05 | 0 action ← Plan外壳连续拒绝 ← Goal预猜primary/fallback cardinality且一次性aggregate计划无成员状态 |
| LH06 | candidate/security verdict错误、priority crash ← deps默认空、writer无approved source、malicious body未进validator、自证 ← 多source/authority/criterion relations在Plan中丢失 |
| LH07 | 0 action ← Plan外壳拒绝；历史放行又只处理service01 ← 8 reads/writes压成复合Tasks且collection/priority分支语义缺失 |
| LH08 | 只apply一member、补偿未发生 ← runtime/action recovery block、无member barrier ← 三配置apply压成一Task，expected negative/compensation不是typed state |
| LH09 | remote终态正确但duplicates=8、result错误 ← obligation重放整套effects三轮 ← 初始Plan用伪request files替API并提前猜final result |
| LH10 | source/tests后验PASS但README/manifest缺 ← recovery无新runtime信息且local block全局停止 ← T4选择部分suite和不可用`python` |
| LH11 | Round3–22全部0 Task ← 全图枚举到length或压成不可执行phase/single Task ← one-shot complete DAG contract与46+原子动作规模冲突 |
| LH12 | Round22 0 action；Round13仅parser正确 ← max-5入口死锁；唯一执行轮contract只直达parser、runtime恢复错误 ← 七项完整但重叠Goal被整体拒绝 |

## 覆盖结论

- 90份case文档全部存在，本索引每题恰有一行；它只压缩链条，不替代逐题证据。
- 相同最终`blocked`分别可能来自正确artifact proof FN、错误producer、producer未执行、Goal未创建或Plan未创建。任何下一改动必须声明它修的是哪一层，
  并用本索引中的具体cases做正/反例回归。
- 某题在后验External正确，不授权Controller在线补evidence；某题在后验External错误，也不授权Controller按标准答案改RWKV payload。
