# Round22 Medium 30题人工因果合成

## 1. 合成范围与结论边界

本文件只合成`E2E-M01`–`E2E-M30`逐题审阅中已经记录的observed facts。它不是脚本按标签计数的报告，也不直接决定
Round23改动。每个模式都通过具体case连接“首个偏离点→下游放大→终态”，并保留反例与Round21对照。

Medium 30题的总体现象不是“RWKV完全不会做任务”，也不是“只差兼容工具外壳”。更准确的结论是：

1. RWKV在输入成员完整、任务边界紧凑时已经表现出真实能力：M21一次生成精确标准答案；M25从Round21的通用幻觉改进到只剩
   一个组内排序与末尾newline错误；M27正确完成节点集合、计数与全部dependency precedence；M28在Round21 cutoff可见时曾生成正确
   moved/kept分类。
2. 当前架构经常在模型观察关键数据前冻结具体Plan，或把模型漏填的dependency、集合成员、criterion owner静默物化成“空/已完成”；
   这会让本可被RWKV使用的真实输入在producer阶段缺席。
3. 生产task完成主要由action success和“artifact等于刚提交payload”决定；它证明Harness忠实执行模型输出，却常被误用为任务语义
   已进展。错误producer因此成为后续唯一事实源。
4. proof层正确拒绝了same-target/same-lineage循环自证；问题不是gate过严，而是架构没有保留可供RWKV选择的source relation、typed
   intermediate和独立expected provenance。放松gate会增加作弊/假阳性。
5. recovery多数新增reader或重复writer，不修最早错误的Goal/Plan/producer；material workspace不变时内部task history仍增长，最终把
   一次局部错误放大成十几至几十次模型请求。

## 2. 按生命周期定位首个偏离

### 2.1 Goal：表示容量、语义互斥与可见规范

| 模式 | 直接证据 | 因果后果 |
|---|---|---|
| 固定max-5与自然验收粒度冲突 | M03、M06、M20连续两次返回6/7项后0 action；M27第一次6项包含nodes_unique | 前三题完全阻断；M27 correction为满足上限删除唯一性，开始造成hard requirement实质丢失 |
| 全对象correction强化旧输出 | M03、M06、M20逐字复读；M23只修Plan schema而保留网页假成员 | 局部表示错误无法局部修，完整rejected payload成为强复制模板 |
| Goal内部语义冲突未在freeze前处理 | M18把输入bytes与digest_map自引用；M22把allowed update keys误成final config allowed keys | producer面对互斥criteria，只能任意偏向或生成第三种错误语义 |
| Goal语义被缩窄 | M09把完整API迁移缩为调用文本；M27把动态currently-available弱化为初始no-dependency节点 | 下游Plan/producer漏import或使用分支优先顺序 |
| exact schema未在visible boundary声明 | M04 final newline、M22 applied/rejected属性、M26 valid/rejected属性、M29 translations包装 | 即使修复可见语义仍可能因hidden convention失败；这些差异不能用于指控模型能力或驱动在线修正 |

这些case支持Goal grounding与Goal representation repair分层：架构可以检测count、schema和形式互斥，但不能静默删criterion或替RWKV
解释冲突。需要模型拥有可审计的局部merge/replace/delete权，且repair后重新检查原始hard obligations覆盖。

### 2.2 Plan：静态全量规划在观察前制造假事实

