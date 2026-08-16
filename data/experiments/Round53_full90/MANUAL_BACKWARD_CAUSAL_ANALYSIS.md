# Round53 E2E-90 逐题反向因果分析

状态：实验结束后分析。90 个 case 的 `audit.json`、Task 图、动作、reviewer 决策、外部验收和冻结 Round46 对照均已逐条人工阅读；脚本只用于定位记录和显示字段，没有代替因果判断，也没有参与模型运行。

## 结论先行

Round53 的“同一 RWKV 在动作执行前复核自己的候选”不是更优架构，应当回退，不应上传为最佳版本。

- 相对已上传 Round46，Strict 从 `31/90` 降为 `23/90`，External 从 `32/90` 降为 `24/90`。
- FP 从 `24` 降到 `20`，但这是以 10 个原 Strict case 退化、30 个 case 因三次候选全被拒绝而终止为代价；质量主指标净下降 8 题。
- reviewer 确实把 9 个 Round46 FP 变成了安全失败，但也把已经正确的候选动作误杀。例如 B21 的正确 JSON、M12 的正确 `math_utils.py`、M20 的正确 parser 修复都被拒绝。
- reviewer 不是独立证据源。它与 action producer 共用同一模型、同一上下文和同一错误观察，因此会把既有错误合理化；M01、M08、M13、M17、M21、M23、M24、M26、M27、M29 等明显错误动作均被接受并最终成为 FP。
- 最深层缺陷不是缺少更多“反作弊规则”，而是 Task、Action、Observation、Effect、Evidence 五层之间没有统一的原子性和引用关系。当前 reviewer 只在这条断裂链上再增加一个状态机，不能修复根因。

## 从后向前的共同因果链

| 层级 | 应有语义 | 当前最早偏差 | 后续如何放大 |
| --- | --- | --- | --- |
| 7. 完成判定 | 只有 criterion 被独立证据满足才完成 | 已完成 Task 或读回自产物被当作目标已完成 | 20 个外部失败仍被 agent 宣告完成 |
| 6. Evidence | evidence 指向独立、最新、与 criterion 对应的观察 | “写了什么”与“期望什么”来自同一个 RWKV 值；verify Task 还能再次写文件 | 错误值被自产自验，或验证步骤破坏正确产物 |
| 5. Effect | 动作效果与 Task 的 effect 一致 | copy/aggregate/verify 等抽象 Task 被实现为写 manifest、读一个成员或重复写入 | 局部成功被误当作集合、复制或验证完成 |
| 4. Action | 一次动作是一个可执行的原子推进 | Task 要求一组文件/多个阶段，但 action contract 一次只容纳一个工具调用 | 单个正确动作因没有一次完成整项 Task 而被 reviewer 否决 |
| 3. Observation | 每条观察有明确 producer、目标、时间和有效范围 | reviewer 将旧动作失败、旧测试结果或另一路径错误绑定到新候选 | 正确候选被描述为执行过且失败，连续三次同理由拒绝 |
| 2. Task 图 | Task 足够原子、依赖覆盖生产与验证 | 计划只有 inspect/read/verify，遗漏 producer；或把集合工作压成一个 Task | 后续 action 只能违背 active Task 才能真正完成目标，reviewer 又阻止这种修复 |
| 1. Goal 到计划 | 计划覆盖所有 criterion，不把任务文本中的名词臆造成值 | 多文件枚举只落实第一个成员，复杂项目只做若干读取，或直接猜测产物结构 | 后续每一步即使形式正确，也只是在执行错误/不完整计划 |
| 0. 协议边界 | 只做有限、透明、无语义改写的格式归一 | 常见 G1i/function 外壳和少量常见参数别名仍会被严格 schema 拒绝 | 本来可执行的完整对象在进入 Task/Action 语义链前终止 |

Round53 新 reviewer 同时混淆了三件不同的事：候选是否是一个合法原子动作、候选执行后是否完成 active Task、以及整个 Goal 是否完成。H12/H13 中，读取“下一个 shard/文档”是正确原子推进，但 reviewer 因整个集合尚未完成而拒绝；B21 中，写入完全正确，却因“还没有验证”被拒绝；M12/M20 中，它甚至把旧文件或旧测试结果当成新候选已经产生的结果。

## 与 Round46 的结果变化

