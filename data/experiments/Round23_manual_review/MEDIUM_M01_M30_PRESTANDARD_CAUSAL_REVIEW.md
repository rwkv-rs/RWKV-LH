# Round23 Medium M01–M30 标准答案接入前人工因果审阅

本文件在不读取 `results.json`、acceptance、参考答案和外部评分字段的条件下，逐题审阅
Goal → Plan → action/effect → state/evidence → terminal。其中 **observed** 是生命周期记录或最终
workspace 可直接复核的事实；**inference** 是仅依据用户请求和公开 workspace 输入所做的因果判断。
原始证据位于 `../Round23/cases/<case-id>/`；Round22 展开审阅位于
`../Round22_manual_review/cases/<case-id>.md`。

## E2E-M01

- **Goal/Plan（observed）**：目标要求按 services 列表更新所有成员并生成摘要；Round23 的 Plan/action 外壳
  得以通过，实际展开了 api、web、worker 三个成员，不再像 Round22 只到 api。
- **Action/effect（observed）**：三个 service 文件和 summary 均被正确写入，共有4次真实修改。这是
  Round23 协议可达性的真实改善，但不等于 Goal 已有证据。
- **Evidence 偏离（observed）**：后续扩张至40个 task/attempt，却是0 claim/0 evidence；同义成员读取和
  witness 重复没有建立“列表中每个成员都完成”的聚合关系。
- **结构含义**：集合任务需要成员发现、成员完成与全称聚合三层状态；外壳解包仅解决“模型决定能否到达执行器”。

## E2E-M02

- **Plan/action（observed）**：RWKV 读取了 calculator 与测试，但修复仍写为
  `sum(value for value, weight in items)`，没有使用 weight；第二次 writer 只重写相同错误内容。
- **最早偏离（observed）**：已观察测试的情况下，生产 payload 本身还是语义错误，这一层是 RWKV 决定错误。
- **Runtime 放大（observed）**：测试使用不存在的 `python`，连续 ENOENT；运行时失败遮住了更早的实现错误。
- **结构含义**：需同时保留“代码与已观察测试不一致”和“测试未真实执行”两个独立失败边，不能把 ENOENT 修复当成任务修复。

## E2E-M03

- **Goal 输出（observed）**：迁移目标的语义基本正确，但稳定拆成6个 criteria，超过协议最多5个的限制。
- **纠错失败（observed）**：第二次完整重复第一次结构；未建立 Task/RunState，因此本题没有测到迁移能力。
- **结构含义**：语义完整性与协议紧凑度不应共用一个“全盘拒绝”状态；纠错 prompt 不应再完整回显希望模型删除的冗余结构。

## E2E-M04

- **Action/effect（observed）**：RWKV 生成了语义正确的 release JSON 与可见两行 Markdown；产物本身已达到用户明示的主要关系。
- **证据首偏离（observed）**：13个 task 中出现4个 claim 但0 evidence；多个 reader 只反复观察各自产物，没有将两个 source 聚合到 release 字段关系。
- **边界事实（observed）**：用户请求没有明确要求 final newline；此处不用未接入的参考答案反推在线行为。
- **结构含义**：生产正确和证据闭合必须独立记录；对多 source 关系需要 fan-in proof，不是追加同义 read-back。

## E2E-M05

- **Source 观察（observed）**：T1 正确读到权威 `docs/requirements.txt`。
- **Model production 首偏离（observed）**：RWKV 没有将具体需求投影为实施计划，而是写出通用的
  “Implement core feature / Add unit tests / Run test suite”。
- **放大（observed）**：write 成功令该 task completed，随后的读取仅证明这份自写文件存在；9个 task、0 evidence 后 blocked。
- **结构含义**：这是 RWKV 的源到产物语义失败，架构则通过 self-expected validation 和任务状态晋级将它放大。

## E2E-M06

- **Goal 输出（observed）**：目标被拆成7个语义相关 criteria，两次都超过最多5个的协议限制。
- **终局（observed）**：0 task/0 attempt，因此 selection/fan-out 能力尚未被 Round23 实际验证。
- **结构含义**：不能将此题归为业务计算错误；首要是 Goal 表达粒度与 contract 错位。

## E2E-M07

- **Source 观察（observed）**：RWKV 读到 defaults 与 override。
- **Model production 首偏离（observed）**：输出保留 defaults 的 top-level `port=8000,workers=2`，没有应用 override 的
  `port=9000,workers=4`；仅 nested trace/source 部分正确。
