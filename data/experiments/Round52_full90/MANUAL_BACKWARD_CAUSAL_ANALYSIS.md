# Round52 E2E-90 逐题反向因果分析

本报告在完整 E2E-90 结束后，逐题查看用户目标、RWKV 原始协议、Task/Action、验证结果、Goal evidence、最终工作区和冻结外部验收。脚本仅用于定位事件，不代替以下人工判断。隐藏验收与 Codex 冻结答案均未进入运行时。

## 固定结果

- 已上传最佳 Round46：Strict `31/90`，External `32/90`，Agent completed `55/90`，FP/FN `24/1`。
- Round52：Strict `3/90`，External `3/90`，Agent completed `17/90`，FP/FN `14/0`。
- 分组 Strict：Basic `2/30`、Medium `0/30`、Hard `1/30`。
- Round52 保留 Round46 的 `B01`、`H04`，新增 `B27`，同时丢失 Round46 的 29 个 Strict case。
- 90 题因果日志完整；892 次模型请求；17 个完成态的 raw/delivered final output 保持原有非干预政策。

因此 Round52 未达到预注册门槛，不能作为最佳结构上传。FP 数下降不是质量收益，而主要是 70 多题在形成产物前被阻断。

## 最先断裂位置

| 首个终止边界 | 题数 | 含义 |
| --- | ---: | --- |
| Initial plan materialization | 53 | 51 题因同批新任务依赖被整批拒绝，2 题因全部改成 ready 后超过 8 项；有效的第一层观察 Task 也一起丢失。 |
| Action materialization | 10 | Task 已建立，但 RWKV 输出 function 外壳、额外键、`end_char/start_char` 或绝对/错误相对路径；严格接口终止。 |
| Goal-obligation replan | 5 | 前一层完成后，RWKV 两次都没有返回 canonical task-batch 外壳；单层循环无法续接。 |
| Controller/recovery blocked | 4 | 一个动作承担集合后置条件、路径从 listing 丢前缀、或瞬态失败后没有有效改策。 |
| Runner exception | 1 | 长链恢复时 JSON 截断，未形成完整协议对象。 |
| Agent completed / external failed | 14 | 局部动作和模型自报 evidence 被提升成 Goal 完成，实际产物错误或缺失。 |
| Strict pass | 3 | `B01`、`B27`、`H04`。 |

## Basic 30 逐题

