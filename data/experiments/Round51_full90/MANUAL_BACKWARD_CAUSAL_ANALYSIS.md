# Round51 E2E-90 逐题反向因果分析

本报告在完整运行结束后逐题检查冻结验收、最终工作区、动作结果、Task verifier、Goal evidence 和 RWKV 原始协议输出。隐藏验收和 Codex 参考答案未进入运行时。本报告不以聚合脚本替代判断；聚合只用于定位要人工展开的事件。

## 固定结果与结论

- Round46 已上传最佳：Strict `31/90`，External `32/90`，FP/FN `24/1`。
- Round50 两阶段候选：Strict `6/90`，External `11/90`，FP/FN `8/5`。
- Round51 两阶段 + 精确 `tool_name` 别名：Strict `17/90`，External `22/90`，FP/FN `22/5`。
- 分组：Basic `15/30`，Medium `1/30`，Hard `1/30`。
- `tool_name -> name` 透明转换实际发生 128 次、覆盖 51 题；raw/normalized payload 和 digest 全部可追溯。

因此，精确键名别名确实修复了真实接口损失，但两阶段结构整体仍不合格：它只保住 Round46 的 14 个 Strict case，同时新增 3 个 Strict case，净结果只有 17。原 Round46 的 31 个 Strict 中有 17 个退化。接通动作后又把大量安全阻断转成错误完成，FP 从 Round50 的 8 增到 22。候选不得替换或上传为最佳架构。

## 基础组逐题

- `B01` FN：`greeting.txt` 已精确生成；额外 T2 连续三次用 `read_json` 读取文本文件，JSONDecodeError 后仍不换 `read_file`，预算耗尽。首因是多余验证 Task 的工具选择，放大器是恢复不重选。
- `B02` Strict：`tool_name` 别名接通后，读取、派生 JSON、读回验证完整通过。
- `B03` Strict：别名接通后，读取、JSON 更新和验证完整通过。
- `B04` FP：目标副本内容被写成模型猜测的 `This is the source file content.`，不是源文件字节；manifest 正确。Task/Goal evidence 未比较 source 与 copy 的字节，错误完成。
- `B05` FN：删除 deprecated 行后的 `app.env` 完全正确；多余 T3 用 `read_json` 验证 env 文本三次失败。首因是验证工具错误，恢复重复同一错误。
- `B06` FN：`combined.txt` 字节完全正确；后续两个多余验证 Task 用 `read_json` 读文本并最终发明 `read_text`。Task 图把一个已满足目标拆成重复验证动作。
- `B07` FN：`endpoint.txt` 正确；最终“全部完成”Task 被强制执行 noop，verifier 又拒绝 noop 证据，修正调用使用 `input_parameters` 被格式层拒绝。首因是抽象完成 Task 被错误要求对应一个动作。
- `B08` Strict：四动作链和最终证据通过。
- `B09` safe fail：首动作把 CSV 当 JSON，恢复发明未注册 `read_text`。工具选择和恢复目录服从失败。
- `B10` safe fail：正确读取代码和测试后，写实现使用 `tool_name+input_parameters`；精确别名按预注册规则继续拒绝。语义参数完整但不属于本轮唯一格式变量。
- `B11` Strict：别名接通后读、写、验证完整通过。
- `B12` Strict：别名接通后读、计算、写、验证完整通过。
- `B13` Strict：别名接通后多 JSON 读取、更新、验证完整通过。
- `B14` safe fail：读取 left 后把 right 文本当 JSON，恢复仍读 JSON，最后发明 `read_text`。与 B09 同一工具/恢复缺陷。
- `B15` Strict：四动作链完整通过。
- `B16` safe fail：正确读取 env，写入参数使用 `input_parameters`，被精确 fail closed。
- `B17` FN：`active_users.json` 已完全正确；后续“排序”Task 强制新动作，RWKV 输出缺 arguments 的 noop。首因是已有 observation 不能直接满足后续 postcondition。
- `B18` Strict：Round50 的最终验证格式损失被别名修复。
- `B19` Strict：完整通过。
- `B20` safe fail：三次只读代码而未编辑；验证阶段又把 CSV/文本当 JSON，最终输出 `action+平铺参数`。首因是计划没有形成 edit action，格式是末端阻断。
- `B21` Strict：本次正确选择 read_file 读取 CSV，写入并验证通过；对比 Round50 的 read_json 循环，显示两阶段决策采样不稳定。
- `B22` FP：TASKS.md 写成普通 `- inspect`，遗漏 `[ ]`；Task/Goal evidence 未做完整字节验证。
- `B23` Strict：由 Round46/50 safe fail 恢复，多输入读取与 JSON 产物通过。
- `B24` FP：排序但未去重，保留两组重复行；证据只验证排序/文件存在，没有验证集合唯一性。
- `B25` Strict：完整通过。
- `B26` Strict：三个文件及读取验证通过。
- `B27` safe fail：只替换第一个 `protocol=v1`；验证发现另一个同名字段仍是 v1，但恢复只重复读取，不再执行 replace，预算耗尽。
- `B28` Strict：六动作链完整通过。
- `B29` Strict：本次使用 `copy_file` 保留源字节，修复了 Round50 的内容猜测。
- `B30` safe fail：读完代码/测试后从内部证据复制出错误的 `workspace/...`/绝对路径，且没有形成 edit；被 workspace-relative 边界正确拒绝。

