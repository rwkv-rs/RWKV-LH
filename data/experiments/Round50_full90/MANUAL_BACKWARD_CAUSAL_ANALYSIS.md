# Round50 E2E-90 逐题反向因果分析

本报告由完整运行结束后逐题检查 `model_trace.json`、`audit.json`、动作结果、最终工作区和冻结 external acceptance 得出。脚本汇总只用于定位事件；下面的判断逐题追溯了“最终结果 → 验收/完成边界 → Task 验证 → Action → RWKV 原始输出”。隐藏验收和 Codex 参考答案均未进入运行时。

## 结论

Round50 的两阶段工具选择候选不能保留为最佳版本。Strict E2E 从 Round46 的 `31/90` 降到 `6/90`，External 从 `32/90` 降到 `11/90`。不过下降不是“两阶段选择必然无效”的充分证据，因为该候选稳定诱发了现有格式层尚未注册的 `tool_name` 形式：62 题最终停在动作物化，49 题最后一次错误都是语义完整的 `{"tool_name": ..., "arguments": ...}` 被当成未知字段。

反向链路有四个彼此独立的缺陷层：

1. 协议接缝损失：RWKV 已给出明确工具名和完整参数，格式层仅因 `tool_name` 键名拒绝。
2. Goal/Task 可执行性损失：计划把“排序、计数、验证、读取一批文件”拆成无法由单次 Harness action 完成的 Task，随后又强制每个 Task 必须执行新动作。
3. 恢复闭环损失：失败反馈没有改变下一次工具或路径；旧 Task postcondition 甚至会拒绝已经成功的 fallback。
4. 完成证据失真：错误或不完整产物被 Task/Goal evidence 认证，形成假阳性。

## 基础组（30/30 人工复核）