| 模式 | 直接证据 | 因果后果 |
|---|---|---|
| 复数自然语言task只落实一个action成员 | M01、M11、M17只读首个配置；M26只读records不读schema；M28只读一个log | action success把“一个成员”提升为“全集完成”，后继在缺source时猜值或覆盖原值 |
| 未观察数据前具体化动态成员 | M23读取build_plan前就生成index.html/style.css/script.js | 真实T1数据到达后，错误Active Task仍压过source并驱动三次幻觉写入 |
| missing dependencies被默认`[]` | M08、M19、M24 | producer/verifier先于reader执行；M24较Round21退化到完全未读源码、公开`add`被删除 |
| priority被误当作因果顺序 | M08、M19、M24 | 在缺edge时高priority错误task先执行，reader或正确producer被饿死 |
| lifecycle顺序倒置 | M10读不存在文件早于create；M13 verify/sort早于create；M30 verifier早于其断言必须存在的report | current failed task垄断recovery，后方可行writer永远不运行，或未来verifier必然失败 |
| Plan无criterion completion owner | M04、M14、M17、M26、M27、M29；若干题GC只advances不satisfies | 无论action多正确，CriterionEvidence从结构上都不可能完整；obligation继续派生无owner任务 |

这里的根因不是简单“任务太多”。M21有明确T1/T2成员依赖时正确合并；M23/M24表明错误来自观察前猜测和语义默认。Plan需要能够先
保留unresolved collection/compute节点，观察后再由RWKV提交continuation；缺失semantic field必须与显式空集合区分。

### 2.3 执行与状态：action忠实，但task语义和数据谱系断裂

#### A. task title/effect不一致

- M13“sort/verify CSV”选择`read_json`；M15 compute-all退化为reader；M28“move files”选择写report；M30“apply migration”也选择写report。
- Harness正确执行了RWKV所选action，但Controller没有核对action effects能否推进task declared effects，仍可能把task标记completed。
- 不能靠规则替模型改工具或参数；可在执行前把effect mismatch作为typed observation返回RWKV。

#### B. 纯计算没有typed result

- M15 line-count计算、M25 parse/sort、M27 ready-set演化、M29 key partition/fallback、M30 migrated config都没有独立可持久化的纯值结果。
- 模型只能用reader冒充compute，或过早写最终artifact；后继看到的只是“JSON written”或错误artifact snapshot。
- M30是明确回归：Round21直接source→config时保住metadata、版本和毫秒转换；Round22拆成compute→write但compute没有typed handoff，
  T4丢source后生成通用timeout模板。

#### C. 只投影直接依赖会丢仍然必要的源

- M16 recovery选中的真实path未commit为后继typed state；M28 T3只依赖T2后看不到T1 cutoff，报告从Round21正确分类退化；M30 T4只看
  T3 report而丢MIGRATION/config。
- M11/M17的pre-state没进入member writer，导致preservation任务覆盖真实字段。
- 需要传递的是有locator、attempt、source hash、selected relation的typed state，不是把全部历史原文无限塞回prompt。

#### D. 同artifact多writer互相覆盖

- M07重复whole-file merge；M12 T4从旧base覆盖T3正确zero check；M14并列JSON/Markdown producer没有共享canonical lineage；M24两版
  queue实现互相覆盖；M26三个“valid/rejected/count”task都全量写validation；M29/M30后继全量重写切断source。
- 这些不是幂等性问题，而是缺少artifact-level read/write set、base digest和writer顺序。后写成功不能证明前一能力从未出现。

### 2.4 RWKV本身仍存在的生产错误

架构缺陷不能替RWKV免责。以下错误发生在相关输入完整可见时：

- M02同时看到实现和test仍原样写回错误代码；M05看到source仍生成通用requirements。
- M07完整看到base/override仍漏top-level override；M09看到旧import仍只改调用。
- M14对同一排序关系生成正确JSON、错误Markdown；M22完整看到config/policy/request仍未应用允许值且未保留untouched值。
- M25只在第二个version group漏排序并多一个newline；M27只在动态available tie-break错一步。
- M29正确识别base-only差集，却不materialize fallback values并把missing_keys逆序。

这些case显示当前13.3B RWKV的主要能力边界是多阶段关系、动态state更新和局部约束一致性，而非单纯读不到文件。结构改造应该把复杂
变换分成模型明确选择的typed state transitions，使错误可在局部被观察和修正；不能由Controller代算最终答案。

## 3. 验证：必须保留防作弊gate，但重建独立关系证据

