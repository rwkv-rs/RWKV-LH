# Round23 Basic B01–B30 标准答案接入前人工因果审阅

本文件不是错误计数器。每题都按 Goal → Plan → action/effect → state/evidence → terminal 反向追溯，记录最早偏离与
后续放大。原始证据位于 `../Round23/cases/<case-id>/`；Round22 展开审阅位于
`../Round22_manual_review/cases/<case-id>.md`。

## E2E-B01

- **Goal（observed）**：目标仍是写入精确 greeting 并验证；这一层不是终止原因。
- **Plan 首偏离（observed）**：五个 task 全部漏写 dependencies，writer、reader 和 final verifier 因而同时 ready；
  `satisfies_criteria` 也全部为空。Controller 仍保存该图，并按 priority 先调度最高的 T5 final verifier。
- **Action/effect（observed）**：T5 在 writer T2 尚未运行时读取不存在的 `greeting.txt`，两次真实失败。failure analysis
  错称为 write/read race；后续 materialization 两次改成绝对路径并被 scope contract 拒绝。
- **放大与终局（observed）**：DAG 只检查无环，没有检查显式 producer→consumer 因果；priority 被当作足以决定执行的
  顺序；recovery 没回到尚未执行的 producer。最终在 action materialization blocked，workspace 没有目标文件。
- **结构含义**：最早应处理的是 Plan 因果完整性和 scheduler 对未执行 producer 的认知，不是放宽绝对路径或增加 read retry。

## E2E-B02

- **Goal/Plan（observed）**：source→report 的核心关系正确，但 Plan 重复设置两个相同 writer，并让单个 read-back task
  一次声称满足五项 criterion。
- **Action/effect（observed）**：T1 读到 `project=Orion,count=7`；T2/T3 都写入同一正确对象
  `{project:Orion,doubled_count:14}`，后续三次 read_json 也观察到该对象。
- **Evidence 首偏离（observed）**：witness 先选 unknown/non-eligible source，再把 WS source ID 当 WH handle ID，或在
  mode 阶段提前复制 catalog object；没有产生 CriterionEvidence。
- **放大与终局（observed）**：obligation 连续追加同义 read-back task，而不是修复 source→multiply→field 的关系；最后
  proposal 使用字符串 priority `high`，`int()` 转换异常逃出协议边界，run interrupted。
- **结构含义**：产物生产、任务动作完成和 Goal 证据闭合必须分开；proof 失败不能复制 reader，也不能使字段类型异常崩溃。

## E2E-B03

- **Goal/Plan（observed）**：Goal 保留两个 feature 变更和 unrelated-field preservation；Plan 的 reader、whole-object writer
  与四类 verifier 均可执行，且初始 claim owner 非空。
- **Action/effect（observed）**：RWKV 从原 JSON 生成并写入 `{feature:{enabled:true,mode:safe},name:alpha,retries:4}`；
  之后所有 read_json 都观察到同一 revision。
- **Evidence 首偏离（observed）**：mode prompt 要求仅 `{schema_version,decision}`，RWKV却稳定提前输出 literal、workspace、
  evidence 等下一阶段对象；另有非精确 Goal quote 和无效 handle binding。正确 producer 没形成 evidence。
- **放大与终局（observed）**：每轮 obligation 把同四个 verifier 成组复制，任务从 6 扩到 34，workspace 不变但 task-state
  digest 改变，使“未进展”没有阻止扩张；最终 unresolved_goal_obligations blocked。
- **结构含义**：proof 阶段划分与弱模型输出习惯错位；恢复应定位“证据构造边”而非把已完成 task 重新物化。

## E2E-B04

- **Goal/Plan（observed）**：复制 source、写 manifest、read-back 的主链完整；额外验证 task T8 需要读取纯文本 manifest。
- **Action/effect（observed）**：source copy 和 `archive/manifest.txt` 均被正确创建并保持；T8 却选择 `read_json`，三次因
  JSONDecodeError 失败。
- **Recovery 联合原因（observed）**：failure analysis 能识别“文本不是 JSON”，但提出不存在的 `read_text`；下一次
  action-choice 仍固定为 `read_json`。Round23 的 selected-action identity gate 正确阻止 materialization 偷换成 read_text，
  随后模型继续选择 read_json。
- **终局（observed）**：正确产物未再被破坏，但 recovery lineage budget 用尽。与 Round22 的“错误 verifier 覆盖正确
  manifest”相比，身份绑定提高了安全性，却没有解决错误 task/action 的 producer correction。