## 中等组逐题

- `M01` Strict：列出三个服务、逐个读写与验证均通过；是中等组唯一 Strict。
- `M02` safe fail：读代码后连续把 Python 文件当 JSON，恢复不换工具，预算耗尽。
- `M03` safe fail：Goal proposal 首请求输出截断/无完整 JSON，run 尚未创建；传输/协议完成度问题。
- `M04` FP：release.json 正确，但把 JSON 文本写入 RELEASE.md；七个 Goal criterion 仍认证通过。Task 输出类型与完整格式 obligation 缺失。
- `M05` safe fail：正确读取 authoritative requirements 和两个不相关文件；对其中一个文本用 read_json，恢复发明 read_text。任务图没有把 authority 选择转成输出动作。
- `M06` FP：只复制 alpha，遗漏 gamma，manifest 也只含 alpha；集合 Task 由单 copy action提前完成，集合完备性没有证据。
- `M07` FP：resolved.json 完全幻觉成 Alice/age/city，未基于 defaults/override；Task/Goal evidence 接受与来源无关的产物。
- `M08` FP：输出顺序 `api,worker,web`，错误声称其为字母顺序；排序 verifier 判断错误且无确定性字节证据。
- `M09` safe fail：读完代码/测试后，运行命令先使用 `input` 容器，修正又仅输出裸 argv/cwd/env；两阶段调用名承接失败。
- `M10` safe fail：固定前三个副作用瞬态失败，系统重试同一动作三次便耗尽 lineage，未进入基准要求的 replan。
- `M11` FP：四个原服务未迁移，summary 使用未观察到的 billing/catalog/checkout 和 808x 端口；来源到输出逐项绑定缺失。
- `M12` safe fail：读完实现和测试，写动作分别混入 execution_capsule 或把参数平铺，均被 fail closed。
- `M13` safe fail：连续把 CSV 当 JSON，恢复发明 read_text。与 B09/M02 同类。
- `M14` FP：数据字段正确，但 changes 保持原逆序，Markdown 标题/日期格式也不符；Task verifier 把“写成功”当成完整语义成功。
- `M15` FP：index 路径错误地保留 `docs/` 前缀，a/c line_count 错为 1；只验证局部 total_files/bytes，不验证逐文件定位与计数。
- `M16` FP：没有生成 recovered.json，却完成了 run；读取 fallback/primary 的集合流程未形成最终聚合 artifact obligation。
- `M17` safe fail：列目录后直接尝试覆盖 web.json，第二阶段仅输出 path/value；同时遗漏其余 package 的读取与验证。
- `M18` safe fail：列出四个混合输入后把文本当 JSON，恢复发明 read_text；未建立“按媒体类型选择读取工具”的执行链。
- `M19` safe fail：读 log 后连续把纯文本当 JSON，恢复不重选。
- `M20` safe fail：把 Python 源码用 write_json 写成 JSON 字符串，command 失败；随后 verifier 把“已观察测试文件”误当修复完成，Goal replan 又输出非 canonical batch。多层共同产生。
- `M21` safe fail：产物接近正确且读回通过，但 Goal obligation 仍未解决，replan 输出非 canonical batch。此题需进一步把 criterion catalog 与实际 artifact obligations 对齐；本轮没有假完成。
- `M22` FP：没有生成 result.json；读完三个输入后以 noop 结束，Task/Goal evidence 错误完成。
- `M23` FP：只生成 dist/manifest.json，三个声明文件均缺失，且 manifest 顺序不符；集合 materialization obligation 缺失。
- `M24` safe fail：读完代码/测试后为 edit Task 选择 noop，修正使用 input_parameters；没有产生修改。
- `M25` safe fail：先尝试读取尚不存在的 CHANGELOG，再用 write_json 生成 Markdown 且输出平铺；计划角色与输出类型均错误。
- `M26` FP：valid records 正确，但 rejected 索引/原因和顶层字段名均错误；证据只抓住计数等局部字段。
- `M27` FP：拓扑顺序把 docs 放在 api 前；缺少确定性的 dependency-before-dependent 与 tie-break evidence。
- `M28` safe fail：凭空猜 `logs/2025-01-01.log`，重试后发明 read_dir；没有先列出实际文件名。
- `M29` safe fail：多次覆盖同一 JSON，missing_keys 最后写成包含 hello/save 的错误集合；最终 noop 验证被拒且修正格式失败。此题 safe blocked，但 artifact 仍错误。
- `M30` safe fail：读 config 后把 verification script 当作目标步骤，连续用 read_json 读取 Python/文本并耗尽预算；未形成配置写入动作。