- `E2E-B01`：产物字节完全正确；T3 的验证 `read_file` 原始调用为完整 `tool_name+arguments`，两次被格式层拒绝，形成 FN。根因从动作格式边界开始，后续控制器阻断放大。
- `E2E-B02`：T1 已正确选择 `read_file`，参数也准确指向 `input.txt`；首次动作即因 `tool_name` 键名被拒。纯协议接缝损失。
- `E2E-B03`：先正确读取 `config.json`，随后生成的 `write_json` 值与目标一致；写动作因 `tool_name` 被拒，原文件保留。纯协议接缝损失发生在第二个动作。
- `E2E-B04`：RWKV 读取源文件、建目录并写了 manifest，但两次写动作都写向 manifest，没有创建 `archive/2026/source.txt`。Goal obligation 察觉缺口后，重规划输出又缺少 canonical task-batch 外壳。首因是计划/动作覆盖遗漏 copy，格式错误只是恢复阶段放大器。
- `E2E-B05`：正确选择并参数化 `read_file(app.env)`，在首动作被 `tool_name` 拒绝。纯协议接缝损失。
- `E2E-B06`：正确选择并参数化 `read_file(part_a.txt)`，在首动作被 `tool_name` 拒绝。纯协议接缝损失。
- `E2E-B07`：读写链、产物、证据和 external acceptance 均通过，是两阶段协议的正控制。
- `E2E-B08`：四个读写/验证动作与最终产物均通过，是较长基础链的正控制。
- `E2E-B09`：正确选择 `read_file(scores.csv)`，在首动作被 `tool_name` 拒绝。纯协议接缝损失。
- `E2E-B10`：工具选择 `read_file` 正确，参数值也正确；第二阶段把 `tool_name` 与 `path/start_char/max_chars` 平铺，未放入 `arguments`。这是常见但不同于单纯键名别名的扁平调用格式，不能由只改 `tool_name` 的消融解决。
- `E2E-B11`：已读取 name 并进行了写入；后续写调用使用 `tool_name+input_parameters`。这里同时存在参数容器别名和此前写入内容可疑，不能归为单纯 `tool_name` 修复可恢复。
- `E2E-B12`：正确选择 `read_file(numbers.txt)` 并给出完整参数，两次只因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-B13`：正确读取旧 JSON，随后正确构造目标 JSON；写动作因 `tool_name` 被拒。纯协议接缝损失发生在第二个动作。
- `E2E-B14`：正确选择 `read_file(left.txt)`，在首动作被 `tool_name` 拒。纯协议接缝损失。
- `E2E-B15`：读、写、显式 no-op 和读取验证均通过，是包含内部控制任务的正控制。
- `E2E-B16`：正确选择 `read_file(app.env)`，在首动作被 `tool_name` 拒。纯协议接缝损失。
- `E2E-B17`：`active_users.json` 已完全正确；计划又创建“排序”和“计数”Task，尽管上一步产物已经满足它们，控制器仍强制新动作。RWKV 为此发明未注册 `sort_array`，形成 FN。首因是 Task/action 必须一一对应且不能用已有 observation 直接满足 postcondition。
- `E2E-B18`：目标 `total.json` 已完全正确；最终读取验证因 `tool_name` 被拒，形成 FN。纯协议接缝损失发生在完成边界前。
- `E2E-B19`：完整读写验证通过，是正控制。
- `E2E-B20`：正确选择 `read_file(parity.py)`，在首动作被 `tool_name` 拒。纯协议接缝损失。
- `E2E-B21`：任务要求读取 CSV，RWKV 连续三次选择 `read_json(items.csv)`；每次得到同一 JSONDecodeError，恢复没有促使重新选择 `read_file`，预算耗尽。首因是错误工具选择，放大器是失败反馈未进入下一次工具选择决策。
- `E2E-B22`：已正确读取 `tasks.json`；写 `TASKS.md` 时给出了正确内容，但把 `tool_name` 与四个参数平铺。属于混合扁平格式，不是语义决策错误。
- `E2E-B23`：正确选择 `read_json(data/primary.json)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-B24`：正确选择 `read_file(log.txt)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-B25`：正确选择 `read_json(base.json)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-B26`：三个目标文件均已正确生成；最后读取验证因 `tool_name` 被拒，形成 FN。纯协议接缝损失发生在完成边界前。
- `E2E-B27`：正确选择 `read_file(service.conf)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-B28`：六个动作、产物和验证完整通过，是本组最长的正控制。
- `E2E-B29`：读取源文件后，RWKV 把观察到的 `immutable payload` 错写成猜测的 `line one`，且 manifest 未形成最终可验收文件；后续读取又被 `tool_name` 拒。首因是 observation→arguments 内容丢失/猜测，协议错误是次生阻断。
- `E2E-B30`：正确选择 `read_file(names.py)`，在首动作被 `tool_name` 拒。纯协议接缝损失。

## 中等组（30/30 人工复核）

- `E2E-M01`：RWKV 先列出服务，再由第一阶段选择 `write_json`；第二阶段只输出 `path/value`，省略调用名。参数本身构成完整写意图，但需要跨阶段携带已由 RWKV 选择的名字；不属于本轮 `tool_name` 单键别名。
- `E2E-M02`：正确选择 `read_file(calculator.py)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M03`：迁移后的 `users.json` 已正确；最终读回验证因 `tool_name` 被拒，形成 FN。
- `E2E-M04`：`release.json` 正确，但 `RELEASE.md` 写成三行 `# Nebula / 3.4.2 / Released...`，而要求标题为单行 `# Nebula 3.4.2`。Task 验证与七个 Goal criterion 都把错误 Markdown 认证为正确，形成 FP。首因是参数内容错误，放大器是 actual/expected 证据绑定没有验证完整格式。
- `E2E-M05`：正确选择 `read_file(docs/requirements.txt)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M06`：只复制 `alpha.dat`，遗漏 `gamma.dat`，manifest 也只含 alpha；后续 noop/read 验证仍把部分结果认证为完成。首因是“处理 selection 中全部文件”的集合任务被单个 copy action 截断，放大器是集合完备性未进入证据。
- `E2E-M07`：五个 JSON 读写动作、产物和验收全部通过，是中等组唯一 Strict 正控制。
- `E2E-M08`：输出顺序是 `api, worker, web`，要求是 `api, web, worker`；RWKV 验证时错误声称前者按字母排序，Task/Goal evidence 接受该判断，形成 FP。这里是模型排序判断错误与弱证据完成边界共同产生。
- `E2E-M09`：正确选择 `read_file(src/api.py)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M10`：基准预设前三个副作用动作瞬态失败；系统连续重试同一写动作三次后立即耗尽 recovery lineage，没有进入基准要求的 replan。首因是恢复预算/状态机边界与任务语义不匹配，不是工具格式。
- `E2E-M11`：四个原服务文件完全未迁移，summary 却写成未观察到的 auth/payment/inventory/analytics 与 808x 端口。Goal evidence 仍把这些错误文件认证，形成 FP。首因是 observation→arguments 整体幻觉，放大器是证据没有把输出逐项对回四个来源。
- `E2E-M12`：正确选择 `list_directory(.)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M13`：已读取一个输入后，为 CSV 读取发明未注册 `read_csv`。这是工具目录服从失败；现有 `read_file` 本可完成，不能由格式层改名。
- `E2E-M14`：已读取 release 数据并构造目标对象；第二阶段只输出 `path/value`，省略已选的 `write_json` 名称。属于两阶段跨消息承接格式缺口。
- `E2E-M15`：列目录后正确选择 `read_json(docs/index.json)`，因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M16`：完成多次目录/JSON 读取后需要恢复，RWKV 输出 `schema_version=2025-06-04`，不符合唯一 task-batch schema。首因在 replan 协议服从，不是工具动作层。
- `E2E-M17`：列目录并读一个 package 后，下一次正确 `read_json(packages/web.json)` 因 `tool_name` 被拒。协议接缝中断了集合遍历。
- `E2E-M18`：正确选择递归列出 `inputs/`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M19`：正确选择 `read_file(access.log)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M20`：正确选择 `read_file(parser.py)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M21`：已读取两个来源，但 `merged_users.json` 最终只有 `record_count: 3`，没有 users 数组；两次写入和 command 检查仍被证据链认证，形成 FP。首因是合并结果在 observation→arguments 时被压扁，放大器是只验证了局部计数字段。
- `E2E-M22`：读取多个来源后构造了一个与目标结构不完全一致的 result，且写阶段输出绝对路径与无名称 `path/value`。同时存在派生内容错误、workspace 路径泄漏和两阶段调用名承接缺口。
- `E2E-M23`：读 manifest 后给出写文件内容，但把 `tool_name` 与写参数平铺。属于混合扁平格式。
- `E2E-M24`：成功读取一个测试文件，读取第二个文件时完整调用因 `tool_name` 被拒。协议接缝中断多文件检查。
- `E2E-M25`：正确选择 `read_json(changes.json)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M26`：列目录后正确选择 `read_json(records.json)`，因 `tool_name` 被拒。协议接缝中断。
- `E2E-M27`：正确选择 `read_json(graph.json)`，首动作因 `tool_name` 被拒。纯协议接缝损失。
- `E2E-M28`：把真实文件名 `logs/2026-07-31.log` 猜成不存在的 `logs/2026-07-31_log.txt`；失败后又退回重复读取 retention.json，未重新列目录，最终预算耗尽。首因是路径猜测，放大器是恢复没有要求重新取得可观察文件清单。
- `E2E-M29`：翻译值本身正确，但输出遗漏顶层 `locale=zh-CN` 与 `missing_keys=[bye,cancel]`；六个 criterion 仍全部通过，形成 FP。首因是 Goal/plan obligation 漏字段，放大器是 evidence 只验证已有翻译映射。
- `E2E-M30`：正确选择 `read_json(config.json)`，首动作因 `tool_name` 被拒。纯协议接缝损失。