- **结构含义**：协议不能替模型改 action，但 failure state 需要允许 RWKV 在同一原子决定中真正改变 selected action，
  并提供真实可用的 read_file affordance。

## E2E-B05

- **Goal/Plan 首偏离（observed）**：T1 read、T2 remove、T3 read-back 的语义正确，但所有
  `satisfies_criteria=[]`；Controller 已知 coverage 为零仍执行。
- **Action/effect（observed）**：只删除 `deprecated=true`，其余三行顺序/字节保持；T3–T11 多次读到同一修改后状态。
- **放大（observed）**：obligation 第一次新增四个只 advance、不 satisfy 的 verifier，仍不能产生 claim；第二次输出大量
  重复 task 并 length 截断，第三次回显整个 capsule，均被 contract 拒绝。
- **终局（observed）**：workspace 已稳定但 0 claim/0 evidence，最终 goal_obligation_replan protocol blocked。
- **结构含义**：replan 是否“有进展”必须看 unresolved→claim-producing path，而不能只看新增 task 或 advances 标签。

## E2E-B06

- **Goal/Plan（observed）**：两个 source reader 后有一个多余 separator-only writer，再由 T4 写完整 combined；最终 verifier
  声称一次满足所有 criterion。
- **Action/effect（observed）**：T1/T2 取得完整文本，T4 最终写入 `A + ---\n + B` 且只有一个尾换行；最终 read-back一致。
- **Evidence 首偏离（observed）**：proof catalog 无法表达两个 immutable text、literal separator 和 exactly-one-newline
  的组合；RWKV转而选择 unknown source或在 mode 中附带 catalog 字段。
- **放大与终局（observed）**：obligation 再加同义 verifier并输出 `priority=high`，未处理类型异常使 run interrupted。
- **结构含义**：这是“production 正确、relation language 不可达”，不能通过重写 final text或 hidden acceptance判定解决。

## E2E-B07

- **Goal（observed）**：条件分支、唯一 output 和禁止 alternate output 均保留。
- **Plan 首偏离（observed）**：T2“Select the correct endpoint”是纯认知步骤，没有可由一个 Harness action建立的 artifact/
  observation；T3 writer依赖该抽象节点。Graph contract仍接受。
- **Action/effect（observed）**：T1 读到 `production`；T2 action-choice 却对纯文本 `mode.txt` 选择 read_json，三次相同失败；
  writer从未运行。
- **放大与终局（observed）**：failure recovery没有把“task不可落地”升级为 replan，只重试错误 action直到 lineage budget耗尽。
- **结构含义**：Plan 必须区分 observable step 与模型内部计算；内部分支决定应和下一 producer action形成一个可审计决定，
  不能伪装成已完成 task。

## E2E-B08

- **Goal/Plan（observed）**：source read→digest→manifest→verification 主链合理；T2“compute”实际仍只执行 read_file，但
  artifact metadata 向后提供了 bytes SHA。
- **Action/effect（observed）**：RWKV写入的 lowercase digest 与实际 payload artifact SHA一致，manifest恰有两个字段。
- **Evidence 首偏离（observed）**：writer binding 混用 source/derived handle字段；后续 verifier选择 unknown/non-eligible
  expected；mode回显 source metadata并一度 length 截断。
- **放大与终局（observed）**：obligation生成“re-compute”task却仍读 manifest，failed/stale attempt也进入候选；尽管后续
  read成功，Goal仍无 evidence并 blocked。
- **结构含义**：权威历史可以全保留，但给 RWKV 的当前视图需区分 failed/latest-success/source-derived state，并先选
  source/field再按需展开 operator。

## E2E-B09

- **Plan 首偏离（observed）**：T2“Compute row_count/total/average”仍是无单 action落点的抽象计算节点；图还没有把 header
  exclusion变成可追溯的 transform state。
- **Action/effect（observed）**：T1正确读到 CSV；T2先选 read_json，随后 action-choice两次 hallucinate未注册 read_csv，
  materialization identity gate拒绝把 selected `read_json`偷换为`read_csv`。
- **放大与终局（observed）**：恢复把 capability mismatch 当作同 task action retry，既不重新分解，也不回到 read_file
  已观察内容，三次 JSONDecodeError后 blocked。