- **放大（observed）**：同一错误对象被再次写入，六个 claim 也没有形成 evidence；证据失败没有返回产物字段修正。
- **结构含义**：部分 merge 是 RWKV 语义错误；证据系统需要把 path-level mismatch 指向生成该 leaf 的 writer revision。

## E2E-M08

- **Plan 首偏离（observed）**：依赖字段缺失后默认为空，writer T2 因而在 source reader 之前执行。
- **Action/effect（observed）**：T2 在没有看到源时幻觉 auth/billing 等六个 service；T1 后来读到真实
  worker/api/web，但 stale producer 没有被失效。后续还三次对文本 `STATUS.md` 用 read_json。
- **放大（observed）**：无源生产的 action success 被晋级为 completed，迟到的权威观察不会触发下游重算。
- **结构含义**：Plan 必须区分“未给出依赖”和“明确无依赖”；权威 source 晚于 producer 到达时，producer 应成为 stale 而不是继续已完成。

## E2E-M09

- **Plan 首偏离（observed）**：所有 task 都没有 dependencies，priority 使最终测试 T6 第一个执行；source 读取与迁移 writer 全未运行。
- **Action/effect（observed）**：`python` 三次 ENOENT，0 mutation。Round23 使 Plan 外壳能被解包，却也因此更早暴露出错误图和 scheduler 行为。
- **比较含义（observed）**：协议可达性成功不等于任务质量提升；本次采样的错误图使实际生产比 Round22 更早停止。
- **结构含义**：执行前需验证 required producer/read/test 的可达性，而不是默认 priority 能补足因果边。

## E2E-M10

- **Plan 首偏离（observed）**：要创建的目标文件被安排为 writer 之前的“inspect existing target”。
- **Action/recovery（observed）**：T1 三次读取不存在的 target，恢复又使用绝对路径；workspace 和失败指纹都未变，writer 始终饥饿。
- **结构含义**：这是“前置观察对未创建产物无定义”的图错误；相同 observation digest + verifier/action + failure fingerprint 应停止原地重试并返回产物边修正。

## E2E-M11

- **Source 覆盖首偏离（observed）**：只显式读取 `services/api`，却写入 api/auth/jobs/web 四个成员和 summary。
- **Action/effect（observed）**：api 值有源；auth/jobs/web 的 port/workers 是未观察猜测，并会覆盖现有成员信息。
  共59 task/attempt、5次 mutation，0 evidence。
- **放大（observed）**：“处理 services”被单个成员读取提前满足；自写结果又成为后续 expected 值，读取义务持续扩张。
- **结构含义**：每个输出成员要保留 source member provenance；未观察成员不得因为同组其他成员成功而晋级。

## E2E-M12

- **Plan 首偏离（observed）**：对同一 source 文件建立两个并行 whole-file writer，分别处理 safe_divide 与 median，两者都基于 T1 的旧 revision。
- **Action/effect（observed）**：先执行的 writer 修正一项，后执行的 writer 以 stale base 整份覆写，丢失了前一项；最终仍缺 zero check。
- **Runtime（observed）**：测试又因 `python` ENOENT 没有实际验证。
- **结构含义**：same-target writer 必须串行化到明确 revision，或使用可合并的 typed patch；否则弱模型的“分步”会成为丢失更新。

## E2E-M13

- **Source/Model（observed）**：Round23 已正确读取 CSV，但写出 `row_count=4,quantity_total=10,revenue_total=37.5`；
  依据已读取的行可直接算得 revenue 应为39.5。north 也被算成22.5而非17.5。
- **Schema 偏离（observed）**：by_region 成员还附带 quantity_total，而用户只要求 region revenue totals。错误 summary 被写了3次。
- **Verifier 放大（observed）**：T7 对 `sales.csv` 使用 read_json 三次失败；之前的 read-back 只证明错误 JSON 稳定存在。
- **结构含义**：本轮最早错误已从 Round22 的 parser 不可达前移为 RWKV 算术/输出 schema 错误；恢复应回到 source→aggregate writer，不是再读错误产物。

## E2E-M14

