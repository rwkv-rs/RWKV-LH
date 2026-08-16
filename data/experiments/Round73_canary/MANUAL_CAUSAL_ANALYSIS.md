# Round73 fixed-15 人工逐题因果分析

## 实验身份与结果

- 固定入口：与 Round72 相同的 15 个历史失败题，模型、endpoint、采样和并发口径不变。
- 已完整落盘 14 题：Agent `1/14`、External `2/14`、Strict `1/14`，FP `0`、FN `1`。
- `E2E-LH02` 在 34 分钟后仍未收敛，人工安全中断。中断时 revision `3669`、Task `88`、Attempt `112`、模型请求记录 `494`，SQLite 状态库已达 `2.1G`。它不计入上面的 14 题分母，也不伪装成模型答错。
- 对照 Round72 fixed15：Agent `2/15`、External `2/15`、Strict `2/15`。Round73 没有达到预注册的 `6/15` 门槛，并且 B02 从 Strict PASS 回退，故不得运行 full90 或上传。
- 方法：逐题交叉检查 `audit.json`、`event_log.json`、`model_trace.json`、最终 workspace 与隐藏隔离 verifier 的外部结果；聚合脚本只用于定位，不代替以下人工因果判断。

## 总结：最早共同缺陷不在工具数量

Round73 证明了两个修复是有效的：移除 pre-execution semantic reviewer 后，B10 的正确代码修改真实执行；`read_files` 也能一次读取 H13 的四文件批次。失败仍集中在一条更底层的放大链：

`Goal/Task 协议先产生错误或过宽合同 -> 当前请求同时携带旧 capsule、完整历史和新 live frontier -> RWKV 被最近 Attempt ledger 锚定，重复旧 read/action -> Task commit 只看模糊 postcondition 或当前 action 自述，产生错误 pass/open -> recovery/goal obligation 追加重复 Task -> 状态与持久化二次膨胀`。

因此 Round73 的 `live_action_frontier` 不是“压缩层”，只是把当前状态又复制了一遍；plan audit 也不是有效 gate，14 个已建计划的题没有一次实质 revision。继续加 reviewer 或接受更多任意 envelope 只会放大相同问题。

## 逐题因果链

### E2E-B01 — Strict PASS

- Goal、两 Task 计划、`write_file` 和 `read_file` 均与请求一致。
- `greeting.txt` 字节精确为 `Hello, RWKV-LH!\n`，Agent、External、Strict 全部通过。
- 结论：单一目标、单一产物、明确字面值的短链已经可工作；这也是后续回归必须守住的最低线。

### E2E-B02 — 从 Round72 PASS 回退

- 最早协议污染：Goal objective 不是用户目标，而是提示中的 `Create a DRAFT immutable Goal. This draft will be independently audited.`。criteria 尚保留真实请求，但 objective 已被控制提示抢占。
- T1 正确读到 `project=Orion`、`count=7`。T2 的 dependency output 和末端 live frontier 都含这两个事实。
- T2 仍先两次对纯文本调用 `read_json`，随后两次重复 `read_file`；每次 postcondition commit 都正确判断“尚未创建 report.json”，但 action selector 继续选择读。
- 放大器：同一 dependency、causal state、relevant memory 又在旧 execution capsule 和新 live packet 中重复出现；模型 reason 已说“应写 report.json”，动作字段却继续复制 read。
- 终局：恢复预算耗尽，`report.json` 未创建。
- 根因：Goal 提示边界污染 + live state 只是追加而非替换 + 没有相同 observation/no-progress 抑制。不是缺少 write_json 工具。

### E2E-B10 — 外部 PASS、内部 FN