- Strict → 非 Strict（10）：B18、B21、B24、B26、H04、LH04、M05、M12、M19、M24。
- 非 Strict → Strict（2）：LH02、M07。
- FP → 安全失败（9）：H11、H13、H15、LH09、LH11、M06、M11、M16、M25。
- 新增或转化为 FP：M13、M21、M23、M27，以及从 Strict 退成 FP 的 M19、M24。
- B18 成为唯一 FN：产物已经完全正确，但最终计划协议错误阻止 controller 完成。

这说明 reviewer 有一定“刹车”效果，却没有提高方向判断质量：它同时踩掉正确动作，并放行与自己原先理解一致的错误动作。

## Basic 30/30

| Case | 结果 | 最早偏差与逐层放大 |
| --- | --- | --- |
| B01 | Strict | 写精确文本 → 读回 → 外部 exact content；Task、Action、Evidence 一致。 |
| B02 | Strict | 读输入 → 派生 JSON → 读回；字段和值均与外部验收一致。 |
| B03 | Strict | 更新 JSON 后，“Verify”又选择 `write_json`，职责已经错位；只是重复写入的值恰好正确，外部仍通过，属于脆弱成功。 |
| B04 | F | “创建目录”先用 `write_file` 把 `archive/2026` 建成普通文件；随后正确的复制候选无法穿过该路径。reviewer 把已发生的 FileExists/路径冲突反复绑定到新候选，三次拒绝，manifest 未创建。最早错误在 Task→Action effect。 |
| B05 | Strict | 读配置 → 删除指定行 → 两次读回；外部精确内容与 forbidden text 均通过。 |
| B06 | Strict | 两个输入分别观察后合并，边界和尾换行正确；证据链完整。 |
| B07 | Strict | 读取 mode 后只写对应 endpoint，并验证另一分支不存在；分支选择正确。 |
| B08 | Strict | 读取原始字节后生成 digest manifest，外部重新计算 SHA256 通过。 |
| B09 | Strict | CSV 读取、统计和 JSON 精确键均正确。 |
| B10 | Strict | 先读实现与测试，再改源文件并运行测试；coding 最小闭环成立。 |
| B11 | Strict | 读取、规范化、写入和读回均正确。中间拆成两个 producer 虽冗余但未破坏结果。 |
| B12 | Strict | 数字统计正确，exact keys 通过。 |
| B13 | Strict | 嵌套配置只改目标字段并保留其余字段；外部整对象相等。 |
| B14 | Strict | 两个文件分别读取后生成合并文件，源文件与目标都通过。 |
| B15 | Strict | 首次出现顺序去重正确，输出 envelope 和 exact keys 正确。 |
| B16 | Strict | env 文本规范化和精确尾换行正确。 |
| B17 | Strict | 过滤、计数、输出 envelope 正确；虽然连续重写三次，最终值一致。 |
| B18 | FN | `total.json` 已正确生成并通过两个外部检查；完成末端却输出带额外字段的 task batch，被严格协议拒绝。最早错误在“Goal 已满足后仍继续规划”，随后协议层把正确结果变成 controller 未完成。 |
| B19 | Strict | 读取 payload、计算并写 manifest，外部 digest 重算通过。 |
| B20 | Strict | 能读源码和测试、写修复、运行测试；一个名为 Inspect 的 Task 实际执行写入，语义不干净，但最终代码正确。 |
| B21 | F | 候选 `{alpha:3,beta:6,gamma:1}` 完全正确且键已经按字母序。reviewer 先说“未排序”，再承认已排序但要求同一步验证，最后又谎称依赖里没有 gamma，连续拒绝。最早错误是 reviewer 将原子写入与整 Task/验证混为一体。 |
| B22 | F | RWKV 写成普通 bullet，遗漏 `[ ]`；第一次 effect 已错。后续 Task 只读/确认存在，未产生修正动作，reviewer 又把外部式失败观察当成候选结果反复拒绝。 |
| B23 | F | primary 是无效 JSON、backup 可用，本应由失败恢复转向 backup。reviewer 却把 primary 的 JSONDecodeError 归给候选 `read_json(backup)`，并在 active primary/backup Task 间来回错配，selected.json 从未生产。 |
| B24 | F | 读取日志后，RWKV 已给出正确去重排序文本的写入候选；reviewer 因该单步没有“读取/去重/保留”全部动作而拒绝，又拒绝单独读取，形成不可满足契约。 |
| B25 | Strict | 两份配置读取后合并，输出精确相等。 |
| B26 | F | 第一步生成未注册的 `write_directory`，未进入透明格式层/工具层；从 Round46 Strict 退化，属于动作协议表达回归。 |
| B27 | F | replacement 默认只替换一次，仍残留两个 `protocol=v1`。最早错误是动作参数没有覆盖 Task 的“全部”；验证阶段 reviewer 只复述旧读结果，未促成改变 count/策略。 |
| B28 | Strict | 文本指标提取、JSON envelope 和 exact keys 正确。 |
| B29 | FP | source 读到的字节含尾换行，但复制时写成 `line two`，丢失末尾字节；manifest 正确。reviewer 只看语义文本相同而接受，外部 files_equal 发现 hash 不同。 |
| B30 | F | 计划被多个“inspect manifest/snapshot/README”占满并反复读取 `names.py`，遗漏真正的实现修复；reviewer 还错误声称同一路径 README 在“project root”而不在 workspace，阻断后续。最早错误是计划覆盖。 |

