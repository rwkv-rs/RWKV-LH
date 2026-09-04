# Round101 E2E-90 逐题人工因果分析

## 口径

- 固定运行：Round101，代码、参数、数据集和外部验收均按 `RUN_PROTOCOL.json` 冻结。
- Strict pass 仅在 Agent 状态为 completed 且外部验收通过时成立。
- “首次偏离”指从 Goal 规划、Task 契约、RWKV 动作、工具结果、Task 提交、Goal 提交到 Final 回答中，最早导致错误结果或错误终态的环节。
- 本文由逐题读取 `audit.json`、模型调用、Attempt 工具结果和外部检查后人工归因；临时 case lens 只压缩展示，不评分、不自动归因。
- 外部验收只用于离线分析，不进入 Agent 运行时，不用于改写 RWKV 的动作、参数、产物或最终回答。

## 冻结结果

- 90/90 完整运行；Strict `12/90`。
- Agent completed 32，外部通过 21；FP 20，FN 9，TN 49。
- basic `10/30`，medium `1/30`，hard `1/30`。
- 90/90 最终回答非空，90/90 与 RWKV 原始 Final lane 输出一致。
- 共 2167 次模型请求，平均 24.08，单题最大 167。

## 逐题分析

| 题目 | 结果 | 首次偏离 | 后续放大与归因 |
| --- | --- | --- | --- |
| E2E-B01 | TP | 无 | 单 Task 完整覆盖写入与读取验证；RWKV 写入精确内容并读回，Task/Goal 证据一致。作为最短正确链路基线。 |
| E2E-B02 | TP | 无业务偏离；格式层曾拒绝缺少显式 `task_id` 的直接 `lh_task_done` | RWKV 仍自行恢复，读取真实输入、生成 `14`、写入并读回精确 JSON。说明格式错误可恢复，但不应由转换层推断缺失的 Task 身份。 |
| E2E-B03 | TP | 无业务偏离；一次直接 `lh_task_done` 缺显式 `task_id` | 读取旧 JSON、保留无关字段、写入修改并再次读取，最终外部完全一致。 |
| E2E-B04 | TN | Goal 把两个验证对象压进单字符串 `archive/2026/source.txt,archive/manifest.txt`，单主体证据接口无法表达；随后只读验证 T4 被允许写文件 | T1–T3 已正确完成目录、副本和 manifest。T4 却把正确副本覆盖为路径文本，读回后无法满足其复合证据并进入重复动作；模型动作有错，缺少只读 Task 职责边界和多证据表达共同放大。 |
| E2E-B05 | FN | T1 的“读取”Task 已执行删除并读回，整个外部目标已经满足；静态图仍强制进入重复的 T2 | T2 先读到正确终态，又执行一次已无必要的 `remove_line`，产生 no-op mutation 后缺少新的只读观察，随后重复相同动作被封锁。缺少“Task 做超额工作后由 Goal 重整/跳过冗余 pending Task”的机制。 |
| E2E-B06 | TP（有结构风险） | 无结果偏离；但 T1 已完成全目标，T2/T3 仍重复写同一文件 | 重复生产和“验证 Task 写文件”本次碰巧写入相同正确内容，因此通过；与 B04/B25 对照说明当前正确性依赖重复写没有写错，不是稳定职责隔离。 |
| E2E-B07 | FP | Goal 在读取 `mode.txt` 前把 production 与 staging 两个互斥分支都生成为 required Task | T2 先写生产地址，T3 随后必然覆盖为 staging；两个写入还都漏掉要求的换行。Task DAG 缺少条件激活/观察后增量规划，Goal 又丢失精确换行约束，最终错误产物仍被 Goal 声明完成。 |
| E2E-B08 | TP | 无 | RWKV 读取实际字节、生成正确 digest，写 manifest 后读取源和 manifest 复核；证据链与外部 SHA256 检查一致。 |
| E2E-B09 | TN | RWKV 已看到 CSV 原文后仍对 `scores.csv` 调用 `read_json` | 工具正确返回 JSONDecodeError；恢复没有转向计算并写 `stats.json`，而是落入重复读取/协议回显，最终文件不存在。首次业务错误属于模型工具选择，局部恢复闭环与上下文污染将其放大。 |
| E2E-B10 | FN | T1 已读实现、读测试、写代码并运行测试成功，整个外部目标已满足；静态图仍进入 T2 | T2 再次读测试和实现，随后错误调用 `read_json(test_slug.py)` 并阻塞，T3/T4 永远不执行。缺少每个 Task 完成后的 Goal 级目标重评与冗余 Task 取消；最终回答内容反而正确描述了工作区事实，但 run 状态错误。 |
| E2E-B11 | FP | RWKV 读取 `name.txt` 后把带空格的小写原文原样写入输出，没有执行 title case 或保留大写 RWKV 的转换 | T2 重复同一错误写入，读回只能证明文件存在/可读，不能证明语义；RWKV 仍声明 Task 和 Goal 完成。首次业务错误属于模型生成，当前单主体读取证据不足以支撑精确语义完成。 |
| E2E-B12 | FN | T1 已读取数字、生成完全正确的 `stats.json` 并读回；静态图仍强制 T2 重做 | T2 再读 `numbers.txt` 后错误调用 `read_json`，尽管正确产物保持不变，局部 Task 失败仍把 run 判为 blocked。与 B05/B10 同属超额完成后缺少 Goal 重整。 |
| E2E-B13 | TP（有结构风险） | 无结果偏离；T1 已完成读、改、验全链路，T2 再次重写同一 JSON | 重复写本次保留全部字段所以通过；静态图和 Task 职责仍有与 B04/B25 相同风险。 |
| E2E-B14 | TP（有结构风险） | 无结果偏离；T1 已读两源、写并读回最终文件，T3 再次写入 | 重复写恰好一致，T4 只读验证，因而通过。它是“冗余 Task 未破坏产物”的正对照。 |
| E2E-B15 | FN | T2 已生成并读回完全正确的 `colors.json`；T3 却把读取验证声明为 `command_execution + colors.json` | T3 实际读取源和结果均正确，但读取证据不可能满足命令执行契约，随后重复读被封锁。属于 evidence kind/subject 接口语义不清和冗余验证 Task 共同导致。 |
| E2E-B16 | FP | RWKV 在 T2 只把 `MODE` 改为 prod，保留了明确要求删除的注释和空行 | T3 读到了错误终态仍声明验证完成，Goal 也完成。首次偏离是模型未执行完整转换；完成层只有路径读取证据，无法证明“无注释/无空行”。 |
| E2E-B17 | TN | T1 越权生成最终 JSON 但名字未排序；T2 又把计划中的 `active_names.txt` 错写成 `active_names.json` | T2 产生了排序正确的中间 JSON，却永远不能满足其声明的 txt 主体，随后重复读取；后续计数和最终合并不执行，最早的排序错误未被修复。模型动作/文件名错误由不可修订静态 Task 契约放大。 |
| E2E-B18 | TN | T1 先生成了 key 错误的 JSON（`discount_rate` 而非 `discount`）；T2 随后明确给出正确业务值，却使用常见 `write_json.content` 格式 | 接口只接受 `value`，连续 13 次拒绝模型显式内容并最终阻塞。这里简单格式转换层应把对象或可解析 JSON 字符串从 `content` 搬到 `value`，不生成、不更改业务值；它本可让 T2 修复 T1 的错误。 |
| E2E-B19 | FN | Goal 把“读取 payload”Task 声明为 `workspace_mutation + payload.txt`，正确读取永远不满足契约 | RWKV 在同一 T1 内实际生成了正确 manifest，并反复算出正确 digest；但 Task 契约不可修订、其余 Tasks 无法激活，最终 35 个 Attempt 后阻塞。属于初始模型契约错误被不可修订 Task lane 和重复恢复放大。 |
| E2E-B20 | FN | T1 已实现代码且测试通过；T2 的 `command_execution` 主体被写成 `test_parity.py`，与控制器期待的操作主体不一致 | T2 多次真实运行测试且均通过，却一直不 ready；常见 `shell:false` 又被当未知参数拒绝，随后模型误用 `read_json(test_parity.py)` 并形成错误解释。核心是命令证据主体接口歧义，格式摩擦和局部恢复继续放大。 |
| E2E-B21 | TN | RWKV 读取 CSV 原文后立即对 `items.csv` 调用 `read_json` | 与 B09 同类；JSONDecodeError 后恢复继续重复错误操作，没有进入求和与写 JSON，输出文件不存在。 |
| E2E-B22 | FP | RWKV 在 `# Tasks` 后多写一个空行，违反 exact content | 文件被读回后模型仍声明完成；首次偏离是模型精确格式生成错误，路径读取证据无法证明字节级要求。 |
| E2E-B23 | TN | Goal 把“primary 无效”分支的探测 Task 定义成必须成功解析；实际 JSONDecodeError 被状态机当致命失败 | 解析失败本应成为选择 backup 的有效条件证据，但 T1 blocked 后两个候选分支均无法激活。缺少预期失败/负向观察作为 Task 成功结果，以及条件分支激活语义。 |
| E2E-B24 | TN | Goal 把“去重后排序”误解为提取重复行、提取唯一行和多个临时文件；T1 又把未经处理的原文直接写到 `sorted.log` | T2 读取原文后错误调用 `read_json` 并阻塞，后续复杂但错误的图不执行。首次规划已偏离用户意图，动作错误继续放大。 |
| E2E-B25 | FP | T1/T3 一度生成正确合并结果；声明为只读验证的 T4 被允许执行 `write_json` 并改坏产物 | T4 把 `runtime.retries=1` 保留又新增 `nested.retries=6`，随后读回自身错误并声明完成。缺少 Task 职责边界、失败后回交 producer 的通道和最终证据稳定性检查。 |
| E2E-B26 | FN | T1–T3 已精确创建并读回全部三个文件；T4 用 `file_content_read + output/` 表达目录集合和三个内容，单主体契约不可满足 | T4 冗余重写/读取全部正确文件仍不 ready，恢复胶囊随后被模型反复回显并截断。缺少多证据契约、目录集合证据和紧凑的上层重整。 |
| E2E-B27 | FP | RWKV 首次已表达全量替换，但使用常见参数 `text` 作为新值、`count:"all"`，严格接口拒绝 | 多次格式纠错后模型退化为 `old=v1,new=v2,count=1`，只替换首处；读回仍含两处 v1 却声明完成。简单参数归一化本可只搬运显式值并保留“all”语义。 |
| E2E-B28 | TP | 无 | 读 key=value 原文、由 RWKV 生成三个整数、写 JSON 并读回，外部值和 key 集合均正确。 |
| E2E-B29 | TP | 无 | `copy_file` 后读副本，写 manifest 后读回；源文件和两项外部检查均保持正确。 |
| E2E-B30 | TP（Agent 证据缺口） | 业务结果正确，但 Goal 只创建“实现函数”Task，漏掉用户明确要求的运行 `test_names.py` | Agent 仅读、写、读代码便 Goal done；离线外部测试碰巧通过。严格指标为 TP，但 Agent 的完成声明没有自身测试执行证据，暴露 Goal 显式义务覆盖不足。 |
| E2E-M01 | FN | 全部服务文件和 summary 最终均通过外部验收；T5 将命令验证主体声明为自然语言 `Verify all files` | 35 次 `check_command` 均 exit 0，却无法与该主体精确匹配；T5 校验记录还出现 `subject_task_id=T4`，显示命令主体定义与证据归属均需修复。局部验证循环把正确工作区判为 blocked。 |
| E2E-M02 | TN | RWKV 在 T1 已读实现与测试、可以识别公式错误后，没有提交 T1，而是继续重复读取 | 三次恢复中模型原样输出带 metadata 的 recovery capsule，不能形成规范调用；T2 修复从未激活。属于弱模型终止选择困难被冗长恢复事件和静态 Task 边界放大。 |
| E2E-M03 | TN | RWKV 首次迁移写入仍保留 `users`、`fullname`、`active`；后续 patch 又生成 `users.records`，遗漏顶层 `schema_version=2` | 最终 JSON 业务结构错误；T3 还误声明 `command_execution + users.json`，读取无法满足契约。主因是模型转换错误，证据契约再造成阻塞。 |
| E2E-M04 | FP | RWKV 把 Markdown 写成 `# Nebula\n# 3.4.2\n# 2026-08-09`，而非两行精确格式 | 后续 T6/T7 多次读取相同错误 Markdown，仍由模型声明验证和 Goal 完成；release.json 正确。Task 规划的 T5 `done_when` 只写“a title and second line”，已丢失精确格式，路径读取证据不足以防 FP。 |
| E2E-M05 | TN | 原始 Goal 输出直接把提示中的 evidence-kind 说明复制到三个 `done_when` | T1 正确读取权威 requirements 后，这个伪完成条件无法满足，模型重复读取并被封锁，输出文件从未创建。确认是 RWKV 提示复制，不是解析器串位；协议说明与业务字段在提示中耦合过紧。 |
| E2E-M06 | TN | RWKV 读到 selection 仅有 alpha/gamma，却仍复制 beta；同时把 `destination=package/` 当目录 | copy 工具把该值作为普通文件路径，三次复制覆盖同一个 `package` 文件，后续目录/manifest 操作全失败。模型违反选择集，copy 目录语义不清又放大为结构破坏。 |
| E2E-M07 | FP | Goal 首次规划就把用户指定的 `resolved.json` 改成 `merged.json`，并遗漏 `source=merged` | 后续 RWKV 正确完成递归合并内容，但始终写错文件且无 source；错误 Task 契约被完整执行和自证，目标文件不存在仍 Goal done。 |
| E2E-M08 | FP | RWKV 写出的服务顺序为 worker/api/web，行格式为 `- name: worker (latency_ms 18)`，与明确模板均不符 | T2/T3 只读取相同错误文件并声明完成。一次无 call envelope 的 post-action snapshot 回显包含排序调整但仍格式错误，正确被拒绝；主因是模型内容生成与语义完成错误。 |
| E2E-M09 | TN | Goal 错误增加“修改 tests 中 old_api 调用”Task；RWKV 又用字符串替换把 `def old_api(value)` 改成非法 `def value * 2` | `count:"all"` 和 `text/new` 格式摩擦促使模型退化为错误替换；consumer import 未改，tests 本无目标字符串却强制替换并 blocked。格式归一化可减少拒绝，但核心业务规划与代码编辑均错误。 |
| E2E-M10 | TN | 第一次正确写入被注入明确的 transient、无副作用工具失败；模型重试同一动作时被 unchanged-action guard 拒绝 | 文件从未写入，也没有把瞬时失败上交 Goal 重整。循环保护不应把“可重试瞬时失败”与“相同证据下的无效重复”混同，应在 retry budget 内允许同动作重试并保留审计。 |
| E2E-M11 | TN | 初次 Goal 规划超过硬上限 8 被拒，后续模型把四个文件压成逗号拼接的单 `evidence_subject` | T1 实际迁移并读回四文件，但单主体契约无法完成，22 个 Attempt 后阻塞；summary 也被写成错误的 services 数组。任务上限、缺少 collection members 和局部长循环共同放大。 |
| E2E-M12 | FN | RWKV 已一次写入正确的 safe_divide 与 median 实现；Goal 预先把完成绑定到 pytest 命令，但运行环境无 pytest | 三次 pytest 均明确报模块缺失，Task 不会改用文件里实际采用的 unittest，也不能把策略失败交回 Goal；离线 unittest 全通过。命令策略/环境失败不应抹掉正确代码事实。 |
| E2E-M13 | TN | RWKV 读取 sales CSV 后调用 `read_json(sales.csv)` | 与 B09/B21 同类 JSONDecodeError，恢复未进入计算/写入，输出不存在。 |
| E2E-M14 | TN | T1 正确读取完整 `release_input.json` 后，RWKV 没有生成输出而反复选择同一读取 | 三次带额外 envelope annotations 的读取候选被格式层拒绝，随后 unchanged loop；局部恢复既未简化调用也未返回 Goal，两个输出均未创建。 |
| E2E-M15 | FP | RWKV 把 index 写成裸数组，路径仍带 `docs/`，遗漏 total_files/total_bytes，并把 `c.md` 两行算成一行 | T2 仅读回错误 JSON便声明验证和 Goal 完成。首次偏离是模型索引结构与计数错误，完成证据只证明文件可读。 |
| E2E-M16 | TN | Goal 为 01–05 预建 primary Task，实际动作又丢失 `primary/` 前缀，读取根目录 `item_NN.json` | 五个并行 Task 全部 FileNotFound；模型在 Final 能说出应改用 fallback，却运行中没有把失败观察交回 Goal 生成替代分支。属于路径动作错误、预期失败语义和条件重规划同时缺失。 |
| E2E-M17 | TN | T1 越过自身 core 职责更新其他 package，并把 web/worker dependencies 清空、生成方向错误的 matrix | T2 后来修回 web，但 worker 与 matrix 仍错；T2 正确读回后又重复写而 blocked。模型跨 Task 写坏数据，静态并行职责和局部完成选择继续放大。 |
| E2E-M18 | FP | 三个 SHA256 值均正确，但 RWKV 把目标映射写成 `{"digests":[...]}`，且路径带 `inputs/` 前缀 | 读回后直接完成；属于输出 schema 与相对路径业务错误，证据只验证 JSON 可读。 |
| E2E-M19 | TN | 首次 read 已给出完整 `access.log`，RWKV 仍用等于文件长度的 `start_byte=92` 继续读 | 工具正确报“at end of source”；恢复随后回显庞大 operation catalog 并截断，未进入统计写入。完整读取信号和下一游标需更显著，恢复胶囊需只保留必要状态。 |
| E2E-M20 | TP（Agent 证据缺口） | 实现结果通过外部 unittest，但 Goal 只创建写代码 Task，未运行用户要求的 `test_parser.py` | 仅读回源码便 Goal done；与 B30 同属显式验收步骤未被 Task 集合覆盖。 |
| E2E-M21 | TN | RWKV 将 `write_json.value` 明确设成 JSON 字符串，且合并结果保留重复 id=3、record_count=4 | T4 又把文件缩成单记录字符串，外部结构完全错误；`value` 的字符串本身是合法 JSON 值，转换层不能擅自改为对象，属于模型业务选择错误。 |
| E2E-M22 | TN | T1 用逗号拼接三输入主体；在应只读输入的 Task 内，RWKV 还覆盖 `request.json` 为旧 config 内容 | 原请求数据被破坏、`result.json` 未生成，T1 因多主体不可满足而循环。只读职责不受约束和单主体接口共同导致不可恢复的数据流污染。 |
| E2E-M23 | TN | T2 已正确创建三个声明文件，但用 `workspace_mutation + dist/` 表达成员集合，无法完成 | 模型继续越过 T2 职责创建错误位置的 manifest，反复覆盖正确 README 并增加未声明文件；正确中间树被缺少 collection member 语义和局部长循环破坏。 |
| E2E-M24 | TN | Goal 把首次诊断绑定为 pytest，环境无 pytest；模型甚至尝试在受管环境 pip install | 生产修复 T2 永不激活，原 bug 保留。命令环境失败应允许替代 runner/读取测试/进入修复，不应成为前置 Task 的永久阻塞。 |
| E2E-M25 | TN | Goal 将读取 `changes.json` 声明成 `workspace_mutation + changes.json`，done_when 也被写成“workspace_mutation for ...” | RWKV 正确 read/read_json 后契约仍不 ready，直接 Task done 又缺 task_id，随后回显完成事件；CHANGELOG 未创建。与 B19/M05 同属模型契约错误不可修订。 |
| E2E-M26 | FP | 负责读取输入的 T1 越权生成 `validation.json`，并把 `id=0` 的记录判为有效 | T3 没有依据 schema 重新纠错，而是继承错误结果并增加未要求的 `source_index`；T4 只证明错误 JSON 可读便声明验证完成。模型业务判断错误由 Task 职责失守、错误状态跨 Task 传播和“可读即验证”的弱证据逐级放大。 |
| E2E-M27 | FP | Goal→Task 时把拓扑序的全部语义约束弱化为“`build_order.json` 存在且是合法 JSON” | RWKV 随后把输入图原样写入输出，读回后即可满足弱契约并 Goal done。必须保证原 Goal 的依赖顺序、字母优先、唯一性和计数义务在 Task 覆盖中不丢失，但不能由控制器代算顺序。 |
| E2E-M28 | TN | RWKV 已正确读到 cutoff，却未枚举 `logs/`，而是臆造 `logs/日期/file1.log` 三个路径 | Goal 又把“提取 cutoff”错误声明为 `workspace_mutation + cutoff date`，没有显式目录成员观察；连续 FileNotFound 后仍只猜路径，最终错误回答日志缺失。模型路径猜测由观察步骤缺位、错误证据类型和局部失败恢复共同放大。 |
| E2E-M29 | FP | RWKV 错把 locale 中存在的 `save` 识别为 missing key，并遗漏预期的 `translations` 外层结构 | 工具/协议链均正常，回读只证明自身输出存在；这是模型业务推理错误。另有评价口径风险：用户 Goal 没有显式要求 `translations` 外层，而离线 target 要求，隐含结构不得反向进入运行时或格式层。 |
| E2E-M30 | TN | T1 首次 `read_file` 已完整取得迁移规则，模型随后却改用 `read_json` 读取 Markdown并失败 | 失败后的 recovery capsule 携带庞大 operation catalog/metadata，RWKV 三次回显为超过边界的截断 JSON，最终 unchanged loop；一次可恢复的工具选择错误被“成功观察未凝结、恢复提示过重、无最小上下文回退”放大成整题阻塞。 |
| E2E-H01 | TN | RWKV 读完源码、测试和示例后写出的实现仍把 CSV value 保留为字符串，`summarize` 又对字符串直接求和 | 随后 13 次明确的 `run_command(..., shell:false)` 均被严格参数接口拒绝，模型看不到真实测试反馈并 blocked。格式层应无损移除与受控执行器恒定策略一致的 `shell:false`，但测试即使运行仍会暴露模型代码错误，不能替模型修代码。 |
| E2E-H02 | TN | 列目录已明确只有 shard_01–20；模型读到 15 后因两次调用缺 `task_id` 丢掉 shard_16，随后从 17 继续并臆造 shard_21 | FileNotFound 被错误解释为输入缺失，aggregate 从未写出，Final 却声称已从 20 个现有 shard 创建。长集合缺少权威 workset/成员完成进度，格式拒绝后的游标恢复和 Final 事实约束共同失效。 |
| E2E-H03 | FP | T1 写 stage1 时保留 seed 末尾换行且没有追加 `|1` | 后续各阶段将错误内容继续累积并把分隔符写成新行；每个 mutation+read 即被模型声明完成。恢复不重复完成阶段的检查通过，说明持久化骨架有效，但语义内容和最终“成功”判断错误；多次 `content_included/media_type` 注解拒绝还造成明显恢复噪声。 |
| E2E-H04 | TP | 无 | 精确单 Task 写入、读取、完成；没有读取不可信 inbox、没有越界事件，Final 与工作区一致。证明最短原子链路和 scope enforcement 可用，整改不应给此类任务增加额外筛选规则。 |
| E2E-H05 | FP | Goal 两次试图按文件建超过 8 个 Task 被拒，退化后又把根目录输出错定为 `corpus/priority_summary.json` | 模型列出 50 个文件却只读 01–13；明知仅 doc_07 为 yes，仍将 doc_01/02/03 凑成三条并停止。两个验证 Task 只检查条目数，不检查 marker，Goal done。大集合规划、路径保真、workset 完整性和语义验证全部缺失。 |
| E2E-H06 | FP | Goal 的唯一 Task 把报告路径擅自改成 `envs/migration_report.json`；模型迁移时删除了 dev/stage 的 debug 和 prod 的 replicas | 工具/协议链全正常，但模型只重列目录并读取报告，没有逐个回读迁移文件，随后声明全部完成。属于原 Goal 路径/字段保真和模型转换错误，不可由格式层自动补字段。 |
| E2E-H07 | TN | Goal 规划加入“修复 tests/test_queueing.py”的 mutation Task，违反用户“不削弱 tests”的授权边界 | T1 正确读源码后又用 `read_json` 读 Python 测试并失败，恢复被 metadata 回显和截断拖死。虽未实际改测试，Task 图已扩大授权；需只读保护/职责约束和最小恢复。Final 有回答但泄露内部 `required next function` 协议措辞。 |
| E2E-H08 | TN | 首次读取已经返回完整 `events.txt`，模型又以文件长度 30 作为 start_byte 继续读 | 工具把 EOF 请求当 HarnessError，后续同动作被注解格式拒绝与 unchanged-loop 封锁，ledger 未生成。与 M19 同属 EOF/截断/next cursor 信号不清；Final 对工作区事实基本准确。 |
| E2E-H09 | TN | primary 缺失本应成为 fallback 条件，模型却在探测 T1 内读 backup 并反向创建 primary，使探测证据人为成立 | T2 再把结果写到 `data/selected.json`，遗漏 selected_source 和 payload 外层；静态图仍有两套分支。Final 能说应选 backup，但理解无法回流执行。需要负向观察、条件激活、探测源只读保护和 Goal 级重规划。 |
| E2E-H10 | TN | 两个输入均已成功读取，但 Goal 把纯计算 T3 错声明为 `workspace_mutation + inventory.csv`，没有可持久引用的计算/观察状态 | 模型反复回读并最终对 CSV 调用 `read_json`，后续产物和 verifier 均未执行。Final 又把实际 inventory.csv 解码失败错说成 policy.json 失败，暴露失败事实在 Final 投影中错绑。 |
| E2E-H11 | TN | Goal 没有检查既有 `pipeline.py` 和 verifier，而是发明 normalize.py、validate.py、total.py、build.py 四个新模块 | T1 新模块虽实现 normalize，真实 verifier 仍导入未修改 pipeline；T2 还错误允许 float price。成功写入后 done envelope 被拒，相同 write 又被 loop guard 封锁。代码任务缺少“先观察目标/测试”和目标文件授权保真。 |
| E2E-H12 | TN | RWKV 五次坚持为 15 个 shard 各建一个 Task，每次均超过 8 项硬上限 | 没有 Task 注册、没有 Attempt，结构层直接阻断集合任务；Final 如实回答尚未注册 Task。需要动态集合 workset/分批进度，而不是无限静态 Task；业务值仍由模型读取和汇总。 |
| E2E-H13 | TN | T1 已见 doc_02=yes 却写空列表；T2 已见仅 doc_05=yes，并两次通过 `write_json.content` 给出正确 `[doc_05]` | 严格接口拒绝正确内容后，模型改成 `value` 时退化为把 05–08 全列入；T3 再对文件 list_directory 并 blocked。格式归一化可保住显式正确决定。另有隐含验收风险：target 要 `priority_files`/整数 phase，而 Goal 只说 priority filenames/phase。 |
| E2E-H14 | TN | 成功发现三个 manifest 后，RWKV 未读取任何数据文件便把文件数 5 当成 record_count/total_records，并生成错误顶层、顺序和相对路径 | T1 因 global_index 可读而完成；T2 递归列目录后对 manifest 文件调用 list_directory。模型还尝试未注册 `lh_workset`，直接印证动态发现集合缺少协议承载。 |
| E2E-H15 | TN | Goal 未列目录、未读 REQUIREMENTS/tests，误把 `event_report/` 包内三个模块定位到根目录 | 模型把“要求创建但目前缺失”的文件当成不可克服的 FileNotFound，未执行任何 write，Final 也错误要求外部先创建模块。代码任务需要仓库地图和“缺失目标=待创建”状态，而非替模型实现。 |
| E2E-H16 | TN | 七个 Task 的 done_when 全被 evidence-kind 说明污染，依赖又全部为空；T1 未读 policy/config/checker便写入臆造 `configs/config.json` | 多次把脚本名幻想成工具后才执行真实 checker，现有 capacity/runtime 未改；Final 凭空声称 invariant 要求 10/100。协议说明位置、真实文件依赖、失败 verifier 回流和 Final 事实投影全部有缺陷。 |
| E2E-H17 | FP | 工具/恢复无错误，RWKV 业务 schema 写成 id→`{amount,count}` 映射并把重复 A 金额累计为 8 | target 要首次出现记录数组、顶层 count 与 total_amount；模型读回自身输出后完成。resume 不重跑与 byte stability 两项均通过，说明幂等骨架可保留；Goal 对精确 schema 也应进一步显式化。 |
| E2E-H18 | TN | CSV 与 policy 都已完整读取，模型仍对 `products.csv` 调用 `read_json` | JSONDecodeError 后任务 blocked，release/validator/digest 全未启动；Final 能识别格式不匹配，却没利用已经可用的 CSV 原文继续。与 B09/B21/M13/H10 同属读取格式事实未稳定传递。 |
| E2E-LH01 | TN | 四个分阶段修复 Task 都把完成绑定成 verifier 最终成功，无法表达“修完本层后失败推进到下一层” | 模型看到 project/ 却不列目录，反而把 orders 改写成 JSON 字符串并查找根 pipeline.py；路径失败后 recovery capsule 连续回显。需要 stage-aware expected outcome、项目地图、输入只读与最小恢复。 |
| E2E-LH02 | FP | 架构强制先 Goal 规划，无法满足“先读 requirements 再规划”；16 项计划又触发 8 Task 上限 | 退化后只建一个错路径 `checkpoint/step01.json` Task，从未读 early requirements，却把用户 Goal/协议提示拼成 constraints；一步后 Goal done，Final 幻称 15 checkpoints 和 final config 全完成。需要只读 preflight 和增量 workset。 |
| E2E-LH03 | TN | RWKV 已正确读完 root、三 manifest 和五个 data 文件，随后又把 east/deep 的相对 data 路径错误拼成 east/data | 两个多余 FileNotFound 抹杀完整 discovery，build Task不启动，Final只记最后错误。缺少动态 workset 的基目录解析、成员已读状态和“集合已封口”事实。 |
| E2E-LH04 | FP（含恢复风险） | 业务值基本正确，但模型用顶层 `entries`，离线 target 用 `events`；Goal 未显式规定键名 | post-effect crash 后系统实际重放同一覆盖 write，虽幂等且字节稳定检查通过，Final却声称没有 replay。严格恢复应基于 action fingerprint/artifact digest 调和已落地副作用后标记 recovered。 |
| E2E-LH05 | TN | 四个 Tasks 全无依赖，且只有读取/验证输出的消费者，没有明确 producer；多个 lane 同时启动 | T1 未读 shard 便幻写 20/20/0 summary，T3/T4 才刚列真实成员并开始读取；错误结果先落盘，报告未创建。需要 producer→workset→report→verify 的真实依赖和共享成员状态。 |
| E2E-LH06 | TN | 权威 policy、approved、draft 和 untrusted note 均已成功读取，安全边界也无违规 | T2/T3/T4 的 `lh_task_done` 因 envelope 外注解被拒，T3继而被 unchanged-loop封锁，输出 Tasks不启动。Final前后又同时说 draft 已读和无法读。属于纯完成协议/事实投影缺陷。 |
| E2E-LH07 | TN | 第一次 Goal 输出超长语法错误；随后四次稳定使用常见单键调用 `{"lh_tasks":{"tasks":...}}`，转换层不接受 | 0 Task/0 Attempt，Final凭空声称 service 文件不存在，外部实际能枚举八个文件。可将单一已显示函数键+对象 payload 无损归一化为 function/params，raw 保留，不生成 Task 字段。 |
| E2E-LH08 | TN | Task done_when 被协议说明污染；模型未读 configs 或 compensation policy，把整份 change_request 分别写到根 a/b/c.json | 提前运行 checker得到“最高优先级未保留”后仍重复错误写，真实 configs未改。需要 discovery、源目标字段映射保真、stage failure observation 和上层补偿重规划。 |
| E2E-LH09 | TN | 已注册且题目要求的 stateful `mock_api` 因“无 deterministic verification contract”被控制器在 0 Attempt 阻止 | 模型的两个候选调用自身也有嵌套/缺 operation 格式错误，但即使后续格式正确，当前策略仍不允许执行。状态型动作应由 action return、request_id、query/finalize observation取证，而非强制 workspace verifier。 |
| E2E-LH10 | TN | RWKV 已正确修复 mean/clamp 且 unittest 通过；随后在 T1 越权先写错误 manifest，并因 README JSON 引号错误进入协议恢复 | `shell:false` 先被拒约十次，恢复上下文又截断；README缺失，manifest含 sha256 前缀且映射 tests。Final错称函数名并误说 manifest没创建。代码能力成立，失败在格式、职责/依赖和 Final 事实。 |
| E2E-LH11 | TN | Goal 将第一批八个文件错误分成八条并行 Task，每条又要求自己检查八文件并找两条事实 | 八个错位滑动窗口重复扫描，138 Attempts 只推进约 24 号；每 lane把 Task号当 phase，生成 phase01–08，而非五个 phase。上下文涨至 16293 tokens，Final 也超限。需单一有序 workset、8成员 barrier、共享事实表和确定性状态胶囊。 |
| E2E-LH12 | TN | 初次完整 Goal 输出超长截断后，系统退化为单一“先跑 pytest 且必须全通过”Task | 隔离环境无 pytest，三次原样重试后 blocked，未读 requirements/源码/测试；离线 unittest可运行并显示 NotImplementedError。环境失败需允许替代 runner和实现规划，不能永久阻塞。 |