- T1/T2 正确读取 `slug.py` 与 `test_slug.py`；T3 的 `write_file` 真实执行并留下能通过隐藏 verifier 的实现。
- 外部测试通过，说明移除错误的 pre-execution reviewer 与 selector `action` 别名修复确实释放了编码能力。
- GC3 没有接受已有事实，goal obligation 新建 T4 “Run tests”。T4 依次误用 `read_json(test_slug.py)`、`python -m pytest test_slug.py`、`python -m pip install pytest`。
- 第二次失败已经明确输出 `No module named pytest`，但恢复没有选择测试文件本身可直接运行的 unittest 入口；第三次又撞上 externally-managed environment。
- 终局：workspace 已正确，Agent 因 recovery budget blocked，形成 FN。
- 根因：完成判定没有复用真实外部可观察测试证据，运行时能力合同没有明确“标准库可用、第三方包不保证”，恢复又把缺包误解为应修改环境。控制器没有改答案，但停止条件仍不可靠。

### E2E-B24 — 错误 mutation 被认证

- Goal objective 同样被 DRAFT 提示污染。
- 初始计划把“去重”“排序”“写 sorted.log”拆为多个 Task，却没有把“保留 log.txt”绑定到 mutation 边界。
- T2 选择 `remove_line(path=log.txt,text=warn z,all=true)`，实际删除两个 `warn z`，不是“保留一个副本”；它还直接破坏了必须保留的源文件。
- Task commit 仅凭 action 输出 `removed 2 line(s)` 宣称“duplicate complete lines were removed”，没有比较去重语义，也没有检查 preserve contract，于是错误 mutation 被标 completed。
- T3 后续反复读取已损坏的 log；最终又回显完整 Attempt ledger，被格式层拒绝。
- 根因：计划 effect target/保护目标缺失，Task postcondition 过宽，action 成功被误当作用户语义正确。格式错误只是后端终止器。

### E2E-M01 — 事实已读，状态回显阻止第一次写

- 初始计划这次正确列出 api/web/worker 三个真实服务，没有 Round72 的虚构 service1/2/3。
- 三个更新 Task 都先正确读取对应 JSON；postcondition commit 正确保持 open，并明确说需要 write。
- 下一次 selector reason 也明确写出“需要 write action”，但 action 字段仍为 `read_json`。fixed arguments 随后连续输出带 `attempt_id/attempt_count/observed_content/...` 的完整 ledger envelope，三次被未知字段拒绝。
- 三个原文件未被修改，summary 未创建。
- 根因：当前 Attempt ledger 在 action prompt 中既作为历史又作为 authoritative packet 重复，模型复制状态对象而不是最末端工具合同。不能靠不断扩充 decoration 白名单解决；应让当前 packet 替换旧历史。

### E2E-M03 — 读取旧文件被误判为已迁移

- T1 正确读取原始 users.json。
- T2 标题/后置条件要求迁移，但动作只再次 `read_json(users.json)`，返回的仍是含 `users/fullname/active/legacy_note` 的旧结构。
- Task draft 与独立 commit 两阶段都返回 pass，理由甚至声称旧输出是“exact postcondition content”。T2 被错误标 completed。
- T3/T4 随后反复读取同一旧 JSON，又反复说“尚未验证”，直到恢复耗尽。
- 根因：read-only action 被允许关闭 mutation Task；模糊 postcondition `users.json is migrated` 没有机器可见的 required effect/target。两个相同 RWKV reviewer 没有产生独立性，只重复同一错判。

### E2E-M06 — 集合只完成一个成员却被标完成

- Goal objective 被 DRAFT 提示污染，但 T1 仍正确读到 selection 是 `alpha.dat` 与 `gamma.dat`。
- T2 先多读一次 selection，随后只复制 alpha。
- Task commit 用“copy action 成功且 package/alpha.dat 存在”证明了“listed files are copied”，完全漏掉 gamma，错误关闭集合 Task。
- T3 创建 manifest 时又把 selection.txt 当 JSON；后续输出完整 ledger envelope，被格式层拒绝。
- 根因：集合 cardinality/coverage 没有进入 Task 合同和证据；单成员 action_succeeded 被提升为全集合完成。格式回显是次级放大器。

### E2E-M12 — 重复读取与 ledger copy

