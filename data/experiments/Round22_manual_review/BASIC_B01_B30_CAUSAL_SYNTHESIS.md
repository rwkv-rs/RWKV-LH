# Basic B01–B30 完整因果合成（仍非 Round23 方案）

## 1. 分析边界与事实口径

本文件建立在30份逐题人工记录之上，不用聚合结果替代因果判断。每题均先从visible request、Goal raw、Plan raw、
action raw、真实workspace与terminal向后重建，再连接External标准答案；跨题统计只用于检验模式是否重复。

- Basic 30题中External PASS 17、External FAIL 13、Strict PASS 0、agent completed 0、final answer非空0。
- materialized task共222个。按event log中真实`model_request_started`计837次请求；另有29次在run创建前的Goal
  request只存在于model trace/decision记录，因此完整model调用口径为866次。B12的2次Goal请求也只存在于model trace，
  因Goal materialization失败没有run/event log。
- 17个External PASS全部是completion false negative；13个External FAIL均在Goal/Plan/Action或后置mutation中已有生产偏离，
  不能归因于最终proof过严。
- 30题的criterion evidence总数均为0。这不是单纯“证明模块失败”：有些题从Plan开始就没有claim owner，有些artifact错误，
  有些关系不可表达，有些有表达能力却选择错误source/handle。

## 2. 从最终错误向前追：13个External FAIL的首因并不相同

| Case | 最终错态 | 首个决定性偏离 | 后续放大链 |
| --- | --- | --- | --- |
| B04 | 正确manifest被覆盖成JSON string | vague verify task可以选择破坏性`write_json` | direct-only状态丢正确T4；action自证；166次请求级恢复扩张 |
| B09 | stats absent | Plan先违反header非data，再把无工具落点的计算拆成tasks | read_json(CSV)；恢复发明read_csv/read_text；block |
| B11 | source受损、target absent | Goal objective prompt echo；Plan把pure transform变source mutation | 无pre/post canonical content；后继猜old text；block |
| B12 | 无任何action/artifact | Goal把单outcome拆成8 criteria，违反max5 | correction重放全错误输出；RWKV逐字重复；Goal hard stop |
| B14 | concat多一个尾换行 | RWKV在right已有尾换行后再加一个 | dependency边界不显式；action self-check；proof无concat关系 |
| B16 | env仍有blank | T2 task要求删comment+blank，单次action只完成一半 | generic success把部分动作升completed；后续错位/no-op继续完成 |
| B21 | totals absent | Plan虚构parse/inspect/aggregate/sort action并错绑output-exists | read_json(CSV)；恢复执着不存在read_csv；type/action两阶段冲突 |
| B22 | TASKS.md absent | source→producer→verifier依赖全缺，priority先跑verifier | recovery文字知道缺producer却反复read absent target；外壳block |
| B23 | selected.json absent | fallback图硬依赖primary parse task“成功” | expected JSONDecodeError被当fatal；fallback ready却饿死；预算耗尽 |
| B24 | source被破坏、target absent | pure dedup被实现为对source的remove_line | task局部语义未验证；post-content丢失；后继无输入生成失控序列 |
| B25 | nested merge被扁平 | Goal criteria先丢`runtime.*`父路径 | Plan/Action跟随flatten；action自证；proof若放宽会转FP |
| B26 | a/b存在、c缺失 | T4把mkdir+write塞入一个single-action task | make_directory成功即completed；恢复69次主要重复list而不补producer |
| B27 | 只替换1/3处 | `count=-1`违反positive contract却被runtime静默coerce为1 | replace postcondition过弱；reader无claim；12个only-advance obligation |

这13题至少包含六种首因：Goal语义污染、Plan不可执行、数据/控制依赖缺失、Task/action粒度不闭合、action参数语义不一致、
RWKV具体值/表示生成错误。terminal protocol block、priority crash或budget exhausted只是在后面终止链条，不能作为统一根因。

## 3. 17个External PASS为什么仍全部无法完成

### 3.1 Claim入口在执行前就不存在或不完整