### 3.1 当前正确的防线

- M21正确产物中，RWKV把actual/expected绑定同一handle；same-target gate拒绝是正确的。若删除，错误循环证明会把FN伪装成成功。
- M25把当前read output与前一reader artifact绑定，二者都来自同一模型写入CHANGELOG；same-lineage gate正确拒绝。
- hidden acceptance始终隔离；不能因External后验正确就在线标记完成或给RWKV答案。
- M25的unchanged deterministic obligation suppression成功阻止重复T6 reader，证明material observation缓存方向有效。

### 3.2 当前错误的“验证”

- M02/M05/M07/M08/M12/M17/M22/M25/M26/M28/M30等题的task-local exact verifier把expected直接取自本次write payload；它只验证
  payload fidelity，却让错误producer显示completed。
- 大量Verify task只读target，不同时依赖source：M14只读JSON判断双输出agreement；M27只读order不读graph；M29只读resolved output不读
  base/locale。单边观察无法证明二元/多元关系。
- action cross-check被设计为optional，协议或proof失败后task仍completed；task completion、criterion completion和semantic progress混用。

### 3.3 缺失的不是更多硬编码verifier，而是关系所有权

需要由RWKV明确选择：

- actual source、independent expected source；
- 需要应用的关系/transform及其参数；
- 关系产生的typed intermediate或可执行claim。

Controller只负责检查provenance独立性、忠实执行已登记关系、保存raw/normalized/result；不得从hidden标准或源码内容自行选择关系。
M21的source_b precedence、M25的group/sort/render、M27的ready-set transition、M29的override/fallback都是此类关系。最终关系接口的具体
最小集合仍需Hard 30题验证，当前不预先确定。

## 4. Recovery：从错误producer修正退化为reader expansion

### 4.1 已反复出现的放大链

1. producer输出错误或正确但无proof；
2. action success使producer/task completed；
3. obligation只看到criterion未覆盖；
4. RWKV新增“Verify/Validate”reader；
5. reader只读同一target，或甚至选择writer重写同一payload；
6. internal task/history变化使下一轮看似有新state，material evidence实际不变；
7. budget耗尽或某次G1i外壳错误终止。

M14、M21、M27、M29是最清晰的长链；M25展示了正确suppression反例。M23 Round21→22从27降至9 task、M27从30降至13 task，说明
限制放大有效，但只减少成本，没有修首个错误。

### 4.2 failure fingerprint与能力反馈仍不可靠

- M10/M13对相同确定性失败重复reselect同reader；M24第二、三次action fingerprint相同仍重跑不存在的`python`。
- M24的模型只看到解释器缺失，从未看到unittest的`add`错误；不能说模型拒绝修复它没收到的反馈。
- M13需要media type/capability；M24需要真实Python locator。环境能力缺失应在action选择前协商，不能让模型把基础设施错误当业务错误分析。

Recovery必须按失败层级路由：Goal冲突回Goal、Plan coverage/owner缺失回Plan、producer关系错回producer、协议字段错做local typed repair、
外部能力缺失走capability resolution。新增reader不是通用恢复动作。

## 5. 协议外壳：高频，但通常不是最终正确率根因

Medium中出现`function/function_call/tool_calls/action`等外壳、缺固定schema/task_id、witness多余字段及WH/WS ID混淆。M09、M21–M23、
M26、M28–M30均有明显实例。

可安全恢复的边界是预注册、唯一、透明且不生成语义字段：例如已选action type后展开`function_call{name,arguments}`，或tool-choice只缺
固定schema/task_id。以下情况不能自动修：

- M26/M28响应只有`model_action`或缺path/value；
- M30外壳内部config语义严重错误；
- witness actual/expected选择错误或同lineage；
- 任何需要补文件成员、criterion、参数值或最终答案的情况。

因此协议归一化能减少不必要blocked，但必须与payload质量指标分开；不能把“请求执行成功”当“任务更正确”。

