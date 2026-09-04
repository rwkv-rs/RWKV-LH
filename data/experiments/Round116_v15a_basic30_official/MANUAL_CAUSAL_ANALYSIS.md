# Round116 v15-A Basic30 人工因果审计与停止决定

## 结论

Round116 v15-A 被正式拒绝。官方 Basic30 为 Strict `8/30`、External `8/30`、Agent
completed `28/30`、FP `20`、FN `0`。它只保留 Round46 的 `6/24` 个 Basic 真阳性，
远低于预注册的 `23/24`。按停止规则，不运行 confirmatory、collection 或 full E2E-90，
也不在本轮源码上叠加局部 gate/reviewer 补丁。

本轮不是端点故障：30 题均产生完整审计，Final `30/30` 非空且与 raw RWKV 输出一致，
运行期间没有 SSH forward/模型服务中断。冻结源码、测试和数据哈希在运行后复核仍全部
一致。因此 `8/30` 是有效架构结果。

最重要的因果结论不是“one Action 错了”，而是当前实现把三个本应连续的东西拆成了
两个模型 lane 和两个语义提交：

```text
Goal lane 先写自然语言 Task
  -> Task lane 从一个泛化 lh_task_call 中再选 operation
  -> 任意成功 Action
  -> Task lane 再判断 lh_task_done
  -> Goal lane把自然语言 completion_claim 当作已提交进度
  -> Goal lane再调用两次 lh_goal_done
```

在 20 个 FP 中，RWKV 的首次错误通常确实是“选了错误的 Action”或“错误地说 Task
done”；Controller 没有篡改模型参数或答案。但架构把一次与 Task 目标无关的成功读取
升级成 `committed completion_claim`，再将它传播给 Goal lane，形成系统性放大。正确
整改不是让 Controller 从 Task 文本猜工具或答案，而是取消这条虚假的语义事实：ledger
只登记真实 Action/Observation，不登记为权威事实的自然语言 Task 完成声明。

## 固定指标

| 指标 | Round46 Basic30 | Round116 v15-A | 判断 |
| --- | ---: | ---: | --- |
| Strict | 24/30 | 8/30 | 失败 |
| External | 24/30 | 8/30 | 失败 |
| Agent completed | 25/30 | 28/30 | 完成声明增加但质量下降 |
| FP | 1 | 20 | 失败 |
| FN | 0 | 0 | 通过但不足以抵消 FP |
| 模型请求 | 474 | 408 | 下降 13.92%，不是质量收益 |
| Tasks | 129 | 97 | 下降，但错误完成更多 |
| Attempts | 128 | 112 | 下降，但错误完成更多 |
| prompt tokens | 919,718 | 1,224,367 | 增至 1.331 倍 |
| 平均 prompt tokens/request | 1,940.33 | 3,000.90 | 增至 1.547 倍 |
| paired-only artifact similarity | 0.984508565952 / 39 | 0.910152126283 / 20 | 失败 |
| missing-zero artifact similarity | 0.959895851803 / 40 | 0.455076063142 / 40 | 失败 |
| raw Final 非空/一致 | Round46 25/25 | 30/30 | 输出直通通过 |

相似度预注册存在一个必须公开修正的问题：门槛 `0.984508565952` 是 Round46 旧分析器
“只统计具有 actual/target 的 39 项”的 paired-only 值；Round116 协议又新增“缺失
expected artifact 记 0”，但未同步重算 Round46 分母。按新规则把四类可配对验收
`file_content/json_equals/json_exact_keys/directory_file_set` 固定为 40 项，Round46 基线应为
`0.959895851803`，Round116 为 `0.455076063142`。两种口径下 Round116 都失败，所以不
影响停止决定；下一轮必须在运行前只保留后一种版本化口径。

Round46 真阳性保留：B01、B05、B11、B18、B20、B26，共 `6/24`。丢失：B02、B03、
B06、B07、B08、B09、B10、B12、B13、B14、B15、B16、B17、B19、B21、B24、B25、
B28，共 18 题。新增通过 B04、B29；两轮都失败 B22、B23、B27、B30。