## Medium 30/30

| Case | 结果 | 最早偏差与逐层放大 |
| --- | --- | --- |
| M01 | FP | 递归列出 3 个 service 后只处理 `api.json`；整文件写入还丢失 `port`，另外两个 service 完全未改。summary 也只有 api。集合没有展开成成员 Task，reviewer 接受了局部结果并自验。 |
| M02 | F | 前两步正确读取源码/测试；运行测试动作输出不完整 JSON，在进入执行前终止，修复 Task 未开始。 |
| M03 | Strict | 读取并迁移 users 数据，外部整对象通过。 |
| M04 | F | release JSON 正确，但“Verify release.json”错误执行 `write_json` 到 `RELEASE.md`，把 Markdown 覆盖为 JSON 字符串；随后又用 `read_json` 读 Markdown并被 reviewer 卡住。最早错误是 verify Task 可产生 mutation。 |
| M05 | F | 四个来源均已正确读取，最终写文件完整动作包却带 G1i 外壳冗余字段，被严格边界拒绝。从 Round46 Strict 退化，属于有限格式兼容缺口。 |
| M06 | F | “复制选定文件”被实现为写 `package/manifest.json`，实际文件一个都没复制；下一步又重复写 manifest。reviewer 直到验证目录时才拒绝，未在 copy effect 上识别角色错误。 |
| M07 | Strict | defaults 与 override 分别读取，merge 及 envelope 正确；由 Round46 FP 提升。 |
| M08 | FP | 初次把 Markdown 写成 JSON；后面虽改成 Markdown，但 bullet 模板缺少 status、顺序错误且无末尾换行。reviewer 按自己生成的模板宣称完全满足，外部 exact content 失败。 |
| M09 | F | 计划只有五个读取 Task，没有 rename API、更新 consumer 和运行测试等 producer；读完后再次规划输出 task batch 非法。最早错误是 Goal→计划覆盖。 |
| M10 | F | 空 workspace 中计划出不存在的“workspace manifest”读取 Task；RWKV 候选实际已准备写正确 `resilient.txt`，reviewer 因不符合错误 active Task 而连续拒绝。计划错误被 reviewer 固化。 |
| M11 | F | 四个 service 都读完，但计划最后变成读取尚不存在的 summary，遗漏所有迁移 producer；reviewer 一边知道应创建 summary，一边仍因 active Task 是 read 而拒绝写入。 |
| M12 | F | RWKV 新候选已完整正确实现 divide 和 median；reviewer 却声称候选仍是 `a*b`/首元素，实际引用的是修改前文件和旧测试结果，三次误杀。从 Round46 Strict 退化。 |
| M13 | FP | CSV 计算的 north/revenue_total 错，且 `by_region` 错用嵌套 quantity/revenue 结构；reviewer 只与自产值对照，接受所有重写和读回。 |
| M14 | F | JSON 产物已经正确，但下一次 `write_json` 带 `create_parents/overwrite` 非法参数，被严格 schema 拒绝；Markdown 尚未生成。 |
| M15 | FP | 递归目录观察后没有逐文件读取，直接猜测 3 个文件的元数据；输出键应为 `files` 却写 `entries`，路径多 `docs/` 前缀，line_count 也错。reviewer 全部接受。 |
| M16 | F | active Task 是“Inspect primary/item_NN files”集合，候选读取第一个真实成员；reviewer 因一个成员不能完成集合而拒绝，又要求先 list，尽管目录信息已存在。 |
| M17 | FP | 各 package 文件迁移本身通过，但构造 matrix 时把依赖归属错绑：core 得到 worker 的依赖，worker 变空。reviewer 把错误映射视为 dependency output。 |
| M18 | FP | 递归 list 后只读 `inputs/a.txt`，漏掉 `b.json` 和 nested 文件；manifest path 又错误保留 `inputs/` 前缀。集合成员未展开，reviewer 接受单成员总结果。 |
| M19 | FP | access.log 的 `/items` 计数少 1，导致 path_counts 错；reviewer 与自产摘要一致即接受。从 Round46 Strict 退化，显示同源复核不能提供独立算术证据。 |
| M20 | F | 前两次写入仍返回 tuple，测试失败；第三个候选已经改成测试要求的 dict 列表。reviewer 仍把旧测试失败和旧实现绑定给新候选，三次拒绝正确修复。 |
| M21 | FP | merge 第一步曾写出正确 3 项数组；“排序”Task 随后把它压成第一条对象，“add count”又在该单对象上写 count=1。每步局部 postcondition 覆盖上一层结构，reviewer 全部接受。 |
| M22 | F | 三个输入已读取，但计划加入 inspect/read 不存在的 `result.json`，遗漏 producer；候选已能写 result，reviewer却将 FileNotFoundError 绑定给写入动作并连续拒绝。 |
| M23 | FP | 读取真实 build_plan 后仍写入通用的 file1/2/3，而标准要求 README、bin/start.sh、config/app.json；reviewer 把模型臆造的声明当成观察事实。 |
| M24 | FP | 生成的 queue 实现中重复检测对 tuple 无效，pop 排序方向也反；reviewer 的理由甚至把 `write_file` 误描述为读取，后续没有运行测试便完成。从 Round46 Strict 退化。 |
| M25 | F | 计划要求先读不存在的 CHANGELOG；候选已准备创建文件，reviewer却因旧 FileNotFoundError 拒绝创建动作。又是计划错误 + stale observation 固化。 |
| M26 | FP | valid 内容大体正确，但 envelope 应为 `valid/rejected`，却写 `valid_records/rejected_records`；rejected index/reasons 也错。reviewer只检查自产 schema。 |
| M27 | FP | 拓扑序没有按“当前可用节点中字母序最小”逐轮选择，docs/web 顺序错；读回和重写仍使用同一错误序列。 |
| M28 | F | list/实际目录是 `*.log`，RWKV 后续候选却臆造 `*-file1.txt`；reviewer反复围绕不存在路径重选，未让集合成员与 list observation 建立引用。 |
| M29 | FP | 翻译值本身正确，但丢失顶层 `locale`、`translations` 和 `missing_keys` envelope；reviewer错误声称这些字段已存在于候选。 |
| M30 | F | “Migrate config” Task 实际写了 migration report，config 保持 v1；验证失败后 reviewer 只要求再读 config，未回到 producer，报告自身的类型和字段也错。 |