## 6. Round21→Round22的真实进步与回归

### 6.1 真实进步

- M22从`Alice/New York`等通用模板改为使用真实config/policy/request，虽关系仍错。
- M23把网页模板的恢复放大从27 task降至9 task。
- M25从十个虚构版本改为四条真实input，错误缩为局部排序/newline。
- M26保住真实记录、2/2计数和部分reason，未继续生成完全不同schema。
- M29保住真实locale values与正确missing集合，不再被`greeting/farewell`模板覆盖。

这些进步说明紧凑action catalog、依赖内容投影和部分恢复抑制确实提高grounding，不能在下一轮无差别回退。

### 6.2 明确回归

- M24 Round21 writer至少读取source并保留`add`；Round22 dependencies缺失默认空后reader饿死，最终公开接口消失。
- M28 Round21 T3直接看cutoff时report分类完全正确；Round22只投影T2后cutoff丢失，报告退化并幻觉08-10。
- M30 Round21直接source→config时保住metadata/版本/毫秒转换；Round22 compute→write无typed handoff，config完全未迁移。

这些回归共同证明：减少context不是越少越好，增加task也不是越细越好。必须保留与当前关系有关的typed source state，且只有在有真实
handoff时才拆分compute/write。

## 7. Medium阶段形成的待Hard验证结构假设

以下只是待验证假设，不是Round23预注册方案：

1. **Goal表示假设**：取消任意小criterion上限，或让RWKV用局部merge保持hard-obligation coverage，可消除0-action与M27语义丢失，
   但需测长Goal对弱模型prompt负担。
2. **阶段性Plan假设**：先计划观察/能力获取，再根据RWKV观察结果提交continuation，可减少M23式观察前成员幻觉；必须审计每次成员选择，
   不能由Controller自动fanout。
3. **语义字段fail-closed假设**：dependency、criterion owner、source/effect等字段缺失时局部纠错，优于默认空值；需测是否增加协议block。
4. **typed state假设**：保存value+locator+attempt+hash+relation的精简状态胶囊，可同时避免M28/M30 source丢失与无限历史膨胀。
5. **artifact ownership假设**：同目标writer显式串行并校验base digest，可减少M12/M24/M26覆盖；需防止把模型不同候选错误合并。
6. **关系证据假设**：RWKV选择source与transform、Controller只执行/验证，可闭环M21正确产物并为M25/M27/M29提供局部反馈，且不修改
   RWKV答案。
7. **分层recovery假设**：material observation+failure fingerprint不变时抑制相同reader/verifier，转向最早未闭合producer；外部/时效状态
   不使用该缓存。
8. **capability negotiation假设**：执行前暴露media type、可用解释器/命令locator，可把M13/M24基础设施失败与业务错误分离。

这些假设是否覆盖Hard题、是否互相冲突、最小可实现组合为何，必须等H01–H30逐题分析后再决定。

## 8. Medium阶段的防作弊结论

允许的架构帮助是保存、路由和忠实执行RWKV自己的决定：

- 保留source成员、locator、bytes/hash、typed intermediate和失败反馈；
- 对固定协议元数据做透明归一化；
- 检测矛盾、缺字段、同lineage、stale base和effect mismatch后要求RWKV重提；
- 执行RWKV明确选择的relation/action并独立记录结果。

不允许的做法是：

- 按hidden acceptance自动生成字段、成员、排序、代码或最终JSON；
- 删除same-lineage gate，或把action payload自身当目标expected；
- 用Controller规则选择“正确”工具/文件/branch并绕过RWKV；
- 在读取单题hidden失败后在线修改策略使该题通过；
- 修改、补全、替换或重排RWKV最终答案。

Medium 30题支持的目标仍是让RWKV拥有更完整、低噪声、可恢复的状态与协议，使它自己的正确决策更容易落地、错误决策更早获得真实反馈，
而不是由辅助模块替RWKV完成任务。
