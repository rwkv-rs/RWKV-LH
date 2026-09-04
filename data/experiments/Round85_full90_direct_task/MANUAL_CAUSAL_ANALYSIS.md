# Round85 全量 90 题逐题因果分析

## 结论

Round85 不能判定为“已经没有问题”。固定协议下的结果为：

- Strict E2E：`0/90`
- Agent completed：`0/90`
- External acceptance：`7/90`
- False positive：`0`
- False negative：`7`
- 模型请求：`424`，平均 `4.71/题`

相较 Round81 的 Strict `0/90`、Agent `0/90`、External `10/90`，本轮外部正确数减少 3。请求数从 `1533` 降到 `424` 主要是因为更多题在第一、二次请求就被协议层阻断，不是质量提升。

本轮验证了两个不同事实：

1. 删除两阶段 selector 后，旧的“selector 要求选择、模型却直接调用工具”的结构冲突消失；Round85 产物中没有 `lh_select_operation`。
2. 一次性向弱模型暴露 20 个完整操作 schema 产生了更严重的首步偏置：87 个进入 Task lane 的用例中，首个操作有 70 个是 `lh_chunk_map`，占 `80.5%`。Round81 的首选操作分布则以 `read_json=24`、`write_file=22`、`lh_workset=20`、`read_file=18` 为主，只有 1 次选择 `lh_chunk_map`。

因此，当前“全部工具直接暴露”的结构不是质量最好的结构。它消除了一个接口矛盾，但扩大了弱模型对显著、复杂 schema 的错误吸附。

## 从后向前的共同因果链

### A. 首步工具面偏置（70/87）

Task lane 同时注入全部操作 schema 后，RWKV 大量选择 `lh_chunk_map`，包括本应一次读写即可完成的简单题。模型本身作出了错误选择，但接口把一个复杂且显眼的分块操作放在与普通文件操作同一竞争面，显著放大了这种错误倾向。

### B. 路由元数据与语义参数边界不一致（至少 37 题）

- 28 题输出 `function + params + task_id`，被最外层 exact-key 校验拒绝。
- 9 题把 `task_id` 放进 `lh_chunk_map.params`，被操作参数校验拒绝。

模型稳定表达了“这个调用属于 T1”，但当前 wire schema 既不允许顶层携带路由字段，也不允许参数中携带。简单格式转换层不能静默删除或搬移这个字段，否则它就在修改语义；应从协议本身明确路由字段的位置并验证它等于当前活动任务。

### C. 完成协议与模型稳定输出不匹配（16 题）

`lh_task_done` 当前只接受空对象，但模型反复输出 `task_id`、`target_task`、`target_task_id`，有时还携带 `source_*`。其中 B01、B09、B30 的产物已经通过外部验收，仍在完成边界被拒绝。应让完成协议显式接收并核对当前任务引用，而不是靠转换层丢弃字段，更不能替模型宣布完成。

### D. 无变化动作被重复执行（B01、B13、B30、LH02、M23 等）

产物已经正确或动作已经生效后，RWKV 仍重复同一写入/替换。当前 attempt/event 标识会让表面 observation digest 变化，因此相同 workspace、相同动作、相同结果没有被识别为同一失败状态。重复执行最终把正确产物带到 attempt exhaustion 或后续协议错误。这里需要基于 workspace/artifact/effect 的稳定 observation fingerprint；它只能阻止无效重跑并要求 producer 修正，不能自动完成任务或改写模型答案。

### E. 展示态对象被当成写入态对象回填（6 题）

`lh_replace_task` 的新任务只允许 `key/objective/after/done_when`，模型却复制了上下文中的 `task_id/revision/workset` 等运行时字段。根因不是单个字段名，而是同一上下文把“运行时任务展示对象”和“模型可提交的任务提案对象”混在一起。应投影最小 proposal view，而不是为每个多余字段加特判。

### F. 纯格式、工具参数和生成稳定性问题

- 4 题使用 `parameters` 作为参数容器；这是简单格式转换层可以无语义地支持的常见别名。
- `end_line/max_lines/start_byte` 反映文件工具分页接口不统一。
- 5 题分块 source 指向目录或不存在路径，说明模型在没有先观察 workspace 时被诱导规划来源。
- 6 题出现截断或递归重复 JSON，主要发生在大 Task Graph/replace-task/chunk instruction 生成中；应减少一次生成负担并设置可恢复的结构边界。

## 基础题逐题分析（30）

