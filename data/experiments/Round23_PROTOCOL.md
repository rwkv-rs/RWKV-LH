# Round23 预注册协议：透明协议边界闭环

> 状态：`preregistered_implementation_in_progress_not_run`。截至本文及下述运行前勘误冻结时，没有发出任何Round23 RWKV请求，也没有读取任何Round23 hidden acceptance。

> 运行前勘误 `2026-08-13/pre-replay-1`：首版条目把单项`tool_calls`只写成OpenAI嵌套`function`形状；实施后的Round22冻结raw逐条复核确认H07使用该形状，而M09使用单项直接`name/arguments`形状。人工case文档此前只将M09记为`tool_calls wrapper`，没有把这两个wire variant明确分开。由于尚未运行Round23、尚未生成Round23结果，本协议在运行前明确增加第二种精确形状；其他白名单、评价指标和门禁不变。此勘误是对已冻结Round22 raw的协议分类修正，不读取答案，也不按arguments正确性选择接受。

预注册日期：2026-08-13。Round23只实施全90题架构指导中的Stage 1a，不同时修改Goal语义、增量Plan、Task完成语义、state capsule、proof或recovery scheduler。此前“workspace observation协议不相交”候选已经在运行前被90题人工证据否决并完整保留于
[`Round23_ABORTED_PROTOCOL_DISJOINT_OBSERVATION.md`](Round23_ABORTED_PROTOCOL_DISJOINT_OBSERVATION.md)。

## 1. 冻结基线与因果依据

Round22冻结结果：

- External `19/90`；Strict `0/90`；Agent completed `0/90`；FP `0`；FN `19`；全部final output为空。
- Basic `17/30`、Medium `1/30`、Hard `1/30`。
- 历史FP=0条件下的External最好结果是Round16 `24/90`，但Strict与Completed仍均为0。

Round23变量不是从终端`blocked`计数推断。它来自90题逐题raw → parsed → normalized → Controller → Harness链中的可直接复放事件：

- H02和LH07的RWKV输出含唯一、完整的`task_graph.tasks`数组；现有代码已经识别并提升该数组，却因同一已登记外壳缺少顶层`schema_version`而整体拒绝Plan。
- LH02的step02 action中，selected tool与inner action type均为`write_json`，arguments包含正确path/value；只因外层是`action.type+arguments`而停止正确15跳生产链。
- H01、H06、H13等题在selected tool唯一时返回`action_type+arguments`；M09、H07返回单项`tool_calls[0].function`；这些外壳中的action identity和arguments可以在不生成语义字段的前提下唯一提取。
- B03、B05中第一次`invoke_tool_call`的parser/normalizer异常发生在`propose_action`纠错循环之外，因此源码虽写了两次attempt，实际没有第二次同类型请求。
- B08、B11、LH06、LH09证明现有`function_call`、typed function及JSON-string arguments透明归一化能保留原始参数并让真实Harness继续执行；这是一组必须保留的正向对照。
- M30、LH08等题中的inner type为`model_action`、参数未放入arguments、或字段冲突；它们不能因为外壳相似而被自动修成selected tool。

完整逐题证据与跨题边界已经冻结在`data/experiments/Round22_manual_review/`。Round23只检验一个可证伪命题：

> 当RWKV已经唯一表达同一个Plan task array，或已经唯一表达selected Harness action及其原始arguments时，协议边界必须从识别、归一化、schema校验到纠错闭环；无语义外壳差异不能提前终止执行，但任何歧义、冲突或缺失语义仍必须失败关闭并交回RWKV。

## 2. 唯一结构变量

名称：`transparent_protocol_boundary_closure.v1`。

这个变量由三个不可分割的协议边界步骤构成：注册无语义外壳、完整闭环其schema身份、让parser/normalizer错误真正进入既有同类型纠错attempt。三者不改变任务、action或答案语义。

### 2.1 Plan envelope闭环

canonical Plan仍为：

```json
{"schema_version":"long-horizon.plan.v2","tasks":[...]}
```

只允许以下注册外壳：

1. canonical顶层`tasks`；
2. 顶层`task_graph.tasks`且值为非空array；
3. 顶层`task_graph.nodes`且值为非空array，并且每个node显式包含`dependencies`。

归一化规则：