B01/B02/B03/B05/B07/B08/B15/B18/B19/B20/B27/B28/B30等存在required criterion没有任何初始
`satisfies_criteria` owner，或正确producer只advance不satisfy。B19的SHA relation已有operator、B30代码也真实通过测试；但
没有producer claim就不会进入正确的evidence路径。这证明“production正确”和“证明失败”之间还有一层Plan ownership gate。

相反，B21显示只强制ID覆盖也不够：parse/inspect/aggregate/sort四个不会创建output的task都虚假claim output exists。
因此需要审计的是“task-local observable postcondition是否足以建立criterion”，不是criteria ID是否出现过。

### 3.2 独立source在Plan或状态投影中丢失

B06/B07/B13/B15/B17/B18/B20/B28/B29的后置reader只依赖model-written output，source/pre-state/test definition不再作为
直接dependency可见；读回正确target只能证明write/read一致，same-target lineage拒绝是正确行为。B22是更早的极端：producer
与consumer根本没有edge，scheduler先执行不存在target的verifier。

状态问题同时有“太少”和“太多”：B24的mutation只留下`removed 1 line(s)`与hash，后继丢实际content；B08则把failed和
successful attempt、whole object与leaf共139+ handles等权展开，RWKV选到failed empty hash。权威audit store必须完整，弱模型
当前视图却需要canonical projection；两者不能继续视为同一种内存。

### 3.3 所需关系在proof语言中不可表达

- B02：key=value parse、string→number、multiply；
- B06/B14：concat及尾换行边界；
- B07：negative path/alternate absence；
- B13：JSON pre/post排除指定path后的相等；
- B15：stable unique；
- B17：filter/project/count；
- B18：multiply/subtract/round；
- B28：key=value→typed exact JSON。

但“扩大operator集合”本身不是答案：B19已有SHA operator却因无claim不启动；B08有正确digest handles却选stale source；
B25若在Goal path错误时只增强leaf proof，可能把错误flat JSON判对。必须先分清Goal grounding、claim/source reachability、
operator expressiveness和模型selection四层。

### 3.4 运行能力实际存在但没有协商给模型

B20/B30均在代码正确后用`python`运行测试失败；Harness沙箱实际只有`python3`。抽象command schema没有列出真实toolchain，
ENOENT observation也没给可用候选。B20 failure analysis一度提出python3但下一G1i丢失，B30则误判为需要apt安装；两题最后都
由action wrapper协议错误终止。末端wrapper不是首因，首因是模型被要求选择一个未声明实际可执行能力的argv。

## 4. 一条错误如何被各层逐级放大

跨30题最稳定的共同链条不是某个功能，而是“弱模型的暂时提议被过早升级成权威完成状态”：

1. **Goal proposal冻结**：B10的pytest、B25的flat paths、B29的“newline是第二行”一旦进入Goal，后续Plan/Proof都会把它当
   immutable；B11/B18/B24还出现objective复制协议instruction。
2. **Plan只验证schema/DAG**：B21不可执行nodes、B22缺producer edges、B23条件分支不可达、B26复合task、B27零claim均被保存。
3. **Action success提升Task completed**：B16只删一半、B24删错source、B26只mkdir、B27只replace一次都被标completed；
   B04的后置“verify”甚至可再次mutation正确artifact。
4. **状态投影改变下一次RWKV所见事实**：缺source/pre-state/test会迫使模型自证或猜值；堆叠stale handles又扩大错误选择空间。
5. **Proof失败没有回到最早缺口**：unassigned producer、missing dependency、unexpressible relation、wrong handle、wrong artifact
   都常被折叠成“unresolved criterion”，obligation默认增加output reader。
6. **Recovery扩张后协议稳定性下降**：大capsule/重复结构诱发stage-ahead echo、ACTIVE TASK/G1i wrapper、wrong WS/WH IDs、
   `priority:"high"`；异常有时绕过correction并终止整个run。

因此当前缺陷不是“RWKV总答错”，而是系统没有在每层保留proposal、observation、task-local establishment和Goal evidence之间的
等级差。弱模型早期的小错误会被下层当事实重复，而正确中间结果也可能被无约束后置任务覆盖。

## 5. 成功/失败对照给出的反例约束