## 30 题逐条后向归因

下表从最终验收向前追到首次偏离，再记录后续放大。这里的“RWKV 首错”表示原始模型
输出先偏离；“架构放大”表示没有修改模型输出，但协议把偏离升级为错误完成、循环或
阻塞。

| 题目 | 结果 | 首次偏离 | 后续放大与根因 |
| --- | --- | --- | --- |
| B01 | PASS | 无 | 单个 `write_file` Task 与 Action 一致，是 v15-A 理想路径。 |
| B02 | FP | Goal 正确建立写 report Task，但 Task lane 又选 `read_file(input.txt)` | 读取成功后 RWKV 调 `lh_task_done`；Controller 的机械 readiness 只要求“有 Observation”，遂把写 Task 提交。验证 Task再次读 input，Goal 两次 `lh_goal_done`，report.json 从未创建。Round46 在同一 Observation 后通过 operation-specific `write_json` 一次写对。 |
| B03 | FP | 读完 config 后 Goal 首次给出正确写 Task，但 `after=[T1-A1-R1]` 被依赖协议拒绝 | 结构纠错回合把语义改成再次读取；Controller只锁函数名、不可能锁 Task 语义。随后形成 14 个 `read_file(config.json)` Task链，每次都被提交，最终 Goal完成。格式摩擦是首个放大点，变化的 `after` 又绕过同构进度检测。 |
| B04 | PASS，含潜在缺陷 | 生产动作全部正确 | 最后的“验证”Task没有执行验证 Action，并先输出旧 Task id；由于产物已正确，外部验收仍过。它证明结果正确，但不证明 completion spine 正确。 |
| B05 | PASS | `remove_line` 最初两次缺参数，第三次成功 | 透明纠错最终保留 RWKV 显式参数，产物正确；没有复现冗余下游 blocked。仍有 3 次格式拒绝，接口摩擦存在。 |
| B06 | FP | Goal 把“读 part_a 和 part_b”放入一个只允许一次成功 Action 的 Task；Task只读 part_a | 第二次读取被 one-success boundary 拒绝，RWKV仍完成 Task；写 Task只见 part_a，输出 `A---A`。根因始于 Task 原子性没有被结构表达。 |
| B07 | FP | 写 endpoint Task 选择再次 `read_file(mode.txt)` | 读取成功即被提交为写 Task完成；endpoint.txt 不存在，Goal仍完成。 |
| B08 | FP | Goal 把计算摘要、写 manifest、验证全部合成一个 Task；Task先 `list_directory` | 列目录成功后后续真实 Action被 one-success boundary 拒绝，RWKV完成整个 Task；manifest 不存在。 |
| B09 | FP | “读 scores.csv”Task选择 `list_directory` 而非读内容 | 文件名观察被提交为内容已读，Goal直接结束；stats.json 不存在。 |
| B10 | FP | 实现 Task再次读取 slug.py，没有写入；测试 Task先运行失败，随后在同一 Task用 `replace_text` | `replace_text` 是该 revision 第一个成功 Action，边界强制进入 done，测试没有重跑；外部测试仍失败。失败 Action后允许任意不同 Action、成功后又强制结束，导致“修复”和“验证”落在错误 Task边界。 |
| B11 | PASS，脆弱 | Goal/Task连续四次重复读取 name.txt | 第五个 Task才写出正确结果。依赖观察最终被模型利用，但重复链说明 Goal progress 不稳定；本题靠业务值简单而通过。 |
| B12 | FP | 读完 numbers 后，Goal 生成“再次读+计算+写”的非原子 Task；Task再次读文件 | 成功读被当作 stats.json 已完成，文件不存在。Round46 相同数字 Observation 后直接 `write_json`。 |
| B13 | BLOCKED | RWKV 首个 `read_file` 参数为 `path='.'` | invalid 后重复同一 Action；unchanged guard触发。Goal提出相同自然语言读取 Task会被 no-progress guard拒绝，但这里真正需要改变的是 Action 参数而非 Task objective。5 次替换拒绝后 blocked。模型首错真实，恢复协议把可修复调用变成终局。 |
| B14 | FP | Goal 把两文件读取合并为一个 Task，Task只读 left | 后续“创建”Task又读 left；“验证”Task在首次 not_found 后写出 `left--left`。两处错误 Task完成共同放大，right 从未进入写入上下文。 |
| B15 | FP | 创建 colors.json Task再次 `read_file(colors.txt)` | 成功读取被提交为创建完成；文件不存在。此前 `after` artifact ref 还触发一次 Goal协议拒绝。 |
| B16 | FP | normalize Task 和 verify Task都重复读取原 app.env | 没有任何 mutation，三个读 Task仍全部 committed；Final宣称精确新内容。 |
| B17 | FP | 创建 active_users Task选择 `read_json(users.json)` | 验证 Task再次读 users；active_users.json 不存在。artifact/Attempt ref 依赖与重复 Task纠错增加了语义漂移。 |
| B18 | PASS | 前两个 Task重复读取 price.json，但第三个 Task正确 `write_json` | 写入与后续 `read_json(total.json)` 均正确。说明依赖事实在短、清晰链上可以被当前模型利用，但需要额外幸运回合。 |
| B19 | FP | 摘要 Task只 `list_directory` | 目录元数据被提交为 SHA256 已知，后续 Action被边界拒绝；Final幻称 manifest 已写。与 B08 同源。 |
| B20 | PASS | 无关键偏离 | 读实现、读测试、写代码、运行测试四个 Task与四个 Action一致，是当前架构少数完整因果链。 |
| B21 | FP | 创建 category_totals Task再次读 items.csv | 读取被提交为创建完成；多次 Goal依赖/重复结构拒绝后仍错误结束，文件不存在。 |
| B22 | FP | Goal 把读、转换、写、验收合成一个 Task；首个 Action是 `list_directory` | 后续 `read_file(max_bytes=...)`先因参数格式拒绝，再因 one-success boundary不能执行；TASKS.md 不存在。 |
| B23 | FP | fallback 判断使用 `read_file(primary)`，只能证明文本可读，不能证明 JSON有效 | 虽随后读到正确 backup，选择/创建 Task又反复读 primary，验证 Task读 backup，从未写 selected.json。模型也在 Final错误声称选择 primary；接口没有形成“解析失败→分支→写入”的单一连续状态。 |
| B24 | FP | 变换并写 sorted.log 的 Task再次读取 log.txt | 成功读被提交为输出完成，sorted.log 不存在；一次 artifact ref依赖纠错先制造额外漂移。 |
| B25 | FP | Goal 把读两个 JSON、合并、写、验证合成一个 Task；首个 Action只列目录 | 目录列表被提交为整个目标完成；settings.json 不存在。 |
| B26 | PASS，含潜在缺陷 | 三个 producer Action正确 | verify Task没有验证，而是重复写 c.txt；操作幂等且值正确，所以外部通过。说明“验证任务可以执行 mutation 后自称完成”的结构缺陷仍在。 |
| B27 | FP | replace Task再次读取 service.conf | verify Task再读未修改文件，仍 `lh_task_done`；无 mutation，v1 全部保留。 |
| B28 | FP | 写 metrics.json Task再次读取 metrics.txt | 读成功被提交为写完成；文件不存在。与 B02/B12/B21 同源。 |
| B29 | PASS，含潜在缺陷 | copy 与 manifest producer均正确 | verify Task没有执行 Action且出现旧 Task id调用；外部产物已正确所以通过。 |
| B30 | BLOCKED | edit names.py Task选择再次读取 names.py，显示的仍是 `NotImplementedError`，却被完成 | 测试 Task在未修改代码上连续失败 3 次；Goal连续 6 次用同构测试 Task替换，supersede 每次重置局部 attempt budget，共 21 次失败 Action。长 recovery prompt随后产生截断 JSON并 blocked。模型没有根据失败回到 edit 是语义错；预算跨 replacement 不累计、失败事实越滚越长是架构放大。 |

