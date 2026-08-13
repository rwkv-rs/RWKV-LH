# Round23 Basic B01–B30 标准答案后逐题对比

本文件连接三份已冻结证据：独立参考答案、acceptance、标准答案接入前生命周期审阅。所有case的Strict均为FAIL、
`agent_completed=false`；这里另外区分External artifact是否正确。Round22变化只描述本次可观察差异，不把单次采样相关性
写成架构因果。

## E2E-B01

- **Reference/actual**：目标`Hello, RWKV-LH!\n`；Round23文件缺失，External FAIL。
- **因果确认**：final verifier因高priority先于无dependency writer执行，recovery没有回到pending producer；不是RWKV不会写
  greeting，而是Graph/调度使writer从未运行。
- **R22→R23**：External PASS→FAIL，是5个回归之一；Round22曾实际写对同一bytes。本轮证据要求修producer-aware scheduling，
  不能把该回归归给protocol closure的必然效果。

## E2E-B02

- **Reference/actual**：actual正是`{project:Orion,doubled_count:14}`且exact keys通过，External PASS。
- **因果确认**：生产链正确；witness handle/mode错误、重复reader obligation及`priority="high"`异常使完成假阴性。
- **R22→R23**：External持续PASS，Strict持续FAIL；说明简单JSON计算能力稳定存在，completion链仍未改进。

## E2E-B03

- **Reference/actual**：完整config与标准相等，preservation正确，External PASS。
- **因果确认**：proof阶段提前输出后续schema对象，obligation把四个reader成组扩张至34 tasks，0 evidence。
- **R22→R23**：External持续PASS；重复无变化verification仍是主要放大器。

## E2E-B04

- **Reference/actual**：copy SHA与source一致，manifest精确一行，External PASS。
- **因果确认**：错误task仍三次用`read_json`读文本；Round23 action identity gate阻止materializer偷换action并破坏artifact，
  所以正确production被保住，但run仍blocked。
- **R22→R23**：External FAIL→PASS，是3个新增产物通过之一；这是protocol identity约束带来的安全收益，但尚未带来Strict完成。

## E2E-B05

- **Reference/actual**：删除deprecated后一字节序列与标准一致，External PASS。
- **因果确认**：初始Plan的`satisfies_criteria`全空；9次read仍不能创建合法claim，replan只增加advance-only tasks。
- **R22→R23**：External持续PASS、Strict持续FAIL。

## E2E-B06

- **Reference/actual**：拼接、separator及单尾换行完全正确，External PASS。
- **因果确认**：proof relation无法紧凑表达两个source+literal separator+newline，随后priority类型异常中断。
- **R22→R23**：External持续PASS；production不是下一步应重写的环节。

## E2E-B07

- **Reference/actual**：production分支应写endpoint，但文件缺失，External FAIL；alternate正确地不存在。
- **因果确认**：抽象“select endpoint”task被当作可执行node并对文本选`read_json`，三次失败阻断writer。
- **R22→R23**：External PASS→FAIL；Round22曾选对production。需要Plan observable-step contract与producer correction，不能用
  Controller直接替RWKV选择production endpoint。

## E2E-B08

- **Reference/actual**：exact two keys与真实SHA256全部通过，External PASS。
- **因果确认**：生产值正确；proof混用source/derived handle并重复读manifest，未形成criterion evidence。
- **R22→R23**：External持续PASS、Strict持续FAIL。

## E2E-B09

- **Reference/actual**：标准为3/45/15，`stats.json`缺失，External FAIL。
- **因果确认**：抽象compute node先选`read_json`，再hallucinate未注册`read_csv`；identity gate正确拒绝偷换，但没有触发Plan repair。
- **R22→R23**：持续FAIL；缺口是raw-byte observation→RWKV producer payload的可执行边。

## E2E-B10

- **Reference/actual**：slugify的words test通过，multiple spaces得到`multiple---spaces`，完整tests FAIL。
- **因果确认**：RWKV看见测试后仍写`replace(' ','-')`，是直接model code error；sandbox `python`不可用又遮住本地反馈。
- **R22→R23**：External PASS→FAIL。runtime修复只会让此model error更早暴露，不会自动修代码。

## E2E-B11

- **Reference/actual**：应创建`RWKV Long Horizon\n`，实际修改了source且目标文件缺失，External FAIL。
- **因果确认**：Goal先复制system prompt，后续in-place replace把错误source mutation标completed。
- **R22→R23**：持续FAIL；original request与Goal projection双事实源问题仍在。

## E2E-B12

- **Reference/actual**：标准count5/sum25/min-2/max9；stats缺失，External FAIL。
- **因果确认**：RWKV两次给8 criteria，固定max5且纠错回显完整错误对象，0 task。
- **R22→R23**：持续FAIL；此题尚未测试数值计算能力。

## E2E-B13

- **Reference/actual**：完整nested deployment与标准相等，External PASS。
- **因果确认**：producer正确；mutation前后revision没有进入可达proof relation，23个task后仍0 evidence。
- **R22→R23**：External持续PASS。

## E2E-B14

- **Reference/actual**：source均保留，但merged为`alpha\nbeta\n--\n----\n\n`且缺right，External FAIL。
- **因果确认**：四个重叠same-target writers、缺right-reader dependency和append语义共同放大；不是单个separator小错。
- **R22→R23**：持续FAIL。

