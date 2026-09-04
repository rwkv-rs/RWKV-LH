# Round72 fixed-15 人工因果分析

## 实验身份

- 固定数据：沿用 Round71 的 15 个历史失败入口，题目与顺序记录在 `RUN_PROTOCOL.json`。
- 版本：Round72，透明协议边界 `transparent-protocol-boundary.v11`。
- 结果：Agent `2/15`、External `2/15`、Strict `2/15`，FP `0`、FN `0`。
- 对照：Round71 为 Agent `0/15`、External `1/15`、Strict `0/15`，FN `1`。
- 用途：人工逐题确认最早错误、后续放大与公共结构根因；聚合统计只用于定位入口，不代替因果判断。
- 生成方式：交叉检查每题 `audit.json`、`model_trace.json`、`event_log.json`、最终 Task 图、workspace 和外部验收。

## 结论

Round72 修复了 Goal 输出容量、ready frontier 容量、部分固定格式和当前 Attempt/Artifact 注册问题。B01、B02 已 Strict 通过；LH11、M18 从零 Task 进入真实执行；H12、LH02、H13 的长链长度明显增加。这证明 Round71 的基础设施归因有效。

但本轮同时暴露了更靠近主干的四个结构缺陷：

1. **计划在读取事实之前臆造具体路径、值和中间产物。** M01、M18、LH05、H13 最明显；B10、B24、M03、LH02 也存在不可执行、偏离目标或字面合同漂移的 Task。
2. **动作语义审核把“本次调用是否有效”误写成“整个 Task 是否已经完成”。** H12、M16 的 reviewer 明确承认调用正确，却仍返回 `revise`；M06、M12、B24 则进入 selector/reviewer 回声循环。
3. **决策所需事实虽然在长提示中存在，但没有形成紧凑、唯一、靠近响应边界的状态胶囊。** M06 的 selection 和复制历史全部可见，模型与 reviewer 仍同时误判 beta；H13、M12 也被旧动作和错误 Task 锚定。
4. **固定工具调用仍会回显状态包或在 meta selector 使用直接 action 字段。** B10、LH02、LH11 的语义动作已经正确，但被协议边界拒绝。只能对已观察到的少量公共形态做透明转换，不能据此增加答案筛选器。

这些问题不是四套独立缺陷。它们形成同一条放大链：

`缺少事实约束的计划 -> 错误 Task/postcondition 成为长期锚点 -> 冗长历史稀释当前事实 -> selector 选择重复/不推进动作 -> reviewer 混淆动作与任务完成并把错误 reason 回灌 -> 恢复输出回显状态 -> 协议硬阻塞`。

## 逐题因果链

### E2E-B01 — Strict PASS

- 结果：`greeting.txt` 精确正确，生产与读取验证两个 Task 都完成，外部验收通过。
- Round71 问题：冗余验证 Task 先误用 `read_json`，随后正确的 `read_text` 因未注册名阻塞。
- Round72 变化：`read_text -> read_file` 固定别名和 live frontier 使恢复链可通过。
- 结论：透明工具名归一化有效；该题仍有一次额外验证，但不再影响质量。

### E2E-B02 — Strict PASS

- 结果：先读取 `input.txt`，随后写出精确的 `{"project":"Orion","doubled_count":14}`，最终读取验证通过。
- 中间失败：T2 首次尝试仍发生 JSON 解析失败，但失败分析和当前事实包成功引导 RWKV 写入正确结果。
- Round71 问题：相同 identity 重复字段触发硬阻塞。
- Round72 变化：固定 identity 归一化和当前 packet 使模型的恢复动作被执行。
- 结论：该题证明“允许模型真实犯错、观察结果、再恢复”比用规则替模型选择答案更有效。

### E2E-B10 — 最终格式阻塞，前置计划错误