- **结构含义**：首要缺口不是简单增加 read_csv，而是 Plan 的“计算”如何成为同一 RWKV producer decision的一部分，及
  capability mismatch如何进入 replan而不是无效 retry。

## E2E-B10

- **Goal/Plan（observed）**：Goal省略“smallest change”并把 pytest惯例带入；Plan T4虽然依赖实现 T3，却没有把实际 tests T2
  作为验证依赖。
- **Model production 首偏离（observed）**：RWKV读到连续空格测试，却写出 `replace(' ', '-')`，会保留多个连续 hyphen；
  因而实现本身不能满足已见测试。
- **Runtime 放大（observed）**：T4先尝试 pytest，再尝试 python/unittest；bubblewrap内两者都不可执行。retry tool call又用
  `action`外壳但把 argv/cwd 放在 arguments 外，被严格拒绝后继续失败。
- **终局（observed）**：测试从未真正运行，runtime ENOENT遮住了更早的代码错误，lineage budget耗尽。
- **结构含义**：必须同时保存 test observation→implementation 的数据依赖和真实 toolchain capability；只修 runtime会暴露
  代码错误，不等于任务完成。

## E2E-B11

- **Goal 首偏离（observed）**：objective完整复制 Goal-normalization提示词而非用户的 name transform；错误 Goal 被冻结。
- **Plan/action（observed）**：第一次 task decomposition又输出 Goal对象，纠错后才形成 Plan；T2直接修改 source `name.txt`
  为 `RWKV Long Horizon`，既未 trim 外围空白也未创建 `normalized_name.txt`。T3随后错误搜索字面 `name`，三次失败。
- **放大（observed）**：Plan 把一个 value transform拆为若干 in-place replace，且全部无 claim owner；action success令T2被标
  completed，错误的 source mutation成为下游前提。
- **终局（observed）**：恢复没有重新观察并生成目标 writer，只重复 exact replace，budget耗尽。
- **结构含义**：原请求必须保持唯一权威；Goal proposal只能是可审计投影。value transformation不应通过无法闭合整体意图的
  零碎 in-place动作伪装为进度。

## E2E-B12

- **Goal输出（observed）**：两次输出在 objective、source、exact keys、numeric values和关系上都正确，但稳定拆成8项 criteria。
- **协议终止（observed）**：固定 contract只允许1–5项；第二次 correction完整重放第一次8项结构，RWKV逐字重复；没有创建
  RunState/Task，event log为空。
- **联合原因（observed + inference）**：模型违反 compactness是直接原因；完整失败结构在纠错prompt中成为最强锚点是架构
  放大。此题尚未测试模型是否会读数或算对。
- **结构含义**：Goal语义有效性和表达粒度必须分开记录；Controller不能自动合并 criteria，但纠错不应回显要删除的整份对象。

## E2E-B13

- **Goal/Plan（observed）**：目标字段和 preservation 都保留；writer一次构造完整新对象，另一个 replace在正确写入后返回
  `replacement already present`。
- **Action/effect（observed）**：最终 config保留 service/owner/enabled，并正确更新 region/retries。
- **Evidence 首偏离（observed）**：preservation verifier虽间接依赖原 reader，模型当前投影主要暴露修改后 revision；mode
  频繁提前输出 literal/catalog，selection又使用非精确 Goal quote。0 evidence。
- **放大（observed）**：obligation反复复制五个 read_json verifier，最终23 task/23 attempt，workspace从首个 writer后没有
  新信息，run仍 unresolved blocked。
- **结构含义**：criterion coverage还要检查独立 source revision可达性；mutation前后版本应显式进入同一 proof relation。

## E2E-B14

- **Plan 首偏离（observed）**：Graph把完整拼接拆成四个重叠 same-target writer；T3已写入left+separator，T4又追加separator；
  T5题面是追加right却只依赖T4、不依赖right reader T2。
- **Action/effect（observed）**：T3写 `alpha\nbeta\n--\n`，T4追加裸`--`，T5再追加`--\n`而非right，T6追加newline；
  最终缺失全部 right并出现重复separator/空行。
- **Evidence/终局（observed）**：T7 read-back忠实观察错误文本；proof选unknown sources；obligation priority `high`触发未处理异常。
- **结构含义**：多 writer不是自动“分步更稳”；same-target revision链必须有明确片段来源/边界，缺数据依赖的 writer graph应在
  执行前返给 RWKV纠正。