- 若顶层已有`tasks`，不得再从`task_graph`选择候选。
- `task_graph.tasks`与`task_graph.nodes`同时存在、存在多个task array、或任何候选类型错误时失败关闭。
- task array逐对象、逐字段、逐顺序原样提升到canonical `tasks`；不得补task field、dependency、criterion、priority、retry、成员或edge。
- 若外层已声明`schema_version`，只能为已支持的plan v1/v2；冲突版本失败关闭。
- 若注册的`task_graph.tasks/nodes`外壳没有`schema_version`，normalizer登记
  `registered_plan_envelope_implies_v2`并加入固定协议身份`long-horizon.plan.v2`。这只闭合同一已注册wire envelope，不推断任务语义。
- raw payload、normalized payload、transform list、normalizer version和两者canonical digest全部保存。
- 归一化后继续经过现有Task字段、TaskGraph、action arity和criterion ID校验；透明接受Plan不代表Plan语义正确。

### 2.2 G1i单调用外壳闭环

canonical action call仍为：

```json
{"name":"<selected_action>","arguments":{...}}
```

在现有canonical、`function_call`、typed function和`function+arguments`之外，预注册以下外壳：

1. `{"type":"function","name":name,"arguments":args}`；
2. `{"action_type":name,"arguments":args}`；
3. `{"action":{"type":name,"arguments":args}}`；
4. `{"tool_calls":[{"type":"function","function":{"name":name,"arguments":args}}]}`，单项可以带一个不参与语义的字符串`id`；
5. `{"tool_calls":[{"name":name,"arguments":args}]}`，单项可以带一个不参与语义的字符串`id`。

所有新增外壳必须同时满足：

- 当前`tool_action`请求已经有且只有一个selected Harness action；
- wrapper中的`name/type/action_type`逐字符等于selected action；`model_action`不能替代selected concrete action；
- 只有一个call候选，不混用canonical与wrapper字段，不存在冲突字段；
- arguments为object，或为可解析成object的JSON字符串；内部key/value/array顺序按解析结果保留，不补path、argv、content、value、cwd等任何参数；
- `action`内把path/content等放在arguments之外、`tool_calls`长度不等于1、缺name或arguments、额外语义字段、多个identity不一致时失败关闭。

normalizer只删除注册wire envelope并产生canonical view。raw、normalized、transform list、selected action、normalizer version和digest全部进入审计。Harness仍对canonical action执行原有scope、argument schema和安全校验。

### 2.3 同类型局部纠错闭环

只修改`task_decomposition`和`tool_action`两种request的协议异常控制流：

- JSON extraction、registered-envelope normalization、schema validation和Harness action-contract validation中的任何异常都必须落入该request已有的最多两次attempt循环；不能在第一次parser/normalizer异常时逃出循环。
- 第二次request保持相同request type、Task、Goal、selected action、capability contract、temperature policy和输出预算类别。
- correction只返回typed failure stage、JSON pointer/field、expected shape和不超过512字符的局部invalid fragment；不再粘贴4K/8K完整旧输出。
- 两次均失败后仍按Round22既有终止语义block；Round23不修改task-local/global scheduler，以隔离协议边界变量。
- `finish_reason=length`且外层JSON不完整时保持失败关闭；不得从嵌套arguments或截断fragment拼出完整Plan/action。

## 3. 明确不修改

Round23不修改：

- Goal prompt、`max-5`限制、criterion拆分/合并、原始request权威关系；
- Plan任务内容、missing dependencies默认值、priority语义、静态DAG大小、任务排序或criterion coverage；
- 两阶段action type选择策略、action catalog、tool选择结果、sampling参数；
- Harness能力、runtime alias、命令、workspace scope、action参数或真实tool result；
- Task状态、action success/completion/evidence关系、proof/witness、obligation、failure fingerprint、recovery budget或全局block；
- workspace observation/memory projection、artifact、RWKV raw/final output；
- benchmark、standard answer、hidden acceptance或评分实现。

这些已确认缺陷依次属于后续Stage 1b–6，不能混入Round23后再把得分变化归因于协议闭环。

## 4. 不作弊边界

- normalizer只能处理本文运行前列出的wire envelopes，不能根据case ID、文件内容、标准答案、External结果或参数正确性选择是否接受。
- selected action identity必须来自RWKV先前真实choice；wrapper identity不一致即拒绝，Controller不能把`model_action`替换为selected action。
- Plan schema identity的固定补入只适用于本文精确定义的完整`task_graph.tasks/nodes`注册外壳；bare Task fragment不能升级为Plan。
- 不生成、删除或改写task语义、dependency、criterion、member、priority、action、argument、value、branch、code、answer或最终文件。
- raw model output永久保留；normalized view是独立审计对象，不覆盖raw，更不修改RWKV final output。
- 不尝试多个可能解释并选择能通过Harness/External的候选；候选不唯一立即失败关闭。