- 正确进展：RWKV 读取源码和测试；真实测试暴露 `NotImplementedError`；失败分析正确选择 `write_file`，并生成了可执行的 `slugify` 实现。
- 最早错误：初始计划把“运行测试”和“实现 slugify”两个生产 Task 都预填为 `read_file`。T3、T4 因后置条件/确定性检查过弱而被形式化标成完成，真正缺口直到 T5 才暴露。
- 最终阻塞：`write_file` 调用的 `action+arguments` 完全可执行，但 RWKV 同时回显 `attempt_id/task_id/attempt_count/tool_success/workspace_digest` 等当前状态字段。三次都被未知字段拒绝，正确修改从未落盘。
- 根因：Task effect 与 postcondition 没有在计划时做可执行性自审；工具边界也没有识别已观察到的“canonical action + 状态回显 envelope”。
- 性质：不是编码能力失败；正确恢复内容被结构阻塞。

### E2E-B24 — 不可执行的纯内存 Task

- 正确进展：T1 完整读取原始 `log.txt`，原文件保持不变。
- 最早错误：计划把“去重”“排序”“写 sorted.log”拆成三个 Task；前两个 Task 的后置条件没有对应 workspace effect，也没有把变换结果持久化。
- 放大：T2 继续选择 `read_file`；reviewer 正确指出读取无法移除重复，但建议写回 `log.txt` 又与用户要求保留原文件冲突，三轮后阻塞。
- 根因：计划缺少 effect reachability；数据变换应与产生 `sorted.log` 的动作合并，而不是建成不可观察的内存 Task。

### E2E-M01 — 读取前臆造文件名并破坏保留合同

- 正确进展：T1 列出真实文件 `api.json`、`web.json`、`worker.json`。
- 最早错误：初始计划却提前创建 `service1.json/service2.json/service3.json` 三个更新 Task；这些文件名没有任何事实来源。
- 放大：T2 用 `write_json` 创建 `service1.json`，且只写 version/runtime，未保留 name 和无关设置；现有 deterministic check 只验证了模型自己声明的完整 value，因此把错误产物标成完成。
- 后续：不存在的 service2/3 触发失败，selector 与 reviewer 在 `read_json`/`write_json` 之间循环，始终受错误 Task 名锚定。
- 根因：数据依赖 Task 在 discovery 前被具体化；`write_json` 的 effect check 证明“写入与调用参数一致”，不能证明“满足 immutable Goal 的保留要求”。

### E2E-M03 — 目标产物与错误中间 Task 冲突

- 正确进展：RWKV 读取 `users.json`，随后写出 schema_version、records、display_name、status 和保留的 id/tags；实际迁移能力已被执行。
- 最早错误：计划凭空增加“创建 migration script”，而用户只要求迁移 JSON。这个 Task postcondition 成为后续唯一决策边界。
- 内容错误：写出的记录仍包含 `legacy_note:null`，违反“remove obsolete field”。
- 放大：虽然 workspace 已接近目标，Task commit 仍因“没有脚本”保持 open；replan 又重复创建脚本 Task，reviewer 最终拒绝直接写迁移结果。
- 根因：计划添加用户未要求的中间产物；同时缺少目标级 exact-schema 验证来捕获 `legacy_note`。

### E2E-M06 — 事实存在但状态前沿不紧凑

- 正确进展：T1 明确读到只应复制 `alpha.dat` 和 `gamma.dat`；T2 成功复制 alpha、beta、gamma。
- 最早错误：进入复制 Task 后，模型先列出全部 assets，随后把“可见文件集合”误当成“选择集合”，错误复制 beta。
- 关键证据：最后 action-selection 提示中既有 dependency output `alpha.dat/gamma.dat`，也有所有成功 attempt 和 package artifacts；但这些事实位于长历史中，末端 authoritative packet 只重复抽象 Task，没有携带 selection 与已完成目标集合。
- 放大：task commit 正确保持 open；模型又列 assets 而不是 package，并反复重拷 alpha。reviewer 也错误声称 beta/gamma 尚未复制。
- 根因：状态不是缺失，而是决策相关事实没有被压成靠近响应边界的确定性胶囊；重复 reviewer reason 进一步污染选择。

### E2E-M12 — selector/reviewer 回声循环