## 跨题共同链路

### 1. 泛化 wrapper 削弱了弱模型的工具接口

当前只给 Task lane 注册一个 `lh_task_call`，其中 `operation_args` 只是无约束 object；每个
操作的 required/optional arguments 作为 `operation_catalog` 数据再次注入。Round46 则把
`write_json/read_file/run_command/...` 作为独立工具及精确 JSON schema直接暴露给模型。

这不是“selector 与直接调用并存”的问题，而是当前 wrapper 重新引入了隐式 selector：
模型要先在字符串 enum/catalog 中选 operation，再自行恢复该 operation 的 schema。B02、
B07、B12、B15、B16、B17、B21、B24、B27、B28 的 objective 已指向 producer/mutation，
Task lane仍高频回退到前一个 read operation。Round46 同题在相同依赖 Observation 后可以
直接生成 operation-specific `write_json/write_file`，是最强的历史对照证据。

代码入口：`rwkv_lh/model_io.py:164-190` 和 `rwkv_lh/model.py:1020-1058`。

### 2. “自然语言 Task”与“一次 Action”没有同一个结构所有者

Goal lane只能用 `objective/done_when/after` 描述原子性，schema无法机械表达一个 Task
包含几个 Action。B06/B14 的“读两个文件”，B08/B22/B25 的完整端到端目标，B12 的
“读+计算+写”都被接受为 ordinary Task。Controller不能通过自然语言推断这些 Task应拆分，
否则就是替 RWKV作语义决定；因此 one-success boundary 与 Task proposal 天生可能冲突。