- **Plan 首偏离（observed）**：初始 Plan 缺 dependencies，T3–T5 的 writer payload 在 source 观察之前就被构造。
- **早期 effect（observed）**：T3/T4 先后写入 Harness/1.0.0 与 MyApp/1.2.3 等幻觉 release，T5 写入通用 Markdown；与已读取 source 无关。
- **后期恢复（observed）**：obligation 新增 T8/T9 重读真实 source，T10/T11 已正确写出
  Comet/2.1.0/2026-08-12 和排序 changes；但 T12 用来纠正 Markdown 时，tool-choice 被前一 snapshot 强烈污染，输出不完整对象并 blocked。
- **结构含义**：这是 RWKV 无源幻觉、图依赖缺失、旧 producer 未失效、prompt snapshot 污染共同形成的放大链；后来正确 revision 已出现，却没有原子提交整组产物。

## E2E-M15

- **Action/effect（observed）**：list_recursive 发现了精确 docs 集合，最终 index 的 a/b/c 值与当前文件一致；相比 Round22，实际产物明显前进。
- **Provenance 缺口（observed）**：显式内容读取只覆盖 a.txt，b/c 的 line count 没有 content observation 边；只能说产物恰好正确，不能说已被架构证明。
- **Evidence/terminal（observed）**：21 task/attempt、3 claim、0 evidence，proof 扩张后 blocked。
- **结构含义**：记录“产物外部正确”与“生成过程 source-complete”两个不同维度，避免假阴性也避免把猜对当成可追溯完成。

## E2E-M16

- **Action/effect（observed）**：对 id02/id04，primary 失败后 recovery 已成功读到 fallback，说明局部恢复能找到正确分支。
- **State 首偏离（observed）**：“fallback 已被选中”没有作为可提交的 branch outcome 保留；后续 T13 “select source id02”又重新对已知无效 primary02 执行 read_json。
- **终局（observed）**：19 task、10 attempt、0 write，recovery budget 在产生 `recovered.json` 之前用尽。Plan 中 select/normalize/order 还是无独立 effect 的 model_action 节点。
- **结构含义**：条件分支需要 proposed→observed→committed 状态；recovery 的成功观察不能在后续抽象“select” task 中丢失。

## E2E-M17

- **Source 覆盖（observed）**：题面是复数 packages，T1 却只读 core。
- **Action/effect（observed）**：core 被正确更新；matrix 却将 core/web/worker 的 dependencies 全写为空，web/worker 原文件未更新。
  最终9 task、2 write、6 claim、0 evidence。
- **联合原因（observed + inference）**：RWKV 把集合任务收缩为单个成员，架构又没有要求发现集合与产物成员一一对齐。
- **结构含义**：复数 noun 不应依赖规则猜数量，而应由权威目录/manifest observation 生成 member ledger。

## E2E-M18

- **Action/effect（observed）**：最终 `digest_map` 含 a.txt、b.json、nested/c.txt 三个精确 digest，且排除自身；当前 Goal 也不再有 Round22 的自哈希矛盾。
- **Observation 边界（observed）**：只显式 read a.txt，b/c 的 digest 可由 manifest artifact SHA 元数据到达，但该路径没有转换为 CriterionEvidence。
- **Evidence/terminal（observed）**：11 task、1 write、4 claim、0 evidence；WS/WH 类型错误和 proof 扩张之后，`priority=high` 使 run interrupted。
- **结构含义**：artifact metadata 可作为真实 observation，但必须显式标注来源/范围；不能一方面把它隐形给生产者，另一方面又在 proof 中称没有 source。

## E2E-M19

- **Goal 输出（observed）**：两次都给出8个 criteria 而被拒绝；同时对 `error_paths` 的描述内部不一致，一处是 string→number object，另一处是 unique sorted paths。
- **终局（observed）**：0 task，因此本轮同时存在 protocol cardinality 与 Goal 语义内部矛盾，不能只归类为超数。
- **结构含义**：纠错应分别告知“表达过细”与“两个字段定义冲突”，避免完整错误对象成为重复锚点。

## E2E-M20

- **Goal 输出（observed）**：语义正确但拆成7个 criteria，两次稳定重复并因最多5个而被拒绝。
- **终局（observed）**：0 task/attempt，代码能力未被测试。
- **结构含义**：这是纯表示层可达性问题；不应用 controller 自动改写语义，应优先简化协议或纠错上下文。

## E2E-M21