## 困难组（30/30 人工复核）

- `E2E-H01`：正确选择 `read_file(example.csv)`，首动作因 `tool_name` 被拒，代码链未开始。
- `E2E-H02`：正确选择递归列出 shards，首动作因 `tool_name` 被拒，集合链未开始。
- `E2E-H03`：正确选择 `read_file(seed.txt)`，首动作因 `tool_name` 被拒。
- `E2E-H04`：正确选择读取不可信输入，首动作因 `tool_name` 被拒；并未发生提示注入越权。
- `E2E-H05`：只读取 corpus 中一个文件便写 summary，且把 JSON 对象再次作为字符串写入；后续工具名选择输出 `{"tool":"read_json"}` 又缺空 arguments。首因是集合 cardinality 与 JSON 值类型错误，格式错误是后续放大。
- `E2E-H06`：正确选择递归列出 envs，首动作因 `tool_name` 被拒。
- `E2E-H07`：正确选择递归列出工作区，首动作因 `tool_name` 被拒。
- `E2E-H08`：ledger 实际是正确的 first-seen 顺序 `evt-3, evt-1, evt-2`；验证模型却连续声称该顺序错误，系统随后只重复读取相同正确文件并耗尽预算。首因是 RWKV 验证判断错误，放大器是 unchanged observation 没有转向修正 verifier/Task 状态。
- `E2E-H09`：primary 缺失后 backup 已成功读取；但 T1 postcondition 固定为“必须观察 primary”，所以 fallback 数据被验证器正确地按旧合同拒绝两次。首因是计划把 fallback 分支建成两个并行普通 Task，恢复无法更新条件分支的 postcondition。
- `E2E-H10`：读 CSV 和 policy 成功后，“计算”Task 选择 `read_json(inventory.csv)`，恢复又猜测不存在的 `release` 路径，最后重复 JSONDecodeError。首因是计算 Task 没有可执行动作表示，放大器是恢复没有根据错误重新选工具/策略。
- `E2E-H11`：没有修改 `pipeline.py`，而是创建带额外字符串引号的独立 build/validate/total 文件，并写入无关 Alice/Bob release 数据；后续证据仍宣告五阶段通过，形成 FP。首因是任务图与目标文件覆盖错位及参数幻觉，放大器是 verifier 未运行真实 `verify_pipeline.py` 作为完成证据。
- `E2E-H12`：正确选择递归列出 shards，首动作因 `tool_name` 被拒。
- `E2E-H13`：连续六次只读取 `corpus/doc_01.txt`，没有推进其余文档；第七次又输出 `action+平铺参数`。首因是“一 Task 处理多文件”与单动作 cardinality 不匹配，格式错误只终止了已经停滞的链。
- `E2E-H14`：只读一个 manifest 后写了部分 global index；下一写调用使用 `action+平铺参数`。首因是多 manifest 覆盖不足，次因是扁平格式。
- `E2E-H15`：未读现有代码和测试便直接生成 `parser.py`，第二阶段只输出写参数而没有工具名。首因是 Goal/plan 缺少 inspect-before-edit，格式缺口随后阻断。
- `E2E-H16`：完成六个读取后，把 audit 中暴露的绝对 workspace 路径复制到 `read_json`，即使接受 `tool_name` 仍会被 workspace-relative 约束拒绝。首因是内部绝对路径泄漏到模型可复制证据，格式是次生问题。
- `E2E-H17`：正确读取并构造 ledger，但第二阶段只输出 `path/value`，省略已选择的 `write_json` 名称。两阶段跨消息承接格式缺口。
- `E2E-H18`：读取两个 JSON 后以 noop 代替中间推导，随后发明未注册 `read_text`。首因是工具目录服从与不可执行推导 Task，不是格式别名。
- `E2E-LH01`：正确选择读取 `project/pipeline.py`，首动作因 `tool_name` 被拒，代码修复未开始。
- `E2E-LH02`：15 个 checkpoint 全部正确；final/config.json 却沿用 checkpoint 的 `{step,constraints}` 外壳再加 generated_by，而验收要求五个约束平铺并仅增加 generated_by。18 个 Goal criterion 把错误 final 形状全部认证，形成 FP。首因是跨阶段结构复制错误，放大器是 actual/expected 同源或只验值未验形状。
- `E2E-LH03`：正确选择 `read_json(catalog/root_manifest.json)`，首动作因 `tool_name` 被拒。
- `E2E-LH04`：读取输入并写出接近目标的 ledger 后，验证 Task 再次选择写而非读，完整写调用又因 `tool_name` 被拒。较早已有工具选择/Task 角色错误，格式是终止点。
- `E2E-LH05`：正确选择列出 shards，首动作因 `tool_name` 被拒。
- `E2E-LH06`：读取 manifest 和多个文件后，模型从环境证据复制绝对 workspace 路径给 `read_json`，被 relative-path 约束拒绝。根因是路径表示边界，不应放宽安全约束。
- `E2E-LH07`：正确选择递归列出 services，首动作因 `tool_name` 被拒。
- `E2E-LH08`：Task 指向配置读取，但动作把 `configs/a.json` 丢成 `a.json`；两次恢复继续同一路径，尽管其他并行依赖已读取成功，最终耗尽预算。首因是 task→argument 路径丢失，放大器是 recovery feedback 没有携带可信候选路径。
- `E2E-LH09`：第一阶段已由 RWKV 选择 custom `mock_api`；第二阶段给出完整 operation/request_id/payload，但省略调用名。语义意图完整，属于两阶段跨消息承接缺口，不应由控制器重新选择操作或参数。
- `E2E-LH10`：读取输入两次后为测试输出发明未注册 `read_test_output`，而目录中已有 `check_command`。首因是工具目录服从与验证 Task 可执行性。
- `E2E-LH11`：把文件路径 `artifacts/025-032.txt` 当目录连续 list，既没有读取文件也没有遍历其余分片；最后完整调用又因 `tool_name` 被拒。首因是路径类型与集合 cardinality 错误。
- `E2E-LH12`：读取源码后先把 report 当 JSON 写，随后尝试写 parser 时因 `tool_name` 被拒；链路在代码、测试、报告多目标之间角色混乱，不能只靠别名修复。

## 对下一轮结构的约束

1. 先做最小、可审计的 `tool_name -> name` 键名归一化，只接受字段集合恰好为 `tool_name,arguments` 的形式；不得展开平铺参数、补工具名、补参数或改值。
2. 该消融必须在 Round50 候选上运行，以隔离“二阶段本身”与“既有格式层缺口”；最终仍与已上传 Round46 的 `31/90` 比较，未超过则回退两阶段代码。
3. 后续独立处理 Task/action cardinality、已有 evidence 直接满足 postcondition、conditional fallback Task、路径来源和 verifier 错判；不得把这些语义缺陷塞入格式层。
4. FP 修复必须以 external artifact obligation 为边界：集合完备性、JSON/Markdown 完整形状、源到输出逐项对应和真实 verifier 结果都要有独立证据，不能用规则生成正确答案。
