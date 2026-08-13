# Round24 预注册协议：紧凑因果 Task 提交链

> 状态：`preregistered_implementation_in_progress_not_run`。本文冻结时尚未发出任何 Round24 RWKV 请求，
> 尚未读取任何 Round24 运行产物或 hidden acceptance。

预注册日期：2026-08-13。因果依据为
[`Round23_manual_review/CROSS_90_CAUSAL_SYNTHESIS.md`](Round23_manual_review/CROSS_90_CAUSAL_SYNTHESIS.md)
及其连接的 90 题逐题记录。Round24 不声称一次修完 collection、typed branch和Goal proof；它先建立这些能力必须依赖的
紧凑状态主干。

## 1. 冻结基线

- Round23：External `17/90`、Strict `0/90`、Completed `0/90`、FP `0`、FN `17`。
- 难度：Basic `14/30`、Medium `2/30`、Hard（含LH）`1/30`。
- Round22：External `19/90`；Round16 是当前 FP=0 的 External 最佳点 `24/90`。
- Round23 相对 Round22 新增 B04/M01/M18，丢失 B01/B07/B10/B15/M21。

Round24 检验一个可证伪命题：

> 如果每个 ready Task 的模型输入只包含当前因果状态，RWKV 在一次 action commitment 中同时提交 tool identity 与原始
> arguments，并且 action effect、Task postcondition、Goal evidence不再共用一个完成位，那么局部正确 action 更少因协议重复
> 或旧历史而丢失，局部错误 effect 也更少被放大为后续依赖已满足。

## 2. 唯一结构变量

名称：`compact_causal_task_commit.v1`。

它由三个不可分割部分组成：current-state capsule、原子 action commitment快路径、三层 Task提交状态。缺少任一部分都会继续
让同一次语义决定在旧历史或单一 completed bit中失真。

### 2.1 确定性 execution capsule

SQLite状态、事件、raw prompt/output和artifact历史继续 append-only保存；只改变模型输入投影。

对一个 active Task，capsule只含：

1. immutable Goal digest、original request、constraints，以及该Task显式绑定的 criterion；若Task没有绑定，保留Goal原始请求但
   不展开全部旧proof状态；
2. active Task 的 id/title/description/direct dependencies/criterion bindings/current action/attempt count；
3. 每个直接 dependency 当前 `output_refs` 中的最新 action result、post-action snapshot及artifact locator/hash；不扫描该dependency
   的旧attempt，也不注入其他Task的evidence；
4. active Task recovery lineage 的最新 material failure、failure fingerprint和remaining budget；不展开完整decision history；
5. 当前请求必需的compact action catalog或唯一tool schema。

projection必须保存 capsule schema/version、canonical digest、selected/excluded memory IDs、各section token和总token。Goal与active
Task不可截断；超预算时按 general evidence → dependency content（保留hash/locator）→ optional contract顺序裁剪。不得用模型自由
摘要代替数据库事实。

### 2.2 原子 action commitment快路径

当前两阶段协议先要求`action_type`，再要求同一RWKV填写arguments。Round24改为：

- 第一次请求给compact action catalog，明确要求一个完整 G1i-compatible `{name, arguments}`；tool name与arguments均由RWKV在
  同一raw输出中提交。
- compact catalog只列运行时已有action的名字、description、read/write/side-effect属性、argument names和required names；不补值、
  不排序候选、不按case筛工具。
- normalizer只接受Round23已登记的唯一调用外壳，完整保存raw/normalized/transform/digest。Harness继续执行全部argument、scope、
  command和safety校验。
- 如果RWKV只返回旧版合法`action_type`承诺，允许进入现有单tool G1i参数请求，作为渐进披露兼容路径；Controller不能改变该type。
- 如果完整call的name唯一有效但argument contract错误，第二次局部纠错只展示该name的唯一tool schema、typed error和不超过512字符
  fragment。不得丢弃第一次完整call后重新做无约束tool choice。
- 完整call通过后不得再发第二次arguments请求；M30类已经给出完整call的语义不得被协议丢弃。

### 2.3 effect、Task postcondition、Goal evidence三层状态

Task持久化三个互不替代的事实：

1. `effect_observation_status=pending|observed|failed`：仅表示真实Harness result及deterministic action-level postconditions；
2. `postcondition_commit_status=pending|committed|rejected`：由一次独立RWKV task-local semantic decision决定该effect是否完成
   active Task自身，不判断未声明Goal outcome；
3. 现有`CriterionEvidence`：仍是Goal级独立proof，Round24不简化其协议。

执行顺序固定为：

`RWKV action commitment → Harness真实执行 → deterministic effect check → RWKV Task postcondition decision → Task completed → 可选Goal proof`

- 只有effect observed且RWKV明确`pass`，Task才可转`completed`，依赖边才满足。
- RWKV明确`replan`或协议失败时，Task不能completed；沿现有recovery预算进入producer correction。
- Task postcondition请求只看到2.1 capsule、实际action/result、deterministic verifier result和workspace digest；没有witness catalog、
  hidden expected、standard answer或其他Task的Goal evidence。