- 正确进展：源码和测试均被完整读取，格式层已经能进入真实 selector，而非 Round71 的 meta 协议直接阻塞。
- 最早错误：修复 Task 的第一次动作仍是重复读取 `math_utils.py`；Task commit 正确判断 open。
- 放大：后续 selector 三次都选择再次 `read_file`，理由是“先检查当前内容”，即使同一内容已经在 dependency/current evidence 中。reviewer 三次原样拒绝，但没有产生新 observation，形成纯语义回声。
- 根因：当前事实前沿未突出“源码内容已经观察”；三轮 pre-execution review 没有新增事实，却消耗恢复预算并硬阻塞。
- 性质：尚未真实检验代码编辑能力。

### E2E-M16 — reviewer 拒绝自己认定的正确调用

- 正确进展：一次读取五个 primary，随后成功读取需要 fallback 的 item02 和 item04。
- 最早错误：fallback Task 的 postcondition 要求“每个 id 的 fallback validity 已知”，但只有实际需要的两个 fallback 文件被读取；Task 边界表述过宽。
- 决定性失败：对下一次 `read_json(fallback/item_02.json)`，review reason 同时写出“该调用不推进”和“正确动作就是读取 item02”。三轮都返回 `revise`。
- 根因：reviewer 将“整个 Task 尚未完成”错误投射为“当前动作不应执行”，并复制自己的矛盾 reason；这是审核接口职责混淆，不是 fallback action 错误。

### E2E-M18 — Goal 修复后暴露无 producer 计划

- Round72 进展：Goal audit 不再截断，正确进入 5-Task 计划并列出 `inputs/`。
- 最早错误：计划没有读取文件精确字节、计算 SHA256 或写 `digest_map.json` 的生产 Task，反而安排三个读取尚不存在 `digest_map.json` 的重复 Task。
- 放大：FileNotFound 后，selector 的 reason 明确知道必须先创建目标，却仍选择 `read_json`；reviewer 重复拒绝，最终阻塞。
- 根因：producer-before-consumer、目标覆盖和重复 Task 均未在计划阶段审计；错误 Task postcondition压过模型 reason 中已经表达的正确策略。

### E2E-LH02 — 长链成功，字面合同错误被放大

- Round72 进展：完成读取输入、15 个 checkpoint 写入、final 写入和 final 验证，共 19 个 Task、21 次 Attempt；ready 容量问题已解除。
- 最早错误：计划把用户明确要求的目录 `checkpoints/` 写成 `checkpoint/`。这一单字符错误被复制到全部 15 个 checkpoint。
- 第二错误：step11、step13 使用 `step_number`，其他使用 `step`；final 使用 `step_number`。目标要求的字段合同没有保持一致。
- 最终阻塞：验证 Task 在读完 step01 后，下一次正确选择 step02；工具调用同时回显完整 task ledger/artifacts envelope，被未知字段拒绝三次。
- 根因：计划缺少 immutable literal/path consistency 审计；长链执行忠实放大了早期计划错误；固定边界仍不识别常见状态回显 envelope。

### E2E-LH05 — 计划只检查不存在输出，没有生产链

- 正确进展：能列出 shards 和 fallback 目录。
- 最早错误：5 个计划 Task 只是检查 shards、fallback、recovery_rules、reports 和 shard_summary；完全没有读取 20 个 shard、fallback 选择、精确字节 hash、聚合、写 summary/REPORT 的生产步骤。
- 具体错误：把 markdown `recovery_rules.md` 固定成 `read_json`；读取不存在的 reports 和 shard_summary；恢复甚至在 workspace 根创建错误的空 `shard_summary.json`。
- 放大：同一 JSONDecodeError 重复三次；其他并行 Task 在不存在输出上失败；运行没有进入任何真实 shard 处理。
- 根因：计划目标覆盖、工具/媒体类型匹配、producer-before-consumer 同时缺失。

### E2E-LH11 — 大批读取已实现，协议与上下文容量成为新边界