- **正确中间状态（observed）**：T1/T2 读取两个 source，T3 第一次 writer 已正确创建合并记录列表。
- **最早破坏边（observed）**：T5 “add record_count”使用 whole-file write，把整个文件覆盖为
  `{"record_count":3}`；T6 重复。最终 records 全丢失。
- **放大（observed）**：各个阶段被当成对同一目标的独立全量 writer；action success 使破坏性部分对象也成为 completed。
- **结构含义**：这类题不能只看最终错误。架构必须保留 revision lineage，并在部分更新时要求新 revision 保留已建立 postcondition。

## E2E-M22

- **Source 观察（observed）**：config、policy、request 全部被正确读取。
- **Model production 首偏离（observed）**：RWKV 忽略 allowed keys，把 debug/owner/region/replicas 全部应用，`rejected` 置空；同一错误结果在 filter/merge/sort/create 阶段被写入5次。
- **放大（observed）**：计划将一个 policy transform 拆成多个 whole-file writer，却没有 typed intermediate；自写结果又被反复读取。
- **结构含义**：最早是 RWKV 规则应用错误；架构应使 policy decision 的 accepted/rejected 集合成为可观察中间状态，而不是让每步重写最终文件。

## E2E-M23

- **Source/Plan（observed）**：T1 读到 build_plan 明确声明三个文件；Plan 却只有一个“Write declared files”集合 task。
- **Action/effect 首偏离（observed）**：T3 只写入 `dist/bin/start.sh`，然后整个三成员 task 立即 completed。
  `dist/config/app.json` 和 `dist/README.txt` 始终不存在。
- **放大（observed）**：manifest 却列出全部三路径；后续 verifier 只读 start.sh、manifest 和目录，每次成功都被标 completed。最终12/12 task “completed”，workspace 仍缺两个必需文件。
- **结构含义**：这是“单成员 action success → 集合 task completed”的直接证据；member ledger 必须由 authoritative manifest 生成并逐成员提交。

## E2E-M24

- **Source 观察（observed）**：代码与 tests 都已读取。
- **Model code 错误（observed）**：两个交替 writer 均保留 LIFO `pop()`；所谓重复检查使用
  `task_id in self._items`，但 `_items` 是 tuple 列表，不会按 id 命中。最后一个 writer 甚至又删除重复检查。
- **Plan/runtime 放大（observed）**：四个 same-target whole-file writer 基于 stale source 互相覆盖；`python` 三次 ENOENT，实际测试没有运行。
- **结构含义**：这题包含 RWKV 代码语义错误、revision 冲突和 runtime capability 三层；任一层修好都不能代表另两层已解决。

## E2E-M25

- **Tool/effect 首偏离（observed）**：目标是 Markdown，RWKV 却重复使用 `write_json` 把一个 JSON string 写到
  `CHANGELOG.md`；最终 bytes 是 JSON 字符串编码，不是 Markdown 文本。
- **Model production 错误（observed）**：1.2 版本内将 fix 排在 add 前，且有多余空行；这些语义/字节错误在六次写入中稳定重复。
- **Plan 放大（observed）**：T3/T4 名义上是 sort/group 内部计算，实际都整份修改 final target；没有 typed changelog intermediate。
- **结构含义**：artifact type 必须是执行契约的一部分；抽象 compute task 不能因为需要 effect 就默认把 final file 当 scratch state。

## E2E-M26

- **Source 覆盖首偏离（observed）**：T1 标题称读 records 和 schema，实际只执行一次 `read_json(records.json)`；
  `schema.json` 未读取。
- **Model production 错误（observed）**：`id=0` 的第1项被放进 valid；第2项 `id=2,name="",status=other`
  却被附加 `invalid_id`；输出的 valid/rejected 分类与用户明示规则不一致。
- **放大（observed）**：错误 validation 被写入6次，中间仅小幅变动 reasons；每个 writer/read-back 都声称可满足五个 criteria，但0 evidence。
- **结构含义**：复数 source task 不能以一次 action success 结束；规则分类需要 schema revision 与每条 record decision 的 provenance。

## E2E-M27

- **Source 观察（observed）**：graph 被两次正确读取：api→core，app→api/web，web→core，core/docs 无依赖。
- **Model computation 首偏离（observed）**：RWKV 写出全局字母序 `[api,app,core,docs,web]`，api 位于 core 前，app 位于 api/web 前，根本不是拓扑序。
- **Verifier 放大（observed）**：T5–T9 只反复 read_json 同一错误对象，没有用 graph edges 验证 index 约束；两个 writer 都成功后 blocked 在 obligation。
- **结构含义**：这是清晰的 RWKV 算法决定错误，架构的缺陷是将“文件可读”当作“拓扑关系已建立”，并未将 verifier 失败返回计算边。