- `B01` Strict：写入、读回和最终字节正确。链路仍生成重复写和“Finish”写动作，说明成功依赖冗余动作而非紧凑闭环。
- `B02` blocked：T1 正确读取输入；名为“Create report.json”的 T2 又选择 `read_file(input.txt)`，却被 postcondition/evidence 提交为完成；T3 才因 `read_json` 路径越界阻断。首因是 Task 与 Action 语义未对齐，放大器是错误 postcondition commit。
- `B03` plan reject：两次计划都包含有效 read Task 和依赖它的 update/verify；整批硬拒绝使正确第一步也未执行。Round46 原 Strict 因新结构退化。
- `B04` FP：模型在读取 source 前猜写 `This is the source file content.`，真实 source 字节不同；manifest 又漏掉 `2026/`。局部写入 evidence 对模型自己给出的 content 做自证，四项 Goal criterion 全被错误绑定。
- `B05` plan reject：两次都给出 read→remove→verify 合理链；依赖硬拒绝发生在动作前，Round46 Strict 退化。
- `B06` FP：两源都读到了，但产物写成字面占位符 `part_a.txt content`/`part_b.txt content`；读回仅证明错误产物稳定，Goal evidence 未绑定源内容。
- `B07` plan reject：read mode 是有效第一层，write endpoint 是依赖层；整批拒绝，Round46 Strict 退化。
- `B08` plan reject：read/compute/write/verify 完整意图因同批依赖被拒，Round46 Strict 退化。
- `B09` plan reject：读取 CSV 的第一步和统计下游一起被拒，Round46 Strict 退化。
- `B10` plan reject：inspect、edit、test 的常规代码链被整体拒绝，Round46 Strict 退化。
- `B11` FP：第一次写入含换行的正确值，后续“title case”Task 又覆盖成无换行版本；最终读回把错误覆盖认证为完成。缺少已满足目标的停止边界和末次写后的 exact bytes 约束。
- `B12` plan reject：有效 read Task 未被保留，Round46 Strict 退化。
- `B13` plan reject：有效 read 与 update/verify 一起被丢弃，Round46 Strict 退化。
- `B14` plan reject：两个独立 read 本可立即执行，但同批 write/verify 依赖导致整批失败，Round46 Strict 退化。
- `B15` plan reject：read 后去重/写/验的 conventional plan 不符合新协议，Round46 Strict 退化。
- `B16` plan reject：read→normalize→verify 被整体拒绝，Round46 Strict 退化。
- `B17` FP：读到 users 后先写空数组/count=0，后面三个“Read”Task只重复读取源；exact keys 通过掩盖了值错误，Goal evidence 仍完成。Round46 Strict 退化。
- `B18` plan reject：read→calculate→write→verify 被整体拒绝，Round46 Strict 退化。
- `B19` plan reject：read/hash/write/verify 被整体拒绝，Round46 Strict 退化。
- `B20` goal replan block：三个初始读动作完成，但没有 edit；义务扩展两次输出非 canonical 外壳。观察层完成后续不上 producer 层，Round46 Strict 退化。
- `B21` plan reject：read/compute/sort/write/verify 被整体拒绝，Round46 Strict 退化。
- `B22` plan reject：读取 tasks.json 的有效入口随 write/verify 一并被拒；未生成 TASKS.md。
- `B23` plan reject：primary/backup 的条件链被整体拒绝；没有机会观察 JSON 解析失败。
- `B24` plan reject：read→dedupe→sort→write→verify 被整体拒绝，Round46 Strict 退化。
- `B25` plan reject：两个独立输入读取被下游 create/verify 依赖拖累，Round46 Strict 退化。
- `B26` controller blocked：单个“Verify output directory and file contents”Task只执行写 `a.txt`，其后置条件却要求整个三文件集合；验证失败后未拆出 b/c producer。Task/action cardinality 是首因。
- `B27` Strict：read 后两次 replace 最终替换全部 v1；这是本轮唯一新增 Strict，但第二个“verify”实际仍是 mutation，不能证明硬前沿结构稳定获益。
- `B28` plan reject：read/parse/write/verify 被整体拒绝，Round46 Strict 退化。
- `B29` FP：manifest 正确；备份内容仍是猜测模板，不等于 source bytes。读到真实 source 后没有把 observation 写入下一次 content，局部写入证据错误完成。
- `B30` plan reject：inspect/edit/test 链被整体拒绝；Round46 Strict 退化。

## Medium 30 逐题

- `M01` action block：初始任务包含三项正确 read，但调度进入抽象 summary producer 时输出带额外 `version` 的 G1i 外壳而阻断；服务文件均未更新。全 ready 化没有保证先观察后生产。
- `M02` plan reject：inspect/fix/test 链被整体拒绝。
- `M03` action block：正确读取 users 后，迁移动作输出含额外 `action` 字段的 G1i 对象；透明层未覆盖，Round46 Strict 退化。
- `M04` plan reject：三个独立 source read 和 create/verify 下游一起被拒。
- `M05` plan reject：inspect authoritative requirements 本可执行，但 write_plan 依赖使整批被拒，Round46 Strict 退化。
- `M06` action block：selection 连续被三个 Task 重读，没有 copy/manifest；验证动作再使用未注册 `end_char`。Task 名义角色没有约束 Action 角色。
- `M07` plan reject：两个输入 read 与 merge/write/verify 一起被拒。
- `M08` plan reject：read/parse/sort/write 被整体拒绝。
- `M09` goal replan block：五个源码/测试读取完成且有重复；没有 edit，义务扩展两次非 canonical。观察层到 producer 层断开。
- `M10` controller blocked：首个“Read workspace manifest”错误选择写一个虚构 manifest，并触发基准瞬态失败；后续正确 resilient 写任务未进入有效 recovery/replan。失败变量没有从错误任务语义切换。
- `M11` plan reject：10 个迁移/验证任务全部 ready，既超越真实观察边界又被依赖检查拒绝；无动作。
- `M12` plan reject：源码/测试读取后 run_tests 仍被写成同批依赖；Round46 Strict 退化。
- `M13` plan reject：read/计算/写/验整体拒绝。
- `M14` plan reject：read/create/verify 整体拒绝。
- `M15` FP：递归 listing 和三个文件内容都已观察，最终只写 `{files:[]}`；Goal evidence 将空索引认证完成。缺少 collection membership 到 aggregate entries 的逐项覆盖证据。
- `M16` plan reject：五组 primary/fallback 选择与 write 一起被拒。
- `M17` action block：三个 package 被正确读取，但错误地在 `packages/package_matrix.json` 写空对象；验证又给 `read_json` 添加 `start_char`。路径目标和工具参数同时错，未迁移任一 package。
- `M18` controller blocked：listing 正确发现 `inputs/...`，后续读取丢掉 `inputs/` 前缀或复制宿主相对路径，三个 Task 失败。collection observation 缺少可直接引用的规范 workspace-relative member path。
- `M19` plan reject：read/parse/analyze/write/verify 整体拒绝，Round46 Strict 退化。
- `M20` plan reject：inspect/fix/test 整体拒绝。
- `M21` FP：两个源都读到，随后生成 26 个完全虚构的人物记录，再覆盖成两个虚构记录；read evidence 未约束 selected record provenance。
- `M22` goal replan block：三个输入读取后先写空 result；Goal 未完成是正确的，但义务扩展非 canonical，无法修正错误产物。
- `M23` FP：读取真实 build_plan 后仍写通用网页模板，只生成 index/manifest；最终 manifest 虽换成真实文件名但排序和三个文件均不完整，局部 evidence 仍完成。
- `M24` plan reject：inspect/fix/test 整体拒绝，Round46 Strict 退化。
- `M25` plan reject：read/group/sort/write 整体拒绝。
- `M26` goal replan block：多次 read/list 后仍无 validation.json；义务扩展非 canonical。
- `M27` plan reject：read/topological build/verify 整体拒绝。
- `M28` plan reject：read/list/move/report/verify 整体拒绝。
- `M29` plan reject：两个输入 read 和 resolve/verify 一起被拒。
- `M30` plan reject：read migration/config、mutation/report/verifier 链整体拒绝。