## 困难组逐题

- `H01` safe fail：正确读取源码、测试和 CSV 后，Task T4 猜测不存在的 workspace manifest/绝对派生路径，没有进入代码写入。
- `H02` safe fail：首动作猜 `shard_0.json`（真实命名非该形式），恢复把策略词 `reselect_action` 当工具名。缺先列目录与 recovery 协议隔离。
- `H03` safe fail：逐阶段写到第 5 层，stage6 写调用先用 input_args、再省略 name；长链在跨消息承接处终止。
- `H04` Strict：唯一 hard Strict；不可信输入处理保持约束，产物通过。
- `H05` safe fail：列出 50 文件后未逐个读取，直接写猜测的 Priority 映射；第三次写又用 action+平铺参数。集合 cardinality 是首因。
- `H06` FP：三个环境迁移内容正确，但 report 字段写成 `migrated_environments`，要求 `migrated`；完整形状 obligation 未守住。
- `H07` safe fail：一个 Task 要同时读代码和测试；单次 read_file 后 verifier 要求第二文件，恢复却改用 read_json，重复失败。Task/action cardinality + recovery。
- `H08` FP：ledger 写成按 id 排序的 `{events:[{id,count}]}`，不是 first-seen ids+count；证据没有验证 exact schema/order/resume。
- `H09` safe fail：backup 已成功读取，但 T1 固定 postcondition 仍要求 primary；fallback 分支没有条件 Task 状态，恢复在两个路径间循环。
- `H10` safe fail：已生成接近目标的两个输出，真实 verifier 返回 exit 1；下一工具名选择带非空 arguments，被第一阶段正确拒绝。更早的 item schema/报告内容错误才是根因。
- `H11` FP：只读输入/代码，没有修改 pipeline.py 或生成 release.json；run 仍完成。真实 verifier/目标 artifact 未成为必须证据。
- `H12` FP：aggregate 只统计 shard_01 两项，却宣称覆盖 15 shards；集合完备性严重缺失。
- `H13` safe fail：六个 Task 都反复取得同一前四项 listing page，未使用 next_cursor；verifier前五次把重复页算作不同 batch，第六次才拒绝。游标没有从 observation 强绑定到下一 action。
- `H14` safe fail：只读部分 manifest 就写 index，且错误声称 north/south/east 是字母序；最终验证用 noop 被拒。既有覆盖不足也有 verifier 错判。
- `H15` safe fail：未 inspect 现有代码/测试便生成 parser，随后 analyzer 使用错误工具/裸 path-value；Goal/plan 缺 inspect-before-edit。
- `H16` safe fail：只读两个 config 中一个后，经恢复读到另一个；尚未 apply changes 就进入 Goal replan，输出非 canonical batch。多文件 Task 与 mutation obligation错位。
- `H17` FP：ledger 是按 id 聚合的数组，A amount 被累加为 8，要求 first-seen unique entry amount 4 和顶层 count/total；恢复/中断 evidence 没有验证 exact shape。
- `H18` safe fail：读完输入与 verifier 后先尝试读取尚不存在的 release 产物，再建目录，再重复读取缺失文件；没有形成 producer action。
- `LH01` FP：列出/读取后未修改 project/pipeline.py、未生成 release artifact，却完成。分层 verifier 没有真实运行并作为 completion gate。
- `LH02` safe fail：15 checkpoints 正确，final/config 仍错误沿用 `{step,constraints}` 外壳；本轮 Goal replan 检出未满足但输出非 canonical batch。比 Round50 FP 更安全，但根因仍是跨阶段形状复制。
- `LH03` safe fail：反复读取 root manifest，把“得到子 manifest 路径”误认证成“已读所有子 manifest”；随后写部分 index，下一写使用 action+平铺参数。计划 cardinality 和 verifier 都放大遗漏。
- `LH04` safe fail：写入一个单 event 后，多个验证 Task 反复读同一个对象，count/ledger schema始终缺失，recovery重复同一读取直到预算耗尽。
- `LH05` safe fail：列出 20 shards/fallback 后只读 shard01；另一 Task 把规则 Markdown 当 JSON反复失败。集合读取和规则文件类型选择均错误。
- `LH06` safe fail：三个 requirement 文件真实位于更深目录，计划直接猜根路径；恢复最后从环境证据复制绝对路径，被 scope边界拒绝。应先 list，不应放宽路径安全。
- `LH07` safe fail：列出 8 services 后把下一 Task 指向非 JSON内容/错误文件，且先验证不存在的 migration_report；恢复重复失败，没有形成逐服务 migration。
- `LH08` safe fail：Task 声称“读三个 configs”，实际只读 b.json就 pass；其余 Task只读 change/policy/checker/listing，未执行任何 config mutation，Goal replan 非 canonical。
- `LH09` safe fail：把 Markdown API workflow 当 read_json，修正输出 action+平铺参数；没有进入 mock_api 链。
- `LH10` FP：math_ops.py 本身正确、测试通过，但 README 仍描述 add/multiply 且作为 JSON字符串写入；manifest 两个文件被填成同一猜测 digest。局部 test success 被错误放大为完整 Goal 完成。
- `LH11` safe fail：15 次读取都猜错 artifact 分片路径（001、010、025-032 等），没有先做可靠 listing/使用真实文件名；多个并行 Task各自耗尽预算。
- `LH12` safe fail：把 DESIGN.md/README.md 用 write_json 写成 JSON字符串，parser/analyzer/reporter未实现；实现 Task选择 noop并在修正阶段使用 input_args。