- Round72 进展：Goal audit 通过，生成 10 个 Task；前五个 `read_files` Task 已读取全部 40 个 artifacts。Round71 的零 Task 阻塞已修复。
- 最早结构问题：计划把“读取八文件”和“提取两个 IMPORTANT fact”拆开，后续 extraction Task 又从同一批文件重新读取；没有把模型提取结果定义为可持久化、可引用的派生 observation。
- 放大：Task commit 对 extraction 保持 open；selector 使用常见 `{"action":"read_files","reason":...}`，但边界只接受 `action_name`，并把它当成直接真实工具调用，报 expected `select_action`。
- 容量证据：一次 Goal criterion provenance commit 的本地 prompt 达 28904 token，超过 16384 context 的安全容量。
- 根因：selector 常见字段别名未归一；长任务缺少 RWKV 生成、带原始引用的分层摘要/派生 observation；goal proof 仍投影过多原文。

### E2E-H12 — 正确的第 13 次读取被审核器阻塞

- Round72 进展：连续成功读取 shard01–shard12，当前 attempt ledger 和 evidence 均保持完整。
- 最早错误：T1 postcondition 同时要求 shard_count 和 item_count，却只用目录 listing；计划的 discovery Task 自身不可一次满足。
- 决定性失败：RWKV 正确选择 `read_json(shards/shard_13.json)`。reviewer 明确写出“proposed call is valid and will advance”“should be approved”，却因为 15 个 shard 尚未全部读完返回 `revise`。
- 放大：两轮 review 继续承认调用正确，仍不批准；第三轮建议修改 immutable Task postcondition，最终硬阻塞。
- 根因：action review 与 task completion 是两个不同决策，当前 schema/提示把它们混成一个语义 gate。

### E2E-H13 — 容量修复后，缺少内容事实的计划被执行

- Round72 进展：13 个 Task 被合法接受，不再因第 9 个 ready Task 整批拒绝。
- 最早错误：T1–T6 只列出六批文件名，从未读取文档内容；T7 起却直接把每批所有文件都写成 `priority_filenames`，等价于在没有 PRIORITY/signal 事实时猜答案。
- 放大：前三个 checkpoint 被写出且形式化通过；T9/T10 又把 `.txt` 用 `read_json` 打开，重复 JSONDecodeError；T10 selector/reviewer 围绕同一错误 read_json 循环。
- 根因：data-derived mutation 没有强制依赖实际内容 observation；Task effect check 只验证写入等于调用参数，无法证明 priority 判断来自源文件。

## 公共根因矩阵

| 根因 | 直接题目 | 典型放大 |
| --- | --- | --- |
| 计划缺少事实依赖、effect reachability 和 producer-before-consumer | B10、B24、M01、M03、M18、LH05、H12、H13 | 错误 Task 成为长期状态锚点，后续恢复无法跳出 |
| 计划未保持 immutable path/field/保留合同 | M01、M03、LH02 | 同一个早期错误被复制到多个最终产物 |
| action review 与 task completion 混淆 | M06、M12、M16、H12、H13、B24 | 正确或可推进动作被 `revise`，reason 回灌形成循环 |
| 决策相关事实未形成末端状态胶囊 | M06、M12、M16、H13 | prompt 有事实但模型仍采用旧失败或抽象 Task |
| 常见 meta/action envelope 未归一 | B10、LH02、LH11 | 已生成的正确动作未执行 |
| 大任务缺少带来源的 RWKV 派生 observation/分层摘要 | LH11；将影响大代码与搜索任务 | 原文堆积超 context，提取结果无法成为后续可靠输入 |
| deterministic effect check 被误当目标正确性 | B10、M01、H13 | “执行参数成功”被放大为“用户目标已满足” |

## 下一轮结构指导

### P0：由 RWKV 自审并重写完整计划

计划保存前增加一个独立、可审计的 RWKV plan audit/revision 边界，至少检查：