- 源码和 unittest 文件均被完整读到，计划也正确包含两个修复 Task 和测试 Task。
- T3/T4 每个修复 Task 都连续选择 `read_file(math_utils.py)`；postcondition 每次都准确指出源码仍错误，但 selector 继续以“先确认当前状态”为理由重复同一完整读取。
- 第三轮 fixed action 直接回显 ledger 对象并被协议拒绝；任何代码写入都没有发生。
- 根因：没有“同 workspace digest + 同完整 observation + 同 idempotent action + postcondition open”的 no-progress 约束；旧 causal state 比 ACTIVE TASK 的 mutation 目标更强，导致状态复制。

### E2E-M16 — fallback 恢复被 Task 合同反向阻塞

- 初始计划只含五个 primary read，没有 fallback producer、recovered.json producer 或 verify Task；plan audit 仍声称 frontier 完整并 approve。
- item02 解析失败、item04 不存在后，RWKV 对 item04 正确改读 fallback/item_04.json。
- 但 T4 postcondition 固定为“primary/item_04 contents observed”，所以即使 fallback 读取成功，Task commit 仍返回 open；item02 也连续重复读取损坏 primary，直到 blocked。
- 后续 goal obligation 又追加重复 primary read 和 recovered producer，但依赖 Task 已阻塞，无法推进。
- 根因：恢复策略与不可变 Task postcondition 不兼容；planner 在未知 validity 前具体化了只允许 primary 的合同，plan audit 没发现 producer/fallback 缺口。

### E2E-M18 — Goal reviewer 放大错误直到截断

- 首次 Goal draft 的 objective 正确，但它虚构了 `digest_map.json.digests` 包装层，并把“最多 24 criteria”理解为应生成 24 条，大量重复禁止点号路径的条目。
- goal audit 正确选择 revise，却又错误声称用户没有要求目标文件存在/排除自身；final Goal 连续三次扩展同一长列表并以 `finish_reason=length` 截断。
- Run/Task 从未创建。
- 根因：Goal 生成上限被模型当作填满目标，draft→audit→final 的同模型自审链把错误扩写而非压缩；需要源文本绑定和紧凑单一 Goal 边界，而不是第四次 reviewer。

### E2E-H12 — 15 个源文件读完，聚合阶段被第一条历史锚定

- 计划明确列出 15 个 shard read，T1–T16 全部成功；说明长 fan-out 的读取与并行调度已经可用。
- T17 “aggregate data” 的 dependency 中已有 15 个完整 JSON observation，但 action selector 三次只读 shard_01。
- 每次 postcondition 都判断 aggregate 尚未计算；随后 fixed action 输出 T17-A1 的完整 ledger，连续三次格式拒绝。
- 根因：15 份原文被直接堆入一个 action prompt，旧动作 shard01 位于最强锚点；计划还创建了不可观察的“calculated and ready”纯内存 Task，而不是让计算与 aggregate.json producer 成为同一可执行 effect。

### E2E-H13 — 批量读取能力有效，阶段边界与媒体类型仍不稳

- T1、T2、T5 成功使用 `read_files` 一次读取四个文件，证明“大型项目并行/批量读取”底层能力存在。
- T3/T4/T6 却把 txt 先交给 read_json；恢复后 T3/T4 又退化为一次只读一个文件。
- 相同的四文件 read_files observation 在 T5 前两次被 Task commit 判 open，第三次才判 pass，显示 postcondition reviewer 对同证据不稳定。
- 初始 frontier 只含六个读取阶段；因运行未完成 frontier，没有机会生成每阶段 checkpoint 和 final summary。更关键的是用户要求 phase checkpoint 应紧跟每批读取，当前调度却把六批都并行展开，失去“读一批→持久化一批”的语义屏障。
- 根因：planner 不理解 read_files/phase barrier，媒体类型选择不稳，重复 RWKV postcondition review 对同 observation 没有确定性。

### E2E-LH05 — 计划与实际 workspace 同时错位