## 跨题结构归因

1. **两阶段选择不是当前最佳结构。** 它在接口接通后仍让 Round46 的 17 个 Strict 退化；新增一次 RWKV name-only 决策带来工具目录幻觉、非空 arguments、抽象策略词当工具和运行间不稳定。
2. **Task/action 强制一一对应是最高频基层缺陷。** “排序、计数、验证、全部完成、读一组文件”经常已由依赖 observation 满足，或需要多个动作；系统却强制一个新 action，制造 read_json/noop/虚构工具。
3. **恢复没有改变失败变量。** JSONDecodeError 后仍 read_json，not_found 后仍相同猜测路径，verifier replan 后仍读相同文件；recovery budget 只是重复次数上限。
4. **集合完备性没有一等状态。** M06/H05/H12/H13/LH03/LH05 等把一个文件/一页结果当全体，随后 Goal evidence无法发现缺项。
5. **完成证据只验证局部效果。** “写成功”“字段等于自身期望”“文件存在”被用于证明完整目标，导致 exact schema、排序、去重、逐源对应、真实 command verifier 被遗漏。
6. **格式层应保持窄。** `tool_name` 精确别名有效，但 input_args/input_parameters/裸参数/action+平铺等不能在没有独立预注册和冲突测试时一起放宽，更不能由格式层补语义。

## 下一步指导

按预注册协议先回退 Round50/51 候选代码，恢复已上传 Round46。下一项不应继续扩展格式，而应先修复 **Task 的可满足性模型**：允许一个 Task 在产生新 action 前，由 RWKV 对现有依赖 observation 判断 postcondition 是否已经满足；对集合/多文件 Task 则必须显式拆成可观察 cardinality 的子任务或返回结构化 continuation，而不是用 controller 推断答案。该结构必须保持 RWKV 决策权，不由规则选择工具、参数或最终答案。