## 5. 运行前验证

### 5.1 单元与对抗测试

- 每个注册Plan/action外壳各有raw → expected canonical → exact transform list测试。
- canonical幂等：canonical输入不得发生字段变化；重复normalization结果相同。
- JSON-string arguments仅做JSON decode，decode前后参数canonical digest一致。
- action selected-name match、single candidate、unknown/mixed/conflicting fields、extra action-level parameters、zero/multiple tool calls全部失败关闭。
- Plan双task-array、unsupported version、bare task、缺Task语义字段、冲突顶层tasks、截断JSON全部失败关闭。
- 首次parser/normalizer异常确实触发第二次同类型request；第二次prompt不包含完整旧输出；两次均错仍block。
- 每次normalization事件同时包含request ID、raw、normalized、transform list、version和digest；`controller_semantic_fields_generated=false`。

### 5.2 冻结Round22 replay

在不调用RWKV、不执行Harness的条件下，对Round22全部`task_decomposition`和`tool_action` raw payload复放：

- 保存每个request的旧parsed/normalized/outcome与Round23新outcome；逐条人工检查所有outcome变化。
- 所有新accepted payload必须满足唯一注册外壳，canonical action arguments或Plan task array与raw来源逐字段相等。
- B08、B11、LH06、LH09等现有accepted wrapper结果保持不变。
- M30、LH08及全部identity冲突、参数越层、mixed fields案例继续拒绝。
- 输出完整replay manifest、raw/new digest、transform、case/request/task定位和零semantic mutation证明。

### 5.3 产品回归

- 完整pytest；离线protocol/state固定集`112/112`；LH-Control `30/30`；E2E-90 validate-only。
- 不仅运行新增测试，还运行Goal/Plan/action、proof、snapshot、store save/load、并发/恢复和Web UI相关历史回归。

只有5.1–5.3全部通过并冻结hash后，才允许发出第一个Round23 RWKV请求。

## 6. 正式E2E-90实验

- endpoint：`http://127.0.0.1:29610/v1`；model：`rwkv7-g1i-13.3b-20260805-ctx16384`；context `16384`。
- Basic/Medium/Hard各30；固定dataset version、case hash、初始workspace、并发8、max transitions 200、sampling、timeout和Round22其他参数。
- 90题全部终止前不读取Round23 hidden acceptance、standard answer或Codex reference。
- 完整保留：每个prompt、model raw、finish reason、parsed payload、normalization、correction、TaskGraph、Harness input/result、workspace revision、artifact hash、memory projection、proof/evidence、recovery和terminal state。
- 先冻结所有score-independent结果与hash，逐题检查protocol变化后，才连接90题标准答案并生成`CAUSAL_ANALYSIS.md`、`causal_analysis.json`、`STANDARD_ANSWER_COMPARISON.md`和`STRUCTURE_CHANGE.md`。

## 7. 预注册评价指标

### 7.1 首要因果指标

1. 首次parser/normalizer错误后获得第二次同类型request的比例；
2. 注册外壳raw → canonical成功数与按transform分类；
3. normalization semantic mutation数，必须为0；
4. formerly blocked case到first Task/first Harness/next producer的reachability变化；
5. transparent acceptance后RWKV producer本身正确、错误和未到达的逐题分类；
6. protocol model requests、重复相同raw、输出length及总token变化。

### 7.2 全局结果

- External、Strict、Agent completed、FP、FN；Basic/Medium/Hard分组；
- first source observation、first producer、first verifier、CriterionEvidence与Goal closed的case数；
- Harness attempts、model requests、blocked/interrupted/not_created、side-effect cardinality；
- 与Round22、Round16以及相同case历史最好artifact的预登记相似度比较。

协议接受率上升而producer错误增加，不算架构正确率改善；External上升而FP、Strict或审计完整性回归，也不能晋级。

## 8. GitHub晋级与回滚

恢复FP约束后，以Round16作为当前FP=0的Pareto检查点。Round23只有同时满足以下条件才提交并上传GitHub：

1. FP=`0`，normalization semantic mutation=`0`，所有运行前回归通过；
2. External `>=24`、Strict `>=0`、Completed `>=0`，三项均不劣于Round16；
3. External `>24`、Strict `>0`或Completed `>0`至少一项严格改善；
4. 改善case的完整raw → normalized → execution → artifact/evidence因果链可复核，且不是hidden信息、规则代答或评分口径变化。

若不满足，完整保留Round23实验与分析，标记`do_not_upload`，回滚行为变量后再预注册Round24。不得运行后修改normalizer白名单、metric、threshold或晋级条件。