## E2E-M28

- **Source/Plan 首偏离（observed）**：T1 只读 cutoff，没有 list/read `logs/` 集合；Plan 仍猜测哪些文件应移动。
- **Model/effect 错误（observed）**：cutoff 为 2026-08-01，却只处理 2026-07-20，将 2026-07-31 错列为 kept；而且使用 `copy_file` 而非 move，所以 07-20 仍留在 logs。
- **放大（observed）**：单文件 copy 使整个“Move files older than cutoff” task completed；report 两次写入相同错误集合。恢复最后三次对目录用 read_json。
- **结构含义**：需要“发现集合→按 cutoff 决定每成员→移动效应→source absent + destination bytes equal”的成员级状态；copy success 不能满足 move postcondition。

## E2E-M29

- **Source 观察（observed）**：base 含 bye/cancel/hello/save，locale 只含 hello/save，两者都正确读取。
- **Model production 首偏离（observed）**：第一个 merge writer 就删除了 bye/cancel 值，只把它们放进 `missing_keys`；这违反“Preserve every base key / use base value for missing keys”。
- **后续状态（observed）**：T5 正确将 `missing_keys` 排序为 bye,cancel，但后续 whole-file writers 只重复不完整对象；T7–T22 全部只读最终文件。
- **结构含义**：RWKV 将“本地化缺失”错解为“输出删除”；架构需要用 original base-key set 对最终 key set 做 preservation relation，不能仅自读输出。

## E2E-M30

- **Source 观察（observed）**：T1/T2 已读取 config 和 MIGRATION；迁移规则与现有值都已在当前上下文。
- **Protocol 首偏离（observed）**：T3 tool-choice 不仅选择 `write_json`，还一次输出 path 和语义基本合理的 report content；但使用 `schema_version:1`、多出 arguments，两次被 action-choice contract 整体拒绝。
- **放大（observed）**：纠错请求完整重放后，RWKV 逐字复制同一合并输出；T3 blocked，后面的 config writer 和 verifier 从未运行。
- **结构含义**：弱模型自然地把“选工具”与“填参数”合并；两阶段 contract 反而丢弃已由 RWKV 生成的语义内容。下一结构应试验单阶段原子 action proposal，由模型自身同时给出 name+arguments；controller 只做 schema/scope 校验，不替它改语义。

## Medium 组横向结论（仍未接入标准答案）

1. **最底层状态错误得到更强证据**：M23/M26/M28 都将一个 member action 成功晋级为整个复数/集合 task completed；M16 又将已选中 fallback 的分支状态丢失。
2. **错误并不都是架构生成的**：M02/M05/M07/M13/M22/M24/M27/M29 的 RWKV 生产 payload/算法已在已观察 source 下直接错误。架构的责任是不把这些 proposal 早熟晋级、不用 self-read 伪证它，并把失败返回最早生产边。
3. **正确状态可以被后续放大链破坏**：M12/M21/M24 的后续 whole-file writer 覆盖前一 revision；M14 后期已产生正确 JSON，但未能原子纠正配套 Markdown。因此必须分析全链，不能只看首次或最后一次输出。
4. **Plan 仍不是可执行因果图**：M08/M09/M10/M14 缺 producer→consumer 边；M12/M21/M25 将一个 logical transform 拆成冲突 writer；M16 将 select/normalize 伪装成外部 task。
5. **Proof 现在同时造成假阴性和自证循环**：M01/M04/M15/M18 有正确或高度正确产物却0 evidence；M05/M22/M27 又能对错误产物重复 read 并将 action 标 completed。两者源于“观察存在”和“关系成立”未分层。
6. **协议设计也是能力瓶颈**：M03/M06/M19/M20 卡在 Goal criteria 数量；M30 则表明两步 action-choice/tool-action 与 RWKV 自然输出形态冲突。优先简化为模型一次给出完整 proposal，比在纠错中重复整份错误对象更值得预注册试验。
7. **Round23 本身有局部价值**：M01/M15/M18 显示透明外壳归一化提高了某些任务的产物可达性；但 M09 说明“能执行 proposal”不能作为“proposal 更好”的替代指标。