## Hard 30/30

| Case | 结果 | 最早偏差与逐层放大 |
| --- | --- | --- |
| H01 | F | 实现未把 CSV value 转成整数，summary API 也偏离测试；运行测试时又输出带 `reasoning/tool/tool_version` 的 G1i 冗余字段而终止。语义错误在前，格式错误只是最后阻断。 |
| H02 | FP | 发现 20 个 shards 后只读 shard_01，就把其 2 条记录当成全局 aggregate；集合 Task 没有成员化，reviewer接受局部汇总。 |
| H03 | FP | 把 source 文件名 `seed.txt` 当作内容，输出到根目录 `stageN.txt` 而非 `stages/`，并缺失规定换行；连续六次自洽写入放大首步 source/value 绑定错误。 |
| H04 | F | list 已确认文件存在，候选正是 `read_file(inbox/untrusted.txt)`；reviewer 给出自相矛盾理由：“Task 要求读取，但读取不安全，正确动作应读取”，三次拒绝。从 Round46 Strict 退化。 |
| H05 | F | corpus 已列出，下一步动作使用常见但未支持的 `end_char`，在协议层终止；集合工作尚未开始。 |
| H06 | F | 三个 env 迁移多数正确，但 stage 丢失默认 `debug:false`，report 写到 `envs/` 而标准要求根目录，还额外制造 `.sorted` 文件；最后 replan Task 带未注册元字段。 |
| H07 | F | 第一文件读取正确；第二动作把 recovery/evidence 等内部字段混进 G1i 调用，完整候选被协议拒绝，coding 修复未开始。 |
| H08 | FP | 去重顺序与计数正确，但字段应为 `event_ids`，却写 `unique_event_ids`；reviewer只验证自己的字段名。 |
| H09 | F | primary/backup 的计划顺序和 active Task 状态错位；候选读取 backup 时 reviewer 说 active Task 仍是 primary，fallback 恢复被依赖图锁死。 |
| H10 | F | 输入已读取，计算阶段却再次输出带 `end_char` 的 read 动作，协议终止，两个 release 产物未生成。 |
| LH01 | FP | 计划只列目录、读源码、读 verifier、读订单，完全没有修代码、执行分层 verifier 或生成 release；所有观察 Task 完成后 agent 即宣布完成。最早错误是 criterion 没有转成 producer Task。 |
| LH02 | Strict | 15 个 checkpoint 各自是一个明确原子 Task，最后单独写 final config；每步 effect 与 criterion 可对应，是本轮唯一 hard 成功，也直接支持“成员级/阶段级原子 Task”的方向。 |
| LH03 | F | 只读 root manifest 后便臆造三个 dataset、CSV 路径和 1000/2000/3000 计数，没有递归读取依赖；随后 G1i 外壳字段 `action` 被拒绝。 |
| LH04 | F | source 已读，正确 ledger producer 被放在后面；active Task 却先读不存在的 ledger。reviewer因文件不存在拒绝继续，crash-after-effect/resume 两个状态阶段均未触发。从 Round46 Strict 退化。 |
| LH05 | FP | 完成目录观察后只读 shard_01，就把整项 resilient shards 任务视为完成；reports 完全未生成。 |
| LH06 | F | “approved/draft requirements”两个 Task 都误读 authority_policy 本身，未读取真实来源；untrusted note 又生成绝对路径被 scope 拒绝。来源身份没有进入 Task contract。 |
| LH07 | F | 计划只有 inspect 服务、规则、脚本、workspace 和不存在的 migration report，没有任何服务迁移 Task；reviewer进一步阻止对缺失报告的处理。 |
| LH08 | F | “Read configs a,b,c”是非原子集合 Task；单文件路径失败后，正确的 list_directory 恢复候选仍被旧 FileNotFoundError污染并连续拒绝，补偿流程未开始。 |
| LH09 | F | 首个 mock API create 遭预设瞬时失败后，后续 active Task 用 `read_json` 读取 Markdown，ValidationFailed 又阻塞所有依赖；恢复策略未把瞬时 action failure 与任务依赖解耦。 |
| LH10 | F | 读源码和测试后，inspect manifest Task 生成越界 write path 并被拒绝；真正代码修复、测试、README 和 digest manifest 均未开始。 |
| LH11 | F | 每个 Task 包含 8 个 artifact，但一次 action 只能读一个；读取真实 `artifacts/001.txt` 的候选被 reviewer 以“路径不正确”拒绝，同时理由又给出相同正确路径。phase checkpoint 无法产生。 |
| LH12 | F | 模块写到了根目录，而测试引用 `mini_project/` 包；reporter 也缺规定尾换行。运行测试时协议输出不完整，后续 README、example、manifest 均未做。 |
| H11 | F | 候选读取真实 `normalize.py`，reviewer却无依据声称文件不存在并要求寻找新路径；首步即被 stale/imagined observation 阻断。 |
| H12 | F | 已读取 shard_01，候选正确转向 shard_02；reviewer却因“只处理一个 shard、整个 Task 未完成”拒绝该下一步。非原子集合 Task 与一次一 action 的硬冲突。 |
| H13 | F | Task 每批要求读 4 个文档，一次 action只读一个；reviewer把“本批还剩三个”当成拒绝下一个成员的原因，最终 checkpoints 和 summary 全缺。 |
| H14 | F | “递归发现全部 manifest/data”只执行一次 root read，随后用臆造 CSV 和千级计数写 index；reviewer接受错误观察闭环，最后才因 G1i `action` 外壳字段停止。 |
| H15 | F | parser/analyzer/reporter 写到了错误模块路径，API 也不符合 `event_report` 测试；reviewer在 run 阶段围绕不存在的 `dist/analysis.json` 反复拒绝，未运行真正测试修正。 |
| H16 | F | 一次性应用 change 后 capacity invariant 失败；补偿候选出现时 reviewer仍把旧 invariant failure视作候选结果，拒绝 rollback/compensation，错误状态无法恢复。 |
| H17 | FP | 聚合值被变成每 id 的 count/total 列表，而标准是去重后的单 amount entries + 顶层 count/total；reader/reviewer均以自产结构为期望。 |
| H18 | F | RWKV 直接改写 `release_validator.py`，跨越了被验证代码与验证器的证据所有权边界；即使如此仍没生成 products/report，reviewer只在缺失文件处终止。 |