代码入口：`rwkv_lh/model_io.py:112-152`。

### 3. 任意 Observation 被提升为 Task 完成事实

`_task_completion_readiness` 只要求 current/dependency refs非空，然后把语义决定交给同一
Task lane RWKV。这一原则本身避免 Controller作弊，但随后 runtime把 RWKV的
`lh_task_done` 写成 `postcondition committed`，Goal projection再把模型写的
`completion_claim` 与真实 ActionResult并列。B02 中“创建 report.json”的真实 Action是读
input.txt，Goal仍看到已 committed 的“report.json exists”声明。

代码入口：`rwkv_lh/controller.py:2114-2160`。不能用 operation/objective 文本匹配 gate修复；
那会让规则替模型选择业务工具。应删除权威的自然语言 Task completion fact，只保留真实
Action/Observation。

### 4. 多 lane prompt replay让正确 Observation与下一决定分离

Task assignment确实含完整 dependency observations，不是“数据没传进去”。问题是它们被
重新序列化进一个包含长 operation catalog 的新 Task lane；Goal lane又只接收投影后的
Task/commit对象。Round116 虽比 Round46 少 66 次请求，总 prompt token反而多 33.1%，
平均请求长 54.7%。当前后端明确只有 `prompt_replay`，不存在 native recurrent state。

代码入口：`rwkv_lh/model.py:1020-1058`；能力证据见 `runtime_doctor.json`。

### 5. 同一弱模型重复审核没有增加新事实

Task Action后还需 `lh_task_done`；Goal完成又必须相同 evidence digest下连续两次
`lh_goal_done`。B02 表明两次 Goal review都接受了不存在的 report.json。没有新 Observation
的重复判断只是增加上下文与一次自我确认，不是独立证据。

代码入口：`rwkv_lh/controller.py:435-497`。

### 6. 恢复预算按 Task revision而非因果动作累计

B13 的 unchanged guard错误要求自然语言 replacement结构改变；B30 的 supersede 则让同一
测试动作获得 7 个 Task revision、21 次执行。两者方向相反，但根因相同：恢复预算绑定在
可被重新命名/替换的 Task对象，而不是稳定的 Action+arguments+artifact revision因果键。