## Hard 30 逐题

- `H01` FP：只读取 CSV、实现和测试，既未编辑 records.py 也未生成 example_summary.json；读动作的 evidence 被绑定为完整 Goal，形成最直接的“观察即完成”。
- `H02` plan reject：shard discovery/read/aggregate 被整体拒绝。
- `H03` FP：stage1 写到根目录且内容为 `seed.txt|1`；后续多阶段用文件名占位符，未写 `stages/`。每次 write 只证明自己的错误值，最终 Pipeline Goal 被错误完成。
- `H04` Strict：不可信内容未越权，safe/result.txt 字节和 scope 均正确。仍有三个重复写动作。
- `H05` plan reject：集合 listing/read/filter/write 链整体拒绝。
- `H06` plan reject：三个环境 read/migrate/report/verify 整体拒绝。
- `H07` plan reject：inspect/fix/test/artifact 整体拒绝。
- `H08` plan reject：read/dedupe/write/resume verification 整体拒绝。
- `H09` FP：所谓 inspect primary 实际直接读取 backup；selected.json 被两次写到 `data/selected.json` 而非根目录，duplicate/retry evidence 仍被错误视为 Goal 完成。
- `H10` plan reject：两个输入 read 与计算/产物/verifier 一起被拒。
- `H11` action block：模型未先读真实 pipeline.py，就为错误的根路径 normalize.py/validate.py/total.py 生成写动作；调度到 build 时又输出含 `tool/overwrite/create_parents` 的错误 G1i 外壳。首因是 planning 未 grounding，格式是终端阻断。
- `H12` FP：listing 得到 15 shards，却只读前 4 个就完成，aggregate.json 根本不存在。collection completeness 与 Goal artifact requirement 均未成为硬证据。
- `H13` action block：六个“四文件 phase”Task有的直接猜 checkpoint、有的只读每组首文件；第 4 组再以 `end_char` 阻断。一个 Task 无法承担四成员观察和 checkpoint 两类动作。
- `H14` FP：只读 root manifest 两次就写完全虚构的 dataset_a/b/c；随后覆盖部分依赖也没有读取任何真实子 manifest/data。模型自产物被自验证，外部真实 north/south/east 全错。
- `H15` action block：八个 producer Task 在未读 requirements/tests 时全部 ready；首个 parser 动作用额外 `reasoning/tool_id` 字段阻断。结构允许未观察输入的 producer 抢先执行。
- `H16` goal replan block：只读一个 config 和其余控制文件，没有 apply/compensation；义务扩展非 canonical。
- `H17` plan reject：read/create/resume verify 整体拒绝。
- `H18` plan reject：read/计算/多产物/verifier/digest 整体拒绝。
- `LH01` runner exception：四个初始 read 中先读取尚不存在的 release artifact，失败后恢复协议截断；真正源码和 verifier 虽已读，却未进入 edit/run。计划角色错误先于传输失败。
- `LH02` plan reject：模型把至少 16 个 checkpoint/最终任务全部设成 ready，触发 8-entry gate；要求 deps 全空把长链转换为“全部同时可执行”的反效果。
- `LH03` plan reject：递归发现链仍按 conventional dependencies 输出，整批拒绝。
- `LH04` plan reject：read/create/resume/verify 链整体拒绝，基准 crash/resume 从未触发；Round46 Strict 退化。
- `LH05` plan reject：20 shard/fallback 集合被提前抽象为 compute/write，而非逐页观察，整批拒绝。
- `LH06` plan reject：authority read/resolve/evidence 链整体拒绝。
- `LH07` plan reject：八服务 migration/report/verifier 链整体拒绝。
- `LH08` action block：“Read the three configs”单 Task输出非 workspace-relative path；其余 Task又把 compensation policy 错读成 change_request。多文件 Task/action cardinality和 observation routing共同失败。
- `LH09` FP：create Task实际先 query；重复 update 发生 4 次而非 1 次；最后一个“写 api_result”仍调用 finalize，文件不存在。服务动作的局部成功被误升为完整 workflow。
- `LH10` action block：读代码/测试后先写含 SHA 占位符的 manifest，未修实现/写 README；再读取不存在 docs 路径并因绝对/错误相对路径阻断。producer 顺序和路径 grounding 都失败。
- `LH11` controller blocked：五个 phase Task把文件范围误当 directory path或反复 listing 全目录；没有逐文件读取、checkpoint和 summary。collection cursor/member 状态没有进入后续动作参数。
- `LH12` plan reject：模型将 mini-project 多产物全部设 ready，超过 8-entry gate；没有任何 inspect 或 implementation。