- 对测试用的无模型deterministic fixture，保持既有action-level完成兼容路径并明确审计`decision_source=deterministic_fixture`；正式
  RWKV E2E不得走该兼容路径。
- Goal criterion claiming Task在Task commit后才进入现有criterion proof；Task commit pass本身不能创建CriterionEvidence。

## 3. 本轮明确不修改

- 不改变Goal解析、固定max-5 criterion、Goal prompt或digest；这些留到已登记的Round27。
- 不把静态全图改为incremental frontier，不新增member/phase ledger；这些留到Round25。
- 不新增not_found/invalid/conflict/expected-fail/outcome edge或lifecycle分支；这些留到Round26。
- 不修改Harness action集合、runtime alias、命令、安全scope、真实tool result、外部API服务或final output。
- 不简化witness/proof，不创建Goal evidence捷径，不回滚same-target artifact，不选择“更正确”的旧revision。
- 不修改benchmark、数据集、sampling、并发、transition limit、standard answer、hidden acceptance或scorer。

## 4. 不作弊边界

- Controller只保存、投影和检查RWKV自己提交的action与Task decision；不生成或修改name、arguments、path、content、value、代码、
  member、criterion、expected值或final answer。
- compact catalog不得按题目、文件内容、历史得分或acceptance排序/筛选；所有15个注册action以固定登记顺序可见。
- Task postcondition pass/replan必须来自本次RWKV raw输出。deterministic verifier只能报告实际effect，不能代替语义decision。
- 不尝试多个RWKV候选后以Harness/External通过情况择优；每次请求只执行协议中的单一candidate和固定纠错次数。
- capsule去除的是旧/无关投影，不删除审计历史；raw与normalized分开保存，任何转换不得改语义字段。

## 5. 运行前验证

### 5.1 单元与对抗测试

- dependency capsule只选择每个direct dependency当前`output_refs`，旧attempt与非依赖evidence不出现；Goal/task原文不被截断。
- recovery capsule只含latest material failure/fingerprint/budget，不展开历史；canonical digest稳定，状态变化后digest变化。
- compact action catalog固定含全部15个action、argument names与required names，无case-dependent order。
- canonical及Round23登记wrapper的完整call可从第一次请求直达Harness；name/arguments逐字段不变，第二次request数为0。
- 旧式`action_type`进入唯一tool schema兼容路径；冲突name、mixed wrapper、unknown args仍失败关闭。
- effect check pass但RWKV Task decision=replan时Task不completed、dependency不ready；pass时Task completed但不自动创建Goal evidence。
- unchanged cache-safe Task observation在同recovery lineage中不重复RWKV cross-check；workspace/action/dependency变化后重新调用。
- run schema migration保存三层状态；interrupted effect在恢复时不能被误作Task committed。

### 5.2 产品回归

- 完整pytest、LH-Control-30、E2E90 validate-only、Round18–23相关protocol/state/recovery replay。
- 对Round23全部tool_choice/tool_action raw做离线重放，记录可被第一次atomic fast path保留的完整call、legacy fallback、reject及semantic
  mutation；mutation必须为0。

## 6. 正式实验与冻结顺序

- endpoint/model/context、RWKV-E2E-90版本、并发8、max transitions 200及sampling与Round23相同。
- 90题全部终止前不读取Round24 hidden acceptance、standard answer或Codex reference。
- 完整保留每个capsule、digest、prompt、raw、normalized、action commitment path、Harness result、effect status、Task commit raw/decision、
  Task transition、artifact revision、proof、recovery和terminal state。
- 先冻结score-independent results与blind causal review，再连接已冻结reference/acceptance并逐题比较。

## 7. 预注册指标

### 7.1 首要因果指标

1. 第一次action请求直接产生合法完整call的数量、比例、case与省去的第二次request/token；
2. action name/arguments从raw到Harness semantic mutation，必须为0；
3. execution capsule总token、selected memory、旧attempt引用、非依赖evidence引用及context overflow；
4. effect observed / Task committed / Goal evidence 三层计数及每个状态首次出现位置；
5. effect observed但Task rejected的case，后续是否进入producer correction而非错误dependency；
6. unchanged observation cross-check suppression与material change后重跑；
7. Round23正确revision是否减少被后续错误writer破坏，以及producer reachability变化。

### 7.2 全局指标

- External、Strict、Completed、FP、FN及Basic/Medium/Hard；
- first source/producer/verifier、artifact正确revision、CriterionEvidence；
- model requests、prompt/output tokens、Harness attempts、blocked/interrupted、transition数；
- 与Round23、Round22和FP=0最佳Round16逐case比较，不只比较总分。

## 8. 晋级条件

Round24只有在以下全部满足时才可提交并上传GitHub：

1. 全部运行前/运行后回归通过，semantic mutation=`0`，FP=`0`；
2. External不低于Round16的`24/90`，Strict与Completed不低于0；
3. External `>24`、Strict `>0`或Completed `>0`至少一项严格改善；
4. 改善可由capsule/atomic commit/三层状态链解释，且没有使用hidden信息、规则代答或Controller语义修改。

若不满足，完整保留Round24并标记`do_not_upload`；不得在看到分数后改指标、prompt、cache规则或晋级阈值。