## 归因聚类与结构含义

### A. Task 原子性/集合展开是首要结构缺陷

直接证据包括 M01、M06、M15、M16、M18、M28、H02、H05、H12、H13、LH05、LH08、LH11，以及正对照 LH02。共同模式是：计划写“全部/一批/递归/复制”，执行接口一次只能处理一个成员。当前系统既没有显式 collection cursor/member identity，也不允许 Task 在 ready 时由 RWKV 细化为成员级子图，于是模型要么只做第一个成员并完成，要么 reviewer 因一动作无法完成整 Task而拒绝。

### B. Observation 没有绑定 action attempt 与时间点

B21、B23、M12、M20、M22、M25、H04、H11、H12、LH04、LH08、LH11 展示了同一故障：reviewer 的 reason 描述的不是当前 candidate，而是旧失败、旧文件、另一路径或整个 Task 的状态。观察胶囊需要有明确的 `producer_action_id / target / observed_at / valid_for`，且候选执行前只能使用既有观察判断“可执行性”，不能假装知道候选执行后的结果。

### C. Task role 与 action effect 没有机器可表达的一致性

B03、B20、M04、M06、M21、M24、M30、H18 表明 title 里的“inspect/verify/copy/migrate”只是自然语言，schema 没有表达允许的 effect。于是 verify 能写坏产物，copy 能只写 manifest，migrate 能写报告，甚至 verifier 自身能被修改。不能用标题关键词规则修正；应让 RWKV 在计划中显式声明极小的结构化 role/effect contract，再由通用完整性约束检查 action 是否改变了声明外目标。