## E2E-B15

- **Goal（observed）**：stable unique、first-seen order、exact one key均保留。
- **Plan 首偏离（observed）**：T2“Verify the color list is unique and ordered”作为 writer前置的抽象计算task，却没有一个能建立
  stable-dedup结果的 Harness effect。
- **Action/effect（observed）**：T1读到真实颜色列表；T2对纯文本选择read_json并三次失败，后续writer完全未执行。
- **放大与终局（observed）**：与B07/B09同样，action recovery没有识别task-decomposition mismatch，budget耗尽。
- **结构含义**：计算/选择/排序应属于 RWKV materialize producer payload时的决定，或产生明确typed intermediate state；不能
  用一次无意义reader把“思考”标成task。

## E2E-B16

- **Plan/action首偏离（observed）**：T2题面承诺删除comment/blank、重排并改MODE，但实际只选择
  `replace_text(MODE=dev→prod)`；单个动作没有建立完整 task postcondition。
- **State放大（observed）**：Harness返回replace成功，Controller即把整个T2标completed；注释和空行仍在，错误中间状态成为
  verifier T3输入。
- **Protocol终局（observed）**：T3正确选择read_file但两轮materialization坚持绝对workspace路径，scope contract拒绝后block。
- **结构含义**：至少需要 action executed、task postcondition established、Goal evidence established三种状态；task成功不能
  由一个局部动作的success flag替代。

## E2E-B17

- **Goal/Plan（observed）**：source→filter/sort/count→final的值关系正确，但Graph创建两个不必要scratch文件并把同一推断拆成
  多个 writer，扩大artifact和proof面。
- **Action/effect（observed）**：RWKV正确生成 `active_names=[Ada,Zoe],active_count=2`；scratch和final均与source一致。
- **Evidence首偏离（observed）**：mode阶段多次复制catalog；binding一次输出过多同 intent记录并违反exact schema；正确source
  到filter/sort/count关系始终没有CriterionEvidence。
- **放大/终局（observed）**：obligation重复reader后length/capsule回显被拒绝，goal_obligation_replan blocked。
- **结构含义**：中间artifact只有带来新观察或独立证据时才有价值；模型自写scratch不增加source independence。

## E2E-B18

- **Goal首偏离（observed）**：objective复制系统提示词，criteria围绕文件存在/JSON而遗漏`discount=subtotal*rate`关系。
- **Action/effect（observed）**：下游仍两次读到 `subtotal=80,rate=.15`，RWKV写出 `{subtotal:80,discount:12,total:68}`并
  多次read-back；生产值可由可见source复核。
- **Evidence/恢复（observed）**：初始tasks均无satisfies；obligation第一次新增仍与unresolved无关，第二次输出capsule外壳而非
  new_tasks，protocol blocked。
- **结构含义**：错误Goal与正确original_request同时存在造成双事实源；关系criterion必须在执行前有source-reachable producer。

## E2E-B19

- **Goal/Plan（observed）**：digest目标正确，但初始writer不claim satisfaction；只有后续read-back task声称一次满足全部关系。
- **Action/effect（observed）**：source artifact SHA与manifest内lowercase digest一致，exact two keys；连续read-back稳定。
- **Evidence首偏离（observed）**：mode两次附带`catalog_source`值，违反only-two-fields contract；可用的source SHA→manifest leaf
  路径未进入binding。
- **放大/终局（observed）**：obligation只追加reader，0 evidence，unresolved blocked。
- **结构含义**：operator存在不等于模型可达；producer claim、source revision和最小字段选择必须在同一因果链中。

## E2E-B20

- **Plan首偏离（observed）**：test reader T2是required但T3/T4均不依赖它；priority让T3实现和T4测试越过T2。
- **Action/effect（observed）**：RWKV根据简单stub写出正确 modulo implementation；测试始终用不存在的 `python`执行，三次ENOENT。
- **Protocol放大（observed）**：retry materialization把argv/cwd放在`action`外壳错误层级，correction后仍重复；真实sandbox
  capability从未进入模型观察。
- **终局（observed）**：代码产物存在，但测试未执行、T2仍pending、coverage也不闭合，lineage budget耗尽。
- **结构含义**：required fairness、test→implementation dependency和toolchain negotiation是三个独立边，不能用External test替代。

## E2E-B21