| 题目 | 结果 | 从起点到终点的错误链 |
| --- | --- | --- |
| B01 | External PASS / Agent FAIL | 首次 `write_file` 已生成正确产物；随后 22 次重复相同 `replace_text` 且 workspace 无实质变化；最后 `lh_task_done` 携带 source/target task id，被空参数 schema 拒绝。是假阴性。 |
| B02 | FAIL | 首步误选 `lh_chunk_map`；把 `task_id=T1` 放入 params；在任何工具执行前被参数 exact-key 校验阻断。 |
| B03 | FAIL | 与 B02 同类：首步 chunk 偏置，随后嵌套 `task_id`，0 次有效 attempt。 |
| B04 | FAIL | Goal 已生成 3 个任务；首个 Task 调用为 `lh_chunk_map`，顶层额外 `task_id` 被 call-envelope 拒绝。 |
| B05 | FAIL | 先进入不必要的 chunk/child 流程；随后生成的 `lh_replace_task` JSON 截断，结构无法恢复，未执行有效任务动作。 |
| B06 | FAIL | 不必要地建立 2 个 chunk child 并 reduce；最终 `lh_task_done(target_task=...)` 与空参数完成协议冲突。 |
| B07 | FAIL | 首步 chunk、执行 child 后准备完成；`lh_task_done(target_task=...)` 被拒绝。 |
| B08 | FAIL | 首步 chunk 并完成中间步骤；最终仍因带 target 的 `lh_task_done` 被拒绝。 |
| B09 | External PASS / Agent FAIL | chunk/reduce 后正确写出统计结果；随后完成调用携带 `target_task`，被协议拒绝。是假阴性。 |
| B10 | FAIL | 不必要的 chunk/replace 流程产生过一个 recovery；随后再次声明已有 chunk lane，触发 duplicate chunk lane，而非回到实际 producer 动作。 |
| B11 | FAIL | chunk 流程后调用 `lh_task_done(target_task=...)`；完成边界阻断。 |
| B12 | FAIL | chunk 后调用 `lh_task_done(task_id=T1)`；当前完成 schema 不接受任务引用。 |
| B13 | External PASS / Agent FAIL | 读写已得到正确配置；模型持续重复同一替换，第 6 次因旧字符串已不存在而任务失败。正确产物被重复动作链掩盖。 |
| B14 | FAIL | 进入 chunk/reduce 后尝试 `lh_replace_task`；输出 JSON 截断，且可见任务对象已有运行时字段回填倾向。 |
| B15 | FAIL | chunk 流程后以 `lh_task_done(target_task=...)` 结束，被协议拒绝。 |
| B16 | FAIL | 首步直接读文件方向合理，但生成 `read_file(end_line=...)`；文件工具 schema 不接受该分页参数。 |
| B17 | FAIL | chunk 后替换任务；模型把上下文运行态中的 `revision/task_id/workset` 等复制进新 task，被 proposal exact-key 拒绝。 |
| B18 | FAIL | 本应直接读写，却首步 `lh_chunk_map` 并在顶层携带 `task_id`，调用未执行。 |
| B19 | FAIL | 首步 chunk 偏置；顶层 `task_id` 与 call envelope 冲突。 |
| B20 | FAIL | 建立两个 chunk 并 reduce，但产物未达到本轮外部标准；最终 `lh_task_done(target_task=...)` 再次阻断。 |
| B21 | FAIL | 首步 `lh_chunk_map`；`task_id` 被放进 params，参数 schema 阻断。 |
| B22 | FAIL | chunk 后调用 `lh_replace_task`；replacement task 混入运行时字段，写入态 schema 拒绝。 |
| B23 | FAIL | 多 chunk/reduce 扩大了简单任务；随后 replacement task 回填 `task_id/revision/workset`，协议阻断。 |
| B24 | FAIL | chunk 后替换任务；运行时状态字段进入 proposal，exact-key 校验拒绝。 |
| B25 | FAIL | 首步误选 chunk，顶层 `task_id` 使其在执行前被阻断。 |
| B26 | External PASS / Agent FAIL | 3 次 `write_file` 已生成完全正确的目录树；之后 `list_directory(start_byte=...)` 使用未声明参数，被协议拒绝。是假阴性。 |
| B27 | FAIL | 首步 chunk 偏置，并把 `task_id` 嵌进 params，未执行工具。 |
| B28 | FAIL | chunk 后 `lh_task_done(task_id=T1)`；完成 schema 不接受显式当前任务引用。 |
| B29 | FAIL | chunk 后尝试 replace-task；JSON 截断，且任务提案与运行态字段边界混乱。 |
| B30 | External PASS / Agent FAIL | 首次代码和测试写入已经正确；随后 19 次重复替换；最终完成调用携带 source event/target task id，被空参数 schema 拒绝。是假阴性。 |