- plan audit approve 了 11 个仅发现型 Task，并在 reason 中直接声称“不需要创建或验证文件”，与 Goal 明显矛盾。
- T1 标题要求列 shards，却执行 `list_directory(.)`；过宽 postcondition `A directory listing page is observed` 仍被 pass。
- T3 把真实 `recovery_rules.md` 猜成 `recovery_rules.json`，T4 读取不存在 reports；恢复甚至先创建 reports 目录，再反复读错误 JSON 路径。
- 20 个 shard 没有形成选择、hash、summary 或 REPORT producer 链。
- 根因：Task 没有精确 effect target；plan audit 是同模型 rubber stamp；manifest metadata 与 Task target 未绑定。

### E2E-LH11 — 在执行前超过固定 frontier 合同

- Goal 已正确，workspace manifest 也明确列出 40 个文件。
- planner 不采用五个八文件 phase/read_files，而是展开 41 个 Task（list + 40 个逐文件 read）；两次都超过 32 Task 协议上限。
- Run 在 planning 阶段阻塞，0 Attempt。
- 根因：planning prompt 只给 action 名称，不给 read_files 的批量 effect；“最多 32 immediately-ready”也未限制总 Task 数。该题不是模型不能读 40 文件，而是 planner 没把用户已经给出的八文件 phase 映射到批量工具。

### E2E-LH02 — 产物错误后无限重复恢复（中断，不计分）

- 15 个 checkpoint 最终都存在，路径和 `{step,constraints}` 结构正确。
- final/config.json 最终为 `{constraints:{...},step_number:1}`，缺少 `generated_by`，且错误地沿用 checkpoint 外壳；外部目标仍不满足。
- 更早 T17 曾写过含 generated_by 的版本，但仍含用户未要求的 checkpoint 字段；后续 obligation replan 又多次覆盖 final，并重复重写同一批 checkpoint。
- Goal 本身已错误写入“final/config.json contains the step number and constraints object”，把 intermediate 字段传播到 final。实际值和期望值因此再次绑定到同一个错误 Goal 来源。
- 中断时状态已有 88 Task，其中大量标题/目标重复；72 completed、13 pending、2 failed、1 running。494 次模型请求与 3670 次全量 state checkpoint 使数据库达到 2.1G。
- 根因：Goal 字面合同先错；goal obligation 对 unchanged observation 没有重复 frontier 抑制；新 recovery Task 只追加不取代旧分支；实验存储又在每个事件保存全量 state，放大为不可收敛运行。

## 公共根因矩阵

| 公共根因 | 直接证据题 | 下游放大 |
| --- | --- | --- |
| Goal prompt/criteria 与用户原文未绑定 | B02、B24、M06、M18、LH02 | 控制提示进入 objective；中间 schema 被传播到 final；proof 围绕错误 expectation 自洽 |
| `live_action_frontier` 追加而非替换旧历史 | B02、M01、M06、M12、H12 | selector reason 知道应写，action 却复制旧 read；fixed tool 回显整个 ledger |
| Task 缺少 required effect、精确 target、集合 coverage | B24、M03、M06、LH05、M16 | read 关闭 mutation；单文件关闭集合；错误目录 listing 关闭正确目标 Task |
| 同模型多级 reviewer 没有独立性 | M03、H13、M18；全部 plan audit | 相同错误被重复 pass/open；audit rubber stamp 或扩写错误 |
| 相同 observation/fingerprint 无 no-progress 抑制 | B02、M12、M16、LH02 | 重复 read/parse/replan 消耗预算，长链无限追加 |
| planner 不掌握批量 effect 与 phase barrier | H12、H13、LH11、LH05 | 逐文件爆炸、纯内存聚合 Task、checkpoint 延后、frontier 超限 |
| 每事件全量 checkpoint | LH02 | 3670 snapshots/2.1G，验证不能自然收尾 |

## 对 Round72 归因的修正