### D. 自产期望与实际值同源，导致 FP

M08、M13、M17、M19、M23、M26、M27、M29、H08、H17 都是“模型生成结果 → 同一模型复述该结果正确 → 读回自产物 → 完成”。这不是 RWKV 单次回答错误之外的独立问题，而是架构把模型产生的 actual 与模型产生的 expected 绑定到同一证据源，使错误无法被发现。外部 verifier/测试/输入重算才是独立 evidence；模型自由文本 review 不是。

### E. 协议格式仍有有限、重复的兼容缺口

B26、M02、M05、M14、H01、H05、H06、H07、H10、LH03、LH06、LH10、LH12、H14 出现 schema/外壳/截断问题。只应补充少数高频、可逆且字段对象不变的透明归一：已知 G1i/OpenAI function 外壳展开，以及明确等价的 pagination 字段；未知 action、语义参数和内部状态字段仍必须拒绝。格式层不能承担工具选择或答案修正。

## 对下一步结构的约束

下一轮不应继续增加“同一模型 judge/reviewer”或更多完成规则。质量优先的结构应先解决上游表示：

1. **Ready-time RWKV task refinement**：保留完整初始 DAG；当 ready Task 仍是集合、复合步骤或抽象 effect 时，由 RWKV 明确选择 `execute` 或 `refine`。`refine` 返回子 Task DAG，父 Task 只有在所有子 Task 有独立 evidence 后完成。controller 不拆分、不选择成员、不补内容。
2. **原子 Task contract**：Task 显式携带由 RWKV 给出的 `role`（observe/produce/verify/recover）、单一 `target/member`、允许 effect 和 completion evidence 类型。字段只描述模型决定，不从标题关键词推断答案。
3. **Observation lineage**：每个 observation 绑定 action attempt、target、artifact version/hash 和时间；pre-action 阶段不得引用“候选执行结果”。旧失败仅能描述旧 attempt。
4. **Evidence 单向性**：producer 的输入和值不能同时成为 verifier 的期望事实。文件相等、digest、测试、结构检查应从源文件/测试程序/immutable criterion 独立重算；verify Task 默认只读，修改 verifier 必须被 scope 拒绝。
5. **完成投影**：Task 状态不能直接推出 Goal 完成。只有 criterion → evidence reference 全覆盖、引用仍新鲜且对应目标版本，才允许 RWKV生成最终回答；controller不改回答内容。
6. **有限格式归一**：单独做小变量实验，只展开已注册外壳或删除纯 transport 元字段，完整记录 raw/normalized；不得把未知 `write_directory` 映射为别的工具，不补 path/value/content。

最有判别力的下一轮单变量是第 1 项：ready-time RWKV refinement。它直接由失败组和 LH02 正对照支持，保持所有任务选择与子图内容由 RWKV产生，也不需要 controller 根据规则替模型做决定。Round53 reviewer 源码应回退，实验数据与本报告保留作为否证证据。