## E2E-B15

- **Reference/actual**：应为stable unique blue/red/green，`colors.json`缺失，External FAIL。
- **因果确认**：抽象“verify unique/order”node对纯文本用`read_json`，writer从未运行。
- **R22→R23**：External PASS→FAIL；与B07同属abstract-computation task回归入口。

## E2E-B16

- **Reference/actual**：MODE已改prod，但comment/blank仍在，External FAIL。
- **因果确认**：一个局部`replace_text` success被升级成整个normalize task completed；验证又因绝对路径protocol block停止。
- **R22→R23**：持续FAIL；直接证明需要effect/task/goal三层状态。

## E2E-B17

- **Reference/actual**：active names Ada/Zoe、count2且exact keys，External PASS。
- **因果确认**：模型production正确；scratch artifacts和多阶段proof增加了表面积而没有增加source independence。
- **R22→R23**：External持续PASS。

## E2E-B18

- **Reference/actual**：80/12/68 exact keys通过，External PASS。
- **因果确认**：Goal错误复制prompt并漏discount关系，但下游RWKV仍从source算对；0 claim/evidence导致假阴性。
- **R22→R23**：External持续PASS。

## E2E-B19

- **Reference/actual**：真实digest与two-key manifest完全通过，External PASS。
- **因果确认**：proof mode schema漂移，writer又没有claim ownership；重复reader不增加信息。
- **R22→R23**：External持续PASS。

## E2E-B20

- **Reference/actual**：外部python3测试真实PASS，`is_even`正确，External PASS。
- **因果确认**：Agent内部只尝试不可用`python`，required test reader仍pending，故run blocked。外部验收证明代码而非内部验证完成。
- **R22→R23**：External持续PASS。

## E2E-B21

- **Reference/actual**：标准alpha3/beta6/gamma1，目标文件缺失，External FAIL。
- **因果确认**：CSV被`read_json`读取，复合read+validate task不可由单action闭合；恢复没有返回`read_file`。
- **R22→R23**：持续FAIL。

## E2E-B22

- **Reference/actual**：内容正确但有两个尾换行，External FAIL。
- **因果确认**：前两个writer已建立正确revision，第三个“ensure newline”whole-file writer覆盖成双newline；task success未检查delta。
- **R22→R23**：持续FAIL；需要last-valid revision与same-target writer invariant。

## E2E-B23

- **Reference/actual**：primary invalid时应选择backup，实际`selected.json`缺失，External FAIL。
- **因果确认**：JSONDecodeError本是valid branch outcome，却被重试为fatal，fallback从未调度。
- **R22→R23**：持续FAIL；typed negative outcome是根缺口。

## E2E-B24

- **Reference/actual**：source被破坏，sorted.log为无关alphabet词表，两个checks均FAIL。
- **因果确认**：Goal错误、source mutation和RWKV hallucinated payload依次叠加；这是明确model production错误并被状态机固化。
- **R22→R23**：持续FAIL。

## E2E-B25

- **Reference/actual**：值来源大致正确但runtime被扁平化到顶层，External FAIL。
- **因果确认**：RWKV typed path mapping错误；read-back与self-proof只固化错误对象。
- **R22→R23**：持续FAIL。

## E2E-B26

- **Reference/actual**：a/b正确，nested/c缺失，file set FAIL。
- **因果确认**：创建c的task实际只`make_directory`，action success升级为task completed；重复verifier最终造成context overflow。
- **R22→R23**：持续FAIL。

## E2E-B27

- **Reference correction/actual**：acceptance与“no v1 remains”要求三处substring都变v2；actual只替换第一处，仍有fallback和末行v1。
- **因果确认**：`count=-1`违反positive integer contract却被runtime静默按一次处理；partial effect仍使task completed。
- **R22→R23**：持续FAIL。冻结独立参考中“保留fallback”是Codex错误，已单独登记，不影响actual仍错误的结论。

## E2E-B28

- **Reference/actual**：48/120/3 integer exact keys通过，External PASS。
- **因果确认**：text→typed生产正确；proof source选择错误与priority异常阻断完成。
- **R22→R23**：External持续PASS。

## E2E-B29

- **Reference/actual**：copy bytes与manifest都完全通过，External PASS。
- **因果确认**：Goal invented“exactly two lines”与正确单行产物冲突，导致immutable obligation无法闭合。
- **R22→R23**：External持续PASS；证明Goal provenance优先于扩展proof recall。

## E2E-B30

- **Reference/actual**：外部python3 unittest真实PASS，implementation正确，External PASS。
- **因果确认**：内部`python`不可用；failure-analysis又输出非法decision enum导致protocol failure，run未完成。
- **R22→R23**：External持续PASS。

## Basic组结果

- External `14/30`：B02/B03/B04/B05/B06/B08/B13/B17/B18/B19/B20/B28/B29/B30。
- 其中14题全部是“产物正确、Agent完成失败”；不存在Strict pass。
- 相对Round22：新增B04，丢失B01/B07/B10/B15，Basic从17降至14。
- 后验标准没有推翻主要盲审结论，只纠正了B27对fallback substring的解释，并把B22双尾换行等partial错误精确量化。