1. 每个 Task 的 postcondition 是否能由已注册 action effect 建立或由多个明确动作推进；禁止无持久化载体的纯内存 Task。
2. 读取尚不存在的输出是否有 producer 依赖；数据派生 mutation 是否依赖对应原始 observation。
3. 未观察 workspace 内容前，不得具体化内容派生的文件名、值、分类或摘要。
4. 所有 Goal criteria 是否有生产与最终验证覆盖；不得添加用户未要求的中间产物作为完成条件。
5. 用户给出的路径、字段名、数量、保留/删除合同是否逐字保持。

控制器只能验证 schema、注册动作和依赖闭环；计划内容的修改必须来自 RWKV 的完整 revised plan，不能由规则补 Task、参数或答案。

### P0：删除重复的 pre-execution 语义 action gate

固定 schema、workspace scope、路径安全和工具参数检查通过后，执行 RWKV 选定的 action，并让真实 observation 进入恢复链。action review 不能再判断整个 Task 是否完成；Task completion 只在执行后由独立 postcondition commit 处理。

这不会修改 RWKV 输出，也不会替模型选动作。相反，它移除 H12/M16 已证实的假阴性来源，让模型像正常 Agent 一样从真实执行反馈中修正。副作用仍受现有 sandbox、`shell=False`、scope 和 action schema 约束。

### P0：确定性 live-state capsule

在每个 action selection/materialization 响应边界末端，投影一个小而完整的当前状态胶囊：

- immutable active Task/postcondition；
- dependency outputs 的原文或无损结构值；
- 当前 Task 已成功/失败动作的有序 ledger；
- 当前 workspace artifacts 的 path/hash；
- 尚未满足的具体集合仅可来自 RWKV 已提交的 Task/attempt 状态，不由控制器推断答案。

历史原文继续保留引用，但不能与 live frontier 混排。胶囊只重排和压缩已持久化事实，不生成摘要结论。

### P0：透明格式边界 v12

仅增加两类已在本轮多题出现的固定表示：

1. selector 内 `action` 作为 `action_name` 的字段别名，值必须是已注册 action，reason 原样保留；不接受 arguments，不改变动作选择。
2. fixed action 的 canonical `action+arguments` 外层附带闭集 state-ledger echo 时，分离 echo 并执行原始 arguments；每个被分离字段必须满足固定类型/当前 state identity，raw/normalized payload 与 digest 全量审计。

未知语义字段、冲突 identity、未注册 action、缺参数继续 fail closed。不能扩展为从任意文本“猜”工具调用。

### P1：RWKV 派生 observation 与分层总结

为大代码、大搜索和多文件任务增加统一的 RWKV-only 派生 observation：

- 每个文件/搜索结果先保留 raw ref、path/URL、hash 和完整原文；
- RWKV 生成 file-local/result-local summary，summary 必须绑定输入 refs；
- 上层 RWKV 只聚合已绑定 summaries，同时仍可按 ref 回读原文；
- 任务标题、用户输入短摘要只用于 UI/导航，不成为 Goal、动作或完成证据；
- 最终答案和验收仍由 RWKV 基于可追溯证据生成，控制器不得改写。

这正是 `ai00-x-client` 可借鉴的“保护 live frontier/明确压缩边界”，但不能采用自由摘要作为事实源。

### P2：hidden-state 路由仅做后续 shadow 实验

`rwkv7-state-embedding` 的 93.25% 是特定 R0–R3 难度标签的监督分类，不是当前 coding/research 意图路由。只有后端暴露稳定 hidden/state API、建立 RWKV-LH 自己的冻结标签集后，才可离线训练并 shadow 记录；在证明不改变答案前不得控制 action、验收或最终输出。

## 下一轮门槛建议

- 继续使用相同 fixed15、相同模型和参数。
- Strict 至少 `6/15`，FP `<=3`，FN `<=1`；B01、B02、B10 必须 Strict。
- 单独记录：plan audit 首轮/修订结果、review gate 被移除后实际执行的动作、state capsule digest、所有格式转换。
- 只有 fixed15 达标才运行完整 90；只有完整 90 超过已上传 baseline 且 FP/FN 恢复门槛满足，才提交上传。