## 中等题逐题分析（30）

| 题目 | 结果 | 从起点到终点的错误链 |
| --- | --- | --- |
| M01 | FAIL | Goal 拆成 4 个任务；首个 Task 仍误选 `lh_chunk_map`，顶层 `task_id` 被拒绝。 |
| M02 | External PASS / Agent FAIL | 读取、修改并运行测试后产物正确；终点输出的 `lh_workset` 使用错误成员/状态结构，被状态协议拒绝。是假阴性。 |
| M03 | FAIL | 首步 chunk 偏置；params 中多出 `task_id`，0 次有效执行。 |
| M04 | FAIL | 建立 3 个 chunk 并 reduce；replace-task 时把 `revision` 等运行态字段写回 proposal，协议阻断。 |
| M05 | FAIL | 首步 `lh_chunk_map`，顶层 `task_id` 与 call-envelope 冲突。 |
| M06 | FAIL | 首步 chunk 且顶层带 `task_id`；即使继续，其 source 还包含 glob，说明没有先做 workspace observation。 |
| M07 | FAIL | 操作方向为 `read_json`，但参数容器写成 `parameters`；属于简单格式转换层遗漏的常见无语义别名。 |
| M08 | FAIL | 首步 chunk 偏置；顶层 `task_id` 被拒绝。 |
| M09 | FAIL | Goal 有 4 个任务；首个 Task 调用仍为 chunk，并因顶层 `task_id` 阻断。 |
| M10 | FAIL | 模型重复 `write_file`；用例注入的瞬时工具失败连续命中，恢复只重放同类动作，3 个 attempt 后失败，未形成有效纠错。 |
| M11 | FAIL | 生成 4 个 chunk 后 reduce；`lh_reduce_result` 返回结构不符合 schema，说明复杂分块状态进一步扩大协议面。 |
| M12 | FAIL | 首步 chunk，顶层 `task_id` 被 call-envelope 拒绝。 |
| M13 | FAIL | chunk 流程后 `lh_task_done(target_task=...)`，完成边界阻断。 |
| M14 | FAIL | 首步 chunk 偏置；顶层 `task_id` 被拒绝。 |
| M15 | FAIL | 首步 chunk 且顶层 `task_id` 被拒；其 source 还指向目录，若通过外层校验仍会在 source precondition 失败。 |
| M16 | FAIL | chunk 调用通过 envelope，但 source 指向不存在的 `primary/item_04.json`；未先观察真实 workspace。 |
| M17 | FAIL | 首步 chunk，顶层额外 `task_id` 被拒绝。 |
| M18 | FAIL | `lh_chunk_map` source 指向 `inputs/` 目录；chunk 接口要求文件，说明操作选择和 source 建立均发生在观察之前。 |
| M19 | FAIL | 首步 chunk；`task_id` 嵌入 params，被 exact-key 拒绝。 |
| M20 | FAIL | 首步 chunk，顶层 `task_id` 被拒绝；Round81 曾外部通过，本轮显示运行与接口选择不稳定。 |
| M21 | FAIL | chunk/reduce 后 replace-task；proposal 中带 `revision` 等运行时字段，被任务 schema 拒绝。 |
| M22 | FAIL | 首步 chunk，顶层 `task_id` 使调用无法进入执行层。 |
| M23 | FAIL | 连续 13 次读、30 次写，34 个有效 attempt；后期 artifact/check 一度正确，但模型继续选择相同写入，最终耗尽 attempt，且整体产物仍不完整。 |
| M24 | FAIL | 首步 chunk 偏置；顶层 `task_id` 被拒绝。 |
| M25 | FAIL | chunk 流程后输出 `lh_task_done(task_id=T1)`；完成 schema 阻断。 |
| M26 | FAIL | 首步 chunk，顶层 `task_id` 被拒绝。 |
| M27 | FAIL | 首步 chunk；params 中嵌套 `task_id`，操作 schema 阻断。 |
| M28 | FAIL | Goal 有 7 个任务，但首个 Task 仍误选 chunk；顶层 `task_id` 被拒绝。 |
| M29 | FAIL | 首步 chunk，顶层 `task_id` 被拒绝。 |
| M30 | External PASS / Agent FAIL | 多次写 JSON/运行 verifier 后 workspace 已正确；最后 `write_json` 使用绝对路径，被作用域协议拒绝。是假阴性，但路径约束本身应保留。 |