| 过早方案 | 反例 | 能确认的更底层问题 |
| --- | --- | --- |
| 删除same-target/self-proof gate以减少FN | B04/B16/B25/B27的错误target也可自证 | 必须先恢复独立source和正确Goal；gate本身防止FP |
| CSV题就新增`read_csv` | B09最终已识别text路线；B21后续aggregate/sort仍是虚构nodes | Plan action-feasibility与恢复catalog grounding，而非单工具数量 |
| 所有plan先做hard coverage gate | B12在Goal correction处0-action；B21有虚假full coverage | gate需返回局部、可执行的RWKV correction，不能只看ID或直接停机 |
| 任务拆得越细越适合弱模型 | B17 scratch files、B16/B24串行mutation、B26复合/重复reader都放大lineage | 只保留带新observation或独立evidence ownership的步骤 |
| 扩大proof operator即可完成 | B19 operator存在但无claim；B08有handles却选failed；B25 Goal先错 | 先保证criterion正确、producer claim、source可达，再评估最小表达集 |
| terminal protocol error就是首要瓶颈 | B04 terminal前已覆盖正确文件；B30先ENONENT后才wrapper退化 | 协议边界要修，但不能掩盖上游语义/能力缺口 |
| 规则看到明显依赖就自动补edge/producer | 会改变RWKV的计划与分支决定，违反不作弊边界 | 规则只能拒绝矛盾/记录缺口，修正Plan仍由RWKV提交 |

## 6. Basic阶段已经确认的结构职责边界

这些是30题共同提出的结构要求，不是最终实现顺序；Medium/Hard仍可能改变优先级或揭示冲突。

1. **Goal层**：original request保持唯一事实锚；RWKV派生criterion要带request-span/typed path/条件语义的可追溯性，并由
   RWKV纠正冲突。Controller不得静默合并、删除或改写criterion。
2. **Plan层**：每个node需要声明一项未来可用action capability、输入artifact refs、side-effect scope、task-local
   observable postcondition和criterion relation；保存前审计one action可闭合性、producer-consumer可达性、条件分支及
   claim scope。审计只发回缺口，不替RWKV补图。
3. **执行状态层**：严格区分`action_executed`、`task_postcondition_established`、`criterion_evidenced`；禁止silent coercion和
   vacuous postcondition；mutation需保留pre/post lineage，验证task默认不能自由获得写/delete capability，除非Plan明确声明。
4. **Observation/Memory层**：SQLite/audit继续append-only保存全部历史；模型当前视图只投影canonical latest-success、必要pre/source
   和失败差异，按需展开stale history/transforms。文本必须显式保留bytes/尾换行/truncation边界。
5. **Evidence层**：proof输入由Plan的producer relation驱动，先选语义source再按需展开typed handles；operator只覆盖跨90题
   高频且可审计的确定性关系。External acceptance永不作为运行时证据，Controller不生成答案或补semantic参数。
6. **Recovery层**：failure要分类为Goal grounding、Plan feasibility/coverage、producer partial/wrong、missing observation、
   capability mismatch、proof unexpressible、source selection、protocol syntax等；恢复回到首个未建立层，并让RWKV提交修正。
   unchanged deterministic observation不应继续消耗相同action，ready fallback/producer也不能被一个失败task永久饿死。
7. **协议与运行层**：每个request只有一个输出schema；parser/类型错误全部进入同一可审计correction lifecycle；command action
   需要公布真实注册toolchain capability；reason、decision和next target要在结构上保持同一失败层。

## 7. 仍不能在Basic阶段决定的事项

- Goal/Plan审计采用一次综合request还是分层小request；硬拒绝、软标记、局部修订哪种对弱模型成功率最高。
- 是否扩充action工具，还是主要压缩Plan为read→single producer→check；必须看Medium/Hard是否需要真实中间状态与fan-out。
- proof最小operator集合、统一source/handle协议、canonical projection能减少多少请求且是否损失历史恢复能力。
- conditional task/outcome-as-data、rollback/compensation是否在复杂任务中足够，是否需要新的state transition。
- capability negotiation应公开命令白名单、解释器alias还是运行环境profile；不能仅用B20/B30决定接口。

因此下一步仍是逐题审阅Medium M01–M30，再审阅Hard H01–H30。只有90题首因链、放大链和成功反例全部连接后，才会把
上述结构要求收敛成最小Round23改造、预注册消融顺序和回归指标。