- **Plan首偏离（observed）**：首个task就用“read CSV并验证完整性”承载读取/解析两层语义；后续parse/calculate/sort也是无单一
  Harness action落点的抽象task。
- **Action/effect（observed）**：T1选择read_json读取CSV并失败；materialization想偷换成未注册read_csv，但 selected-action
  identity gate正确拒绝。三轮均未退回真实read_file。
- **放大/终局（observed）**：capability mismatch被当作action retry而非plan repair，首task耗尽budget，零产物。
- **结构含义**：结构化数据任务首先需要“观察原始bytes”和“由RWKV生成producer payload”的明确边界；添加专用工具不是
  唯一且未由本题证明的解。

## E2E-B22

- **Plan首偏离（observed）**：T2/T3都完整写同一正确Markdown，T4又被设计为“确保尾换行”的第三个whole-file writer；
  Graph没有表达same-target revision的expected delta。
- **Action/effect（observed）**：T2/T3产物只有一个尾换行；T4 payload却在相同正文后写两个换行，覆盖正确revision。T5–T8
  忠实观察错误bytes，T7还一度把TASKS.md当JSON后恢复读tasks.json。
- **State/evidence（observed）**：所有writer因file written被标completed；proof mode/selection反复提前字段、unknown source或
  same-output自证，0 evidence。
- **终局（observed）**：workspace保留双尾换行，obligation无法闭合。
- **结构含义**：需要artifact revision和last-valid-producer状态；“ensure invariant” task不能因覆写成功就覆盖已正确revision。

## E2E-B23

- **Plan（observed）**：T1检查primary JSON，T2读取backup，T3/T4分别代表两条producer分支；条件意图存在但状态模型仍是普通
  success-only依赖。
- **Action/effect首偏离（observed）**：primary的JSONDecodeError正是应触发fallback的有效观察，却被Controller当成T1失败；
  T1被重试三次，T2从未调度。
- **放大/终局（observed）**：failed dependency同时阻断两条writer分支，recovery只重试read_json直到budget耗尽。
- **结构含义**：分支inspection需要typed outcome（valid/invalid/read failure），预期negative observation可建立task状态；不能
  把所有Harness failure都等同于任务失败。

## E2E-B24

- **Goal首偏离（observed）**：objective复制系统提示，因而`preserve log.txt`没有形成可靠 outcome约束。
- **Plan/action首偏离（observed）**：T2直接在source删除所有`warn z`，破坏preservation且把应保留一个的重复值删光；T3首次
  materialization输出超长数字序列并截断，纠错后又写入与source完全无关的alphabet词表。
- **State放大（observed）**：remove/write均因action success标completed；T4重复错误writer，后续read-back把错误文本作为事实；
  proof mode继续复制大catalog。
- **终局（observed）**：source已被修改，sorted.log与输入无关，Goal evidence仍未闭合。
- **结构含义**：这是明确的模型语义失败，不能归因给协议外壳；架构缺陷是没有source immutability boundary、task postcondition和
  producer correction，导致错误被层层固化。

## E2E-B25

- **Goal/Plan（observed）**：两份source和merge规则被读到；T3 whole-object writer直接依赖两者，是可执行粒度。
- **Model production首偏离（observed）**：RWKV把nested `runtime.mode/retries`扁平化为顶层`mode/retries`，虽数值来源正确但
  JSON结构违反明确的nested约束。
- **State/evidence放大（observed）**：write_json成功使T3及所有read-back task completed；witness反复选择同一个output作
  actual/expected或unknown expected，没有把base/override JSON pointers连接到目标paths。
- **终局（observed）**：错误结构稳定存在，obligation只加reader后blocked。
- **结构含义**：typed path mapping是producer payload的一部分；proof不能修写错的结构，恢复必须回到writer而不是认证self-output。

## E2E-B26

- **Plan首偏离（observed）**：T4题面要求创建`nested/c.txt`却选择make_directory；T5又把三文件内容验证塞进一次read_file。
- **Action/effect（observed）**：a/b写入正确，nested目录创建，但c.txt从未物化；后续所有reader只读a，list_directory明确显示
  `output/nested`目录但无c文件。
- **State放大（observed）**：make_directory success让T4 completed；file-set/list结果没有反向形成“c producer未建立”；proof
  继续绑定self/unknown sources。
- **Recovery/终局（observed）**：obligation成组复制三类verifier至21 tasks，正在执行T10时固定prompt超过context，run interrupted。
- **结构含义**：task全部description必须被一个action effect闭合；明确缺失Goal path应定位到producer gap，而不是继续list/read。