## 困难题逐题分析（H18 + LH12）

| 题目 | 结果 | 从起点到终点的错误链 |
| --- | --- | --- |
| H01 | FAIL | Goal 拆成 4 个任务；首步 chunk 且顶层 `task_id` 被拒绝。 |
| H02 | FAIL | Goal 生成 21 个任务，已过度展开；首步 chunk 又在 params 中携带 `task_id`，执行前阻断。 |
| H03 | FAIL | Goal 有 6 个任务；首步 chunk，顶层 `task_id` 冲突。 |
| H04 | FAIL | 几乎立即输出 `lh_task_done(task_id=T1)`，既没有产物证据，结构也不被完成 schema 接受；这是模型过早完成与协议冲突叠加。 |
| H05 | FAIL | Goal 过度拆成 29 个任务；首步 chunk 及顶层 `task_id` 被拒，长任务图放大上下文负担。 |
| H06 | FAIL | 选择 chunk 后 source 指向不存在的 `envs/staging.json`；缺少先观察再规划的闭环。 |
| H07 | FAIL | 首步 chunk，顶层 `task_id` 被拒绝。 |
| H08 | FAIL | chunk 后 `lh_task_done(target_task=...)`；完成协议阻断。 |
| H09 | FAIL | chunk source 指向不存在的 `data/primary.json`；任务尚未建立真实 workspace 证据。 |
| H10 | FAIL | 先列目录是合理观察；随后 `read_file(max_lines=...)` 使用文件接口未声明的分页名，被协议拒绝。 |
| H11 | FAIL | 执行多次写入和失败的验证命令；恢复继续围绕同一失败路径，8 个 attempt 后耗尽，未把 verifier 反馈转成 producer correction。 |
| H12 | FAIL | Goal 生成 16 个任务；首步 chunk，顶层 `task_id` 被拒。 |
| H13 | FAIL | `lh_chunk_map.instruction` 出现递归重复并超长截断；复杂 schema 与长指令生成触发输出稳定性失败。 |
| H14 | FAIL | 首步 chunk，顶层 `task_id` 被拒。 |
| H15 | FAIL | chunk 流程中的第二个 `lh_chunk_result` 结构错误；分块协议的中间状态面本身成为新失败源。 |
| H16 | FAIL | 使用 `function + parameters`，同时 chunk params 内还有 `task_id`；先命中纯格式别名遗漏，即使归一化后仍有语义参数边界错误。 |
| H17 | FAIL | 22 次模型调用持续读取不存在的 `ledger.json`，20 个 attempt 后耗尽；错误 observation 没有促使模型改变文件发现策略。 |
| H18 | FAIL | 先列目录，随后 `read_file(max_lines=...)`；与 H10 相同的分页参数接口不统一。 |
| LH01 | FAIL | 首步 chunk，顶层 `task_id` 被拒。 |
| LH02 | FAIL | 读取后连续 17 次重复写入；最终 `lh_task_done` 携带 source/target task id，被完成 schema 拒绝。 |
| LH03 | FAIL | Goal 阶段生成大量重复 `lh_tasks` 项并在约 17.5k 字符处截断；还未进入 Task lane 就因任务图递归膨胀失败。 |
| LH04 | FAIL | 首步 chunk，顶层 `task_id` 被拒。 |
| LH05 | FAIL | chunk source 指向不存在的 `shards/shard_07.json`；缺少真实文件发现证据。 |
| LH06 | FAIL | 模型回显带额外顶层 `payload` 的事件式对象；既不是单一调用 envelope，也不是可无语义归一化的常见别名。 |
| LH07 | FAIL | 首步 chunk；params 中嵌入 `task_id`，参数 schema 阻断。 |
| LH08 | FAIL | 使用 `function + parameters` 且 params 内有 `task_id`；纯格式错误与路由语义错误叠加。 |
| LH09 | FAIL | Goal task objective 递归重复 `return_*` 字段并截断；大任务图生成阶段失稳。 |
| LH10 | FAIL | 首步 chunk，顶层 `task_id` 被拒。 |
| LH11 | FAIL | 建立 8 个 chunk 后 reduce；reduce result 顶层多出 `return_type`，被 call-envelope 拒绝。 |
| LH12 | FAIL | 操作方向是 `read_file`，但使用 `parameters` 容器；属于纯格式转换层可安全覆盖的别名。 |