1. “增加末端 live capsule”方向只完成了一半。必须让它成为 action selection/materialization 的唯一当前状态输入，不能同时保留同一 causal state、dependency 和 evidence 的旧副本。
2. “plan audit”没有获得实证支持。14 个可审计计划均未 revision，且 LH05/H13/M16 的明显缺口被 approve。继续堆同模型审查不是下一步。
3. 移除 pre-execution action review 有正向证据：B10 修改真实执行，H12 也读完 15 shard。该改动应保留。
4. 格式转换只能保留少量已注册常见形态。ledger echo 的反复出现首先是 prompt 状态污染，不应靠无限白名单掩盖。

## Round74 的质量优先结构指导

### P0：单一权威协议脊柱

- Goal：删除 `draft→audit→final` 同模型回声链；用一个紧凑、源文本约束的 RWKV Goal commit。objective 不得复制控制提示，criteria 数量降低并绑定 immutable request 原文。
- Plan：删除没有实效的第二次 plan audit；单一 planner 使用固定 G1i Task batch schema，并看到精简 action effect（尤其 read_files）。frontier 总数设为可恢复的小上限，依赖未观察事实时只创建 discovery barrier。
- Action：保留 `select_action→fixed arguments→execute`，但 action prompt 只含 immutable goal、active task、无损 dependency、当前 Task ledger、last failure 和 action catalog，不再嵌入旧 execution capsule/evidence 副本。
- Completion：相同 RWKV 不再做 draft+review 两次同义判断。先用通用 effect/target/coverage 合同排除“read 关闭 mutation”“单成员关闭集合”，再由一次 RWKV 判断剩余语义。

### P0：no-progress 与重复 frontier 抑制

- 相同 workspace digest、相同完整 observation、相同 idempotent action fingerprint 且 Task 仍 open 时，不再次执行；把“exact call made no progress”作为事实返回 RWKV 重新选择，不替它选择动作。
- 相同 verifier/failure fingerprint 且 observation 未变时不重跑。
- goal obligation/recovery 返回与现有 active Task 合同相同的 frontier 时，不追加第二份；要求 RWKV 在剩余预算内给出不同 Task，或确定性 blocked。

### P0：Goal/Task provenance contract

- Goal criterion 增加用户原文 source quote/ref；控制器只验证引用确实来自 immutable request，不生成 description/答案。
- Task 增加 RWKV 提供的 `effect_kind`、精确 `targets` 和（集合任务需要时）`members/coverage_source_ref`；控制器只验证执行 action 与模型自己提交的合同一致。
- 这不是规则替 RWKV 做决定，而是防止读动作被当作写、错误路径被模糊 postcondition 认证。

### P1：批量读取与阶段 barrier

- planner 明确知道 `read_files` 是“显式路径列表的一次无损批量 observation”，可直接用于 4/8/15/31 文件批次。
- 用户要求 checkpoint/phase 时，frontier 在第一批 read 后停止，下一 frontier 先写该批 checkpoint，再进入下一批；不把所有批次同时展开。
- file-local summary 以后单独实现为 RWKV 派生 observation，必须绑定 raw refs/hash；不能让控制器生成摘要。

### P1：事件日志与状态快照分离

- event/model trace 继续 append-only 全量保留；current state 继续事务保存。
- 只在 milestone 和固定间隔保存完整 checkpoint，不在每个 request/parse 事件复制整份 RunState。timeline 用 event linkage + 周期 snapshot 重建。
- 这首先是“长任务能跑完”的质量条件，不只是效率优化。

## 下一轮门槛

- 先用 B01/B02/B10/M01/M03/M06/M12 七题验证短链：B01、B02、B10 必须 Strict；不允许 read-only action 关闭 mutation Task；不得再出现完整 ledger echo。
- 再跑 H12/H13/LH11/LH02 四题验证批量与长链：LH02 不得追加重复 frontier，数据库/trace 大小必须受控。
- fixed15 至少 Strict `6/15`，FP `<=3`、FN `<=1`；未达标不跑 full90。
- full90 只有 Strict `>31`、External `>=32`、FP `<24`、FN `<=1` 才允许提交上传。