## E2E-B27

- **Model action首偏离（observed）**：RWKV为“replace every”提交`count=-1`，违反action contract的positive integer；runtime
  未拒绝而静默按1次处理。
- **Action/effect（observed）**：只替换第一个complete occurrence，read-back仍含一个standalone `protocol=v1`（另有应保留的
  `fallback_protocol=v1`）。T3仍因read success被completed。
- **放大/终局（observed）**：T4错误选read_json验证文本，三次失败；恢复没有利用`replaced 1 occurrence`和remaining bytes
  纠正producer，budget耗尽。
- **结构含义**：schema/validator/runtime必须一致且禁止silent coercion；partial mutation需要observable before/after count并回到
  RWKV producer correction。

## E2E-B28

- **Goal/Plan（observed）**：key=value source到exact integer JSON的主链正确；writer只claim GC2，relation coverage仍部分遗漏。
- **Action/effect（observed）**：RWKV从文本提取48/120/3，写出exact三键整数对象；两次read-back一致。
- **Evidence首偏离（observed）**：selection把WS source ID当expected handle、附加reason，或选择同output作两端；0 evidence。
- **放大/终局（observed）**：obligation复制reader并输出priority `high`，未处理类型异常中断。
- **结构含义**：常见text→typed fields需要由RWKV选择source lines/path和conversion的可审计关系；不能由Controller替模型解析并补证。

## E2E-B29

- **Goal首偏离（observed）**：新增“manifest exactly two lines”，把终止newline误当第二行；它与用户要求的单行+newline冲突。
- **Action/effect（observed）**：source copy逐字一致，manifest实际为正确单行映射加newline，source保持不变。
- **Evidence（observed）**：copy binding改变预提交source kind；后续多次unknown/same-output binding；错误GC4的Goal quote又不是精确原文。
- **放大/终局（observed）**：错误Goal criterion成为immutable obligation，正确产物仍因0 evidence blocked。
- **结构含义**：model-derived criterion必须能追溯到request span并做相互冲突审计；提升proof recall前必须先避免错误Goal引发FP式改写。

## E2E-B30

- **Goal/Plan（observed）**：source、tests、implementation、test task依赖完整；但实现task没有claim GC1，生产证据入口仍漏失。
- **Action/effect（observed）**：RWKV读tests并写出`strip→lower→split/join('-')`实现，与可见测试一致；run_command使用
  `python test_names.py`，sandbox内python不存在。
- **Recovery联合原因（observed）**：failure analysis意识到环境缺Python，却建议通过shell再次调用python，并附加大量contract外
  字段；两次输出在JSON extraction/contract后被判为非法decision，异常最终逃出为run_interrupted。
- **结构含义**：toolchain capability应在action选择前成为真实observation；recovery需保留task/action边界，只让RWKV修参数，
  但不能自动把python换成hidden verifier解释器或宣称测试通过。

## Basic 组阶段性跨题结论（尚非下一轮方案）

1. **最底层状态语义混用**：B16/B22/B26/B27证明`action success → task completed`会把局部、部分或错误effect升级为完整
   task事实；这是后续proof/recovery失真的共同前提。
2. **Plan不是可执行因果图**：B01缺依赖，B07/B09/B15/B21包含抽象计算task，B23缺conditional outcome，B14/B22有重叠
   same-target writers。仅验DAG和字段shape远远不够。
3. **正确production与Goal完成必须分层**：B02/B03/B05/B06/B08/B13/B17/B18/B19/B28/B29的workspace已经满足或接近
   显式目标，但proof/obligation不闭合；不能据此自动completed，也不能让证据失败破坏产物。
4. **Goal可能成为错误事实源**：B11/B18/B24 prompt echo，B29 invented criterion，B10漏用户约束。original request必须保持
   唯一权威，Goal只能是带source-span provenance的模型投影。
5. **恢复没有回到最早断边**：producer缺失时仍加reader，action mismatch时仍重试同action，proof不可表达时仍复制verifier；
   task-state变化又掩盖workspace不变。
6. **Round23 protocol closure的真实作用**：它透明放行了多种等价外壳并阻止selected-action偷换，未生成语义字段；但“更可达”
   也会执行模型给出的坏Graph/坏action。协议正确只是必要条件，不能作为E2E改善的充分条件。