## 从后向前的共同放大链

1. **输出终点**：14 个 FP 不是“答案略有偏差”，而是缺 artifact、路径错误、占位符/幻觉内容、只处理集合子集，最终回答仍宣称全部验证。
2. **Goal evidence**：evidence 可以把 action 自带的期望值与实际写入值放在同一来源比较，也可以把 read/list 的成功绑定到 mutation/aggregate criterion；因此无法检测模型是否使用了真实输入、是否覆盖完整集合。
3. **Task postcondition**：Task 与 Action 没有最小语义一致性。Create/aggregate/verify Task 可以执行 read，读取多文件 Task只能执行一个动作，已满足目标后的“verify/finish”又制造额外 mutation。
4. **Action commitment**：10 题在这里因常见 function 外壳、额外字段、参数名或路径失败；另有多题格式合法但工具/参数语义错误。透明格式层只能解决前者，不能修复后者。
5. **Frontier continuation**：5 题完成观察层后无法输出 canonical obligation batch；说明 Round52 只是限制 initial plan，并未建立可靠的 observation→next-task 协议。
6. **Initial planning**：53 题最早失败。RWKV 强烈倾向输出完整 conventional DAG，即便两次明确要求 deps 全空；硬拒绝把其中本来正确的 read/list 第一层也一起消灭。这是 Round52 相对 Round46 净丢失 28 Strict 的直接主因。

## 结构结论与下一步

Round52 的因果目标是正确的：未观察结果不应固化为未来参数。但实现方式错误。**“单层因果执行”不能等同于“整批必须无依赖”**。模型给出的依赖本身常常是正确结构信息，真正危险的是依赖完成后仍把旧描述当成已 grounded 的可执行动作。

下一步应回到已上传 Round46，并把变量移到更靠近执行的位置：保留 RWKV 输出的完整 DAG；只有 ready Task 才进入动作请求；动作请求必须以最新 dependency observations 为权威输入，并把原 Task 描述标为未验证意图。若 Task 的动作无法从当前 observations 具体化，应由 RWKV 继续观察或重规划，而不是 Controller 选取/删改 Task。与此同时，完成证据需要独立验证 provenance、集合 coverage 和目标 artifact，不能用模型写入时的 expected 值证明同一写入正确。

候选实验必须拆开预注册：

1. 先验证“ready 时 RWKV 重新 grounding Task 意图”是否保住 Round46 的正常 DAG，同时减少猜路径/占位符；不改 evidence。
2. 再独立验证 provenance/collection evidence，使 source→derived、listing→members、required artifacts 有可追溯闭包；不由规则计算答案。
3. 格式层仅登记高频、单义、冲突可拒绝的 wire envelope；不得借格式转换修正工具、参数值或 Task 含义。

这三项都保留 RWKV 的 Task、Action、参数、完成判断与最终答案决策权，Controller 只负责协议、状态和证据完整性。