## 下一架构决策：v15-A 回退，候选改为 Single RWKV Action Spine

下一候选不应恢复 Round46 的 Goal解析、criterion、静态 DAG、reviewer 或证据类别；只借回
Round46 已被 Basic30 验证的 operation-specific direct tools 和紧凑 execution capsule。

候选链路：

```text
verbatim user request
  -> 单一 RWKV session选择一个直接注册工具或 final_answer
  -> Harness原样执行显式参数
  -> append exact typed Observation + artifact revision
  -> 回到同一 RWKV session
```

具体边界：

1. 一个 run 只有一个语义 lane；不再有 Goal lane、Task lane、completion review lane之间的
   语义投影。当前仍诚实标注 prompt replay，后端支持 native state后再切换 transport。
2. 模型边界直接注册 `read_file`、`write_json`、`run_command` 等 operation-specific schema，
   加一个 `final_answer`。不注册 selector，不注册泛化 `lh_task_call(operation, object)`。
3. 简单格式转换层只把常见 function/name/tool 与 params/arguments/function_args envelope搬运
   到 canonical call；不补 operation、path、value、答案或验收事实。
4. 每次直接 Action自动获得单调 action id、ActionResult、artifact revision。若仍需要 UI
   的 Task展示，Task只是该模型 Action的审计视图，不是第二个模型必须完成的语义对象。
5. 删除 `lh_task_done`、自然语言 `completion_claim committed` 和双 `lh_goal_done`。ledger的
   权威事实只有真实操作、显式参数、输出、错误、workspace/artifact版本；RWKV通过下一
   Action继续，或通过 `final_answer`结束。
6. 失败返回同一 session。retry/no-progress budget使用稳定的
   `(operation, explicit arguments, target artifact revision, failure fingerprint)`，跨重命名和
   恢复累计；不要求自然语言 Task objective改变。
7. Basic30 通过后才加入 workset/member ledger。计划可作为 RWKV非权威 scratchpad，但不
   作为 Controller gate，也不创建第二套进度状态机。

这个候选同时消除本轮两个不可兼容前提：不再要求弱模型先写一个“恰好等于一次 Action”
的自然语言 Task，也不再要求它在另一个 session中从泛化 wrapper重新选择该 Action。它仍
完全由 RWKV决定做什么、参数是什么、何时结束；Controller不改写最终答案，也不利用隐藏
验收作在线决策。

## 下一轮预注册要求

- 新建独立版本/源码清单，不修改 Round116结果。
- 先做 direct-tool wire、raw/normalized audit、artifact revision、failure budget、Final直通的
  offline回归；随后仍直接跑固定 Basic30，不做单题调参。
- 主门槛保持 Strict `>=24/30`、FP `<=1`、FN `<=1`、Round46 TP保留 `>=23/24`。
- 相似度只使用修正后的 missing-zero 40项口径，Round46基线
  `0.959895851803`；不得再混用 paired-only门槛。
- 报告每题首次 Action偏离、下游放大、prompt tokens和 artifact revision；如果 Basic失败，
  再次停止，不进入 collection/full90。

## 审计材料

- 冻结协议：`data/experiments/Round116_V15A_ATOMIC_CAUSAL_TASK_SPINE_PROTOCOL.md`
- 源码清单：`data/experiments/Round116_v15a_source_manifest.json`
- 官方报告：`data/experiments/Round116_v15a_basic30_official/REPORT.md`
- 每题原始链路：`cases/<id>/audit.json`、`causal_ledger.json`、`event_log.json`、
  `model_trace.json`、`state_timeline.json.gz`
- 历史对照：`data/experiments/Round46_full90_uploaded_baseline/`

本报告的脚本只用于把原始 JSON压缩为可读链路；每一题的首次偏离与放大原因均由上述
原始 Action/Observation、模型 raw output和外部验收逐条人工复核，不是按分数自动生成。