## 终点错误分类核对

85 题终止于 `model_protocol_blocked`，另 5 题终止于 attempt/task failure。协议阻断可核对为：

| 终点类别 | 数量 |
| --- | ---: |
| call envelope 多/错 key | 34 |
| `lh_task_done` 非空参数 | 16 |
| `lh_chunk_map` 参数多 `task_id` | 9 |
| replace-task proposal 混入运行态字段 | 6 |
| 截断/递归重复 JSON | 6 |
| chunk source 不存在或为目录 | 5 |
| 文件/JSON 工具参数不一致 | 5 |
| duplicate chunk lane | 1 |
| workset schema 错误 | 1 |
| chunk-result schema 错误 | 1 |
| reduce-result schema 错误 | 1 |
| 合计 | 85 |

剩余 5 题为 B13、M10、M23、H11、H17，均在执行/恢复循环中耗尽或任务失败。

## 下一步结构整改顺序

### P0：重新设计单次 Task 调用表面，不恢复旧 selector，也不保留全量 schema 平铺

目标仍是一次模型生成完成“选择操作 + 参数”，但先离线比较少量、固定候选接口：紧凑 action catalog 配合统一调用 envelope、判别式单工具 envelope、按任务态最小披露操作组。比较必须使用固定 90 题首个 Task observation、固定采样和预登记相似度，不能依据隐藏验收选择操作，也不能修改 RWKV 输出。

验收首先看正确操作/参数的原始生成比例，而不是 parser 接受率。当前证据已经否定“20 个完整 schema 全量平铺”作为默认结构。

### P0：让路由字段成为协议的一部分

明确 `task_id` 的唯一 wire 位置，并由 runtime 校验其等于活动任务。不能在格式转换层静默删除、移动或补全。这样覆盖 28 个顶层路由错误和 9 个嵌套路由错误的共同根因。

### P0：调整完成调用的真实 schema

让 `lh_task_done` 接受显式任务引用并严格核对活动任务，同时仍由既有 evidence/verifier 决定能否完成。它只解决“模型表达当前任务”的协议问题，不替模型生成验收证据，也不把失败改成成功。

### P1：加入稳定的 unchanged-observation 抑制

以 action、normalized params、workspace/artifact digest、effect/failure fingerprint 为依据；排除 attempt id、event id、时间戳。相同状态下不再次执行确定性无变化动作，返回一次结构化纠错观察并消耗 recovery budget。外部状态、时效性 verifier 和真实变化后必须重跑。

### P1：分离 Task runtime view 与 Task proposal schema

模型提交 replace/add task 时只展示并要求 `key/objective/after/done_when`；`task_id/revision/workset/status` 只存在于只读状态胶囊，且使用清晰不同的字段/区块，避免对象形状复制。

### P2：统一文件工具分页参数，收紧 chunk 的适用时机

为 `read_file`/`list_directory` 选择一个最小分页命名并由纯格式层只做已登记的同义字段转换；chunk 必须建立在已观察且存在的文件 source 上。不要通过规则替 RWKV 判断题目答案，只保证接口表达一致、前置条件可见。

### P2：降低 Goal/Task 大对象单次生成负担

对 LH03/LH09/H13 类递归重复，优先缩小投影视图、限制一次 task frontier 的结构复杂度并提供可重试的结构错误观察。不能从截断文本推断、补写任务或答案。

## 本轮可以保留与不能误判的改动

- 可以保留：原始/规范化 payload 审计；`function/name/tool` 与 `params/arguments/args` 的最小无语义别名转换；旧 selector 冲突已经被识别并移除这一事实。
- 应补充：`parameters` 作为参数容器的常见纯格式别名，仍需重复 alias、冲突字段、额外字段和审计回归。
- 不能误判：FP 为 0 并不代表完成门质量高，因为本轮 Agent 完成数也是 0。
- 不能误判：请求数下降不代表效率或质量提升；当前主要来源是过早协议阻断。
- 不能通过转换层处理：`task_id` 路由、completion target、错误 source、错误工具选择。这些都含语义，必须由明确协议或 RWKV 自己纠正。

## 证据索引

- 固定实验协议：`../Round85_FULL90_DIRECT_TASK_PROTOCOL.md`
- 汇总结果：`REPORT.md`、`results.json`
- 每题证据：`cases/<case-id>/model_trace.json`、`event_log.json`、`causal_ledger.json`、`audit.json`、`state_timeline.json.gz`
- 对照实验：`../../Round81_full90/`

