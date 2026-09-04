# Round118 v17 Full90 人工逐题因果分析

日期：2026-08-15

状态：完整 90 题诊断已经结束；本文件是运行后人工分析，不参与 RWKV 决策，不修改冻结评价。

## 一、结论

Round118 v17 的完整结果是 Strict `25/90`、External `27/90`、Agent completed
`60/90`、FP `35`、FN `2`。它明显恢复了 Round101 被结构 gate 阻塞的能力，但没有超过
Round46：相对 Round101 Strict `+13`、FN `-7`；相对 Round46 Strict `-6`、FP `+11`、
FN `+1`。

因此，v17 证明了“单 RWKV、直接注册工具、无 Task DAG、无 reviewer、单一 causal event
authority”是正确的清理方向，但当前的直接行动脊柱过于无状态：它能让 RWKV 行动，却不能稳定
保留当前行动意图、集合覆盖、重复观察和未完成输出义务。结果是 blocked 减少，但大量错误被更快
提交为完成。

下一轮不能恢复旧 Task DAG、reviewer 或语义 completion gate。应在当前单脊柱上增加一个统一、
RWKV 自己填写的 step contract，并从完整 causal ledger 机械生成进度投影；Controller 仍不生成
业务答案、不改工具参数、不判断 Goal 是否完成。

## 二、固定结果与完整性

| 版本 | Strict | External | Agent | FP | FN | Requests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Round46 历史最佳 | 31 | 32 | 55 | 24 | 1 | 1622 |
| Round101 退化基线 | 12 | 21 | 32 | 20 | 9 | 2167 |
| **Round118 v17 Full90** | **25** | **27** | **60** | **35** | **2** | **1952** |

| 难度 | Strict | External | Agent | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| Basic | 19/30 | 20/30 | 28/30 | 9 | 1 |
| Medium | 5/30 | 6/30 | 20/30 | 15 | 1 |
| Hard（H01–H18 + LH01–LH12） | 1/30 | 1/30 | 12/30 | 11 | 0 |

完整性指标：

- 1557/1557 Action 都有终态和完整 ActionResult；没有 active action 残留。
- 90/90 RunState 可从 immutable causal events 重建；共 7714 个 causal events、129 次 rollover。
- 冻结源码、数据和原协议运行后复核为 `47/47` hash 一致；`git diff --check` 通过。
- Final 非空且与 raw RWKV `final_answer.text` 相等的只有 `87/90`。M16、M17、M21 在模型生成
  连接结果未知时异常逸出，状态仍为 `running`，Final 为空。这违反“Agent 总要回答”的系统要求。
- 选定的 128 项产物检查 missing-zero byte-5gram similarity 为 `0.622786691168`；Round46
  报告中的可配对产物相似度为 `0.861638909388`。两者不是 Strict 替代指标，但方向一致。
- 总 prompt tokens 为 `16,884,399`，是 Round46 `3,502,798` 的 `4.82x`；平均每请求约
  8650 tokens，是 Round46 约 2160 的 `4.00x`。
- 18 个 action_count >= 20 的用例消耗 1170/1557（75.1%）Action；其中 10 个
  action_count >= 50 的用例消耗 929/1557（59.7%）Action。长尾循环已经影响质量，不只是效率。

### 运行协议记录修正

预注册文件把数据集简称写成 B01–B30、M01–M30、H01–H30。冻结 manifest 的真实 Hard 组是
H01–H18 加 LH01–LH12；runner `--suite all` 的实际顺序是 core30、LH12、extension48，即
B01–B10/M01–M10/H01–H10、LH01–LH12、B11–B30/M11–M30/H11–H18。
运行确实覆盖固定 90/90，未漏题；这里保留原协议文本，并记录描述错误，不在运行后重写预注册。

## 三、与历史最佳的整体比较

Round118 只保住 Round46 的 31 个 TP 中 18 个，新增 7 个 TP，同时丢失 13 个：

- 新增：B23、B27、B29、B30、M02、M07、M20。直接工具调用、简单协议归一和 uv Python
  让 fallback、replace、copy 和五个代码/JSON任务恢复。
- 丢失：B05、B08、B11、B12、B14、B16、B17、B18、B24、M03、M19、M24、LH04。
  这些并非都更难；多数是精确格式、一次后续核对、Task-local focus 或失败后纠正能力丢失。

Round118 相对 Round101 严格通过增加 15 题、丢失 2 题，说明去掉旧 evidence gate/reviewer
总体有效；但 Agent completed 从 32 增至 60，而真实 External 只从 21 增至 27，新增完成主要流入
FP。与 Round46 相比 Agent completed 多 5、External 少 5，更直接证明当前完成边界过松而不是整体
能力超过最佳。

同一 v17 源码的独立 Basic30 是 21/30，Full90 中 Basic 是 19/30。B08/B12/B18 从独立运行
TP 变为 Full90 失败，只有 B10 从失败变为 TP。这种净两题和四题翻转说明一次小样本不能作为架构
结论，也说明下一版通过后还需要冻结的第二次 Full90 确认。

## 四、逐题反向因果分析

标记说明：`TP` 为 Strict pass；`FP` 为 RWKV 宣布完成但外部失败；`FN` 为外部正确但 Agent
未完成；`TN` 为两者都未完成。每行先从最终外部事实向前找到首次偏离，再记录后续放大。

### 4.1 Basic 30

| 题目 | 结果 | 从外部事实反向定位的首因与放大链 |
| --- | --- | --- |
| B01 | TP | 精确写入并读回 greeting；链路正确。 |
| B02 | TP | 先读 input，再正确派生 doubled_count 并写 JSON；一次 `max_bytes` 拒绝后按 schema 恢复。 |
| B03 | TP | 读取完整 config、保留无关字段、写入并读回；链路正确。 |
| B04 | FP | 已读到正确源字节；首次偏离是把 `archive/2026/source.txt` 写成 `archive/source.txt`，随后 manifest 也绑定错误路径；两次读回只能证明自产错误，Final 仍称成功。 |
| B05 | FP | 已读到完整 env；`replace_text` 只删除文字而留下空行，没有执行请求中的最终核对；动作成功被直接等同于精确格式完成。 |
| B06 | TP | 两个输入均被读取，组合内容和分隔线精确。 |
| B07 | TP | 观察 production 后选择正确分支，未创建 alternate。 |
| B08 | FN | manifest 与 SHA256 已完全正确；RWKV 随后连续 12 次调用未注册 `verify_checksum`，最终 interrupted。首因是通用 digest/verify 能力不可达，不是业务答案错误。 |
| B09 | TP | CSV 读取、行数/总和/平均值均正确。 |
| B10 | TP | 读取源码与测试、修复、真实 unittest 成功。 |
| B11 | FP | 已观察首尾空白；写出时保留了空白，仅改大小写；Final 未依据实际产物纠正。 |
| B12 | TN | 首次 read_file 已得到全部整数；RWKV 随后退化成对文本连续 5 次 `read_json`，稳定 JSONDecodeError 后终止，未创建输出。 |
| B13 | TP | 嵌套更新正确且无关字段保留。 |
| B14 | FP | 两个源均正确读取；写入时在分隔线两侧增加空行，外部精确字节失败，Final 仍称 exact。 |
| B15 | TP | 去重和 first-seen 顺序正确。 |
| B16 | FP | 读取后只修改 MODE，未移除注释和空行；成功 write 被当成完整 normalize。 |
| B17 | FP | 过滤 active 正确，但没有按姓名排序；自产 JSON 未再次核对请求约束。 |
| B18 | FP | 金额计算正确，但把输入 `discount_rate` 额外写入要求“exactly”三字段的输出。 |
| B19 | TP | SHA256 manifest 正确。 |
| B20 | TP | 实现 is_even 并通过真实测试。 |
| B21 | TP | CSV 分类汇总正确。 |
| B22 | FP | 把 unchecked Markdown item 写成普通 `- item`，遗漏 `[ ]`。 |
| B23 | TP | primary 解析失败后使用 backup，source 路径和值都正确。 |
| B24 | FP | 已读日志，但直接原样复制到 sorted.log，没有去重或排序。 |
| B25 | TP | 两个 JSON 的嵌套 merge 正确。 |
| B26 | TP | 三个文件、目录结构和额外文件约束均满足。 |
| B27 | TP | `count/all` 简单转换层生效，所有文本替换正确。 |
| B28 | TP | key=value 到整数 JSON 正确。 |
| B29 | TP | 源字节、备份字节和 manifest 均正确；相对 Round46 的同题值传递错误已恢复。 |
| B30 | TP | 代码实现和 unittest 均正确。 |

Basic 的 9 个 FP 都可以追到 RWKV 首次写入值或精确格式错误；Controller 没有改值。架构缺陷在于
没有保持“当前 step 的 done_when”和后续实际观察，导致弱模型把一次成功 mutation 当成全部义务完成。
B08 是明确接口 FN；B12 是正确 observation 后错误换工具并被重复失败放大。

### 4.2 Medium 30

| 题目 | 结果 | 从外部事实反向定位的首因与放大链 |
| --- | --- | --- |
| M01 | TN | 三个 service 文件实际迁移正确；首次业务偏离是 summary 写成嵌套 `{name,version}` 而非 name→version。之后连续 12 次把 read 参数用于 `check_command`，使本可局部修正的错误转成 interrupted。 |
| M02 | TP | 修复 weighted_total 并通过完整测试。 |
| M03 | FP | 迁移主体正确，但把应删除的 `legacy_note` 保留为 null；完成没有绑定“字段不存在”。 |
| M04 | FP | JSON 正确；Markdown 标题拆成两行，外部精确格式失败。 |
| M05 | TP | 在噪声中选择权威 requirements，并生成准确三行计划。 |
| M06 | TN | 读取 selection 后又读取未选 beta；只写 manifest 且包含 beta，从未复制 alpha/gamma。其后 12 次错误 `check_command` 参数放大，最终声称文件已复制。 |
| M07 | TP | 递归 merge 正确；这是 v17 相对 Round46 的真实新增能力。 |
| M08 | FP | 数据值正确，但空行、web/worker 排序和结尾换行均错误。 |
| M09 | TN | 首次严重偏离是用实现模板覆盖 consumer.py 和 `__init__.py`，并破坏测试文件语义；之后重复运行失败测试，没有回到源 observation。 |
| M10 | FP* | resilient.txt 的内容和重试行为正确；唯一失败是旧架构专属 `replan_applied` event_min_count。冻结 Strict 仍记 FP，但这是评分 schema 漂移，不是当前任务产物错误。 |
| M11 | TN | 四个 service 迁移都正确；summary 用 records 数组而非 name→port。后续 grep 期望值反复翻转并循环，正确主体工作未能转成部分修复。 |
| M12 | TP | 两个函数修复正确并通过测试。 |
| M13 | FP | 把 CSV header 计入 row_count、north revenue 算成 37.5、by_region 自创嵌套 schema；纯模型计算/结构错误。 |
| M14 | FP | changes 未排序，Markdown 标题和空行格式也不符合要求。 |
| M15 | FP | 三个文件都已观察；输出使用 `entries` 而非 `files`、路径多 `docs/` 前缀，并把 a.txt 两行算成一行。 |
| M16 | TN | 对 01–05 的 primary/fallback 实际已观察完整；随后丢失显式集合边界，继续扫描 06–15，未 synthesis。最后一次生成连接 outcome unknown，Run 留在 running 且 Final 为空。 |
| M17 | TN | 更新时遗漏 `compatible=true`，matrix 内容和排序也错；使用 `grep api=v2` 检查 JSON 导致 22 次相同 nonzero 观察。最后网络 outcome unknown，未落终态。 |
| M18 | FP | 三个 digest 本身正确；结果多一层 `digest_map`，键错误保留 `inputs/` 前缀。 |
| M19 | FP | 201 被漏掉，500/503 计数和 `/items` 次数错误；纯模型聚合错误。 |
| M20 | TP | parser 修复并通过测试。 |
| M21 | TN | 两个源已正确读取；RWKV 连续使用 write_json 不支持的 `updates`，没有形成完整 records 对象。第五次拒绝后连接 outcome unknown，状态 running、Final 空。 |
| M22 | FP | 读取 config/policy/request 后仍把 debug/owner 应用进 config，并自创多余字段；政策语义判断错误。 |
| M23 | FP | 把完整 build_plan 原样写到 manifest，只创建一个文件；三个声明文件和正确文件列表都缺失。 |
| M24 | TN | 首次代码错误是 tuple 存储 `(priority,task_id)` 却用 `t[0]==task_id` 查重。之后相同测试失败出现 50 次，但每次 workspace/revision 变化产生新的 failure_key（50 个 key、每个 count=1），最终 103 Actions 后中断。 |
| M25 | FP | 额外写 `# CHANGELOG.md`，且 1.2.0 内仍把 fix 放在 add 前；请求中的精确排序没有留到最终 write。 |
| M26 | FP | reason 内容基本正确，但使用 `reason_codes`，并完全遗漏 valid records 数组。 |
| M27 | FP | 拓扑依赖合法，但 available tie-break 错，把 web 放在 docs 前；确定性排序规则丢失。 |
| M28 | TN | 正确识别应移动的日志，但连续 12 次请求未注册 `move_file`；没有执行 copy+delete，也没有完成 report。属于标准文件操作能力缺口。 |
| M29 | FP | hello 没有采用 locale 值，并把 translations 展平到顶层；源观察到写值之间发生语义丢失。 |
| M30 | FN | config、migration_report 和外部 verify 全部正确；连续 12 次使用常见 `timeout_ms` 而非 `timeout` 被拒，最终 interrupted。明确是简单接口转换缺口。 |

`M10*` 不修改官方计分。若只做架构中立的任务质量诊断，它应算完成；同类还有 H09。把两题
加回后，诊断 Strict 为 27/90，仍低于 Round46 31/90。B08/M30 外部正确但 Agent 未完成仍是
真实 FN，不能一并“调整掉”。

### 4.3 Hard 18

| 题目 | 结果 | 从外部事实反向定位的首因与放大链 |
| --- | --- | --- |
| H01 | FP | summary artifact 正确，但 load_records 保留数字字符串；测试明确暴露差异。RWKV 连续重写同一错误实现并把失败称为测试误报，Final 与最后 verifier 事实冲突。 |
| H02 | TN | 已顺序读取多个 shard，随后重新 list 并从 shard01 开始；没有 aggregate。缺少 discovered/read member ledger。 |
| H03 | FP | 只 list 一次；read_file 的 `max_bytes` 被拒后模型直接声称工具不可用并 Final，六阶段一个未创建。 |
| H04 | TP | 最终安全产物正确、无越界；但在写入前完全相同的 list_directory 成功观察重复 33 次。Strict pass 掩盖了严重状态循环。 |
| H05 | TN | 50 文件已由 list 暴露，实际只读到 doc09 后重启；随后格式退化并幻称 doc41–50 为 priority，未创建 summary。 |
| H06 | FP | 三个环境迁移都正确；report 额外加入 schema_version 和 timestamp，违反 exact object。 |
| H07 | TN | 读取正确测试后却用 write_json 把 Python 测试改成 JSON；随后 0 tests/exit5 重复，未修 queue，也无 VERIFIED。 |
| H08 | FP | 去重顺序正确，但 ledger schema 自创 first_seen entries，遗漏要求的 count/event_ids。 |
| H09 | FP* | fallback source 和 selected.json 完全正确；唯一失败是旧 `action_returned` event_min_count。属于评分事件名漂移。 |
| H10 | TN | CSV、policy、verifier 已提供精确期望；模型不创建 output，反复读取不存在的两个 release 文件，稳定 not_found 后终止。 |
| H11 | TN | release.json 碰巧正确，但 pipeline build 始终对 list 调用 total；同一 stage4 traceback 重复 68 次左右，72 次成功写文件，153 Actions 后中断。 |
| H12 | TN | 15 个 shard 曾全部读取一遍；没有形成“15/15 已覆盖”事实，rollover 后从 shard01 重读，63 Actions 后仍无 aggregate。 |
| H13 | TN | 读取到 doc11 后重新 list/from doc01；没有任一 phase checkpoint 或 final summary，随后协议退化。 |
| H14 | TN | root、3 manifest、5 data 文件都曾完整读取；没有 seal/reduce 转移，重复读取 manifest/data，78 Actions 后 global_index 仍不存在。 |
| H15 | TN | 已读 requirements、三个 stub 和测试；却反复 read 不存在的 DESIGN/README/report/manifest，而不是进入实现阶段。多输出义务没有持久 focus。 |
| H16 | TN | 把 dotted change keys 平铺进两个 config，破坏原 schema；随后 10 次调用未注册 `check_invariants` 而不是通用 check_command，compensation 也未写。 |
| H17 | TN | ledger 写成错误数组 schema；验证命令 argv 只有 `-c`，被 bwrap 当选项，完全相同失败重复 7 次，resume 条件也未满足。 |
| H18 | TN | policy、CSV、validator（含精确预期）分别重复读取约 25 次；从未转入 write，Final 却声称四个产物都存在。 |

Hard 唯一 TP H04 自身也有 33 次相同成功观察，因此 1/30 不只是模型做不出复杂计算；架构没有
把重复事实、成员覆盖和阶段义务投影给 RWKV，造成“已读完却重新读”和“已看到精确 verifier 却不写”。

### 4.4 Long-horizon 12

| 题目 | 结果 | 从外部事实反向定位的首因与放大链 |
| --- | --- | --- |
| LH01 | FP | normalize/validate/price 已修，build_release 仍错误；同一 layer D 失败重复 4 次后模型宣布全部通过，release 文件不存在。 |
| LH02 | FP | 15 个 checkpoint 都写出，但每个多了 generated_by；写完 step15 后丢失 final/config.json 义务，直接完成。 |
| LH03 | TN | 3 manifest/5 data 已完整读取；之后目录 list 重复 118 次以上，单个 south list 48 次，189 Actions 后仍无 global_index。 |
| LH04 | FP | crash-after-effect 恢复和 completed-noop 都正确；业务 ledger 自创 count/total_amount per entry，遗漏顶层 count/total，故不是 Strict。 |
| LH05 | TN | 处理到 shard09，能为缺失 shard07 选择 fallback，却没有把 invalid shard04 作为 fallback，并在 04–09 循环；20-member 覆盖和输出均未完成。 |
| LH06 | FP | 权威源选择和越界防护正确；resolved JSON 遗漏 source、增加 metadata，EVIDENCE 未正确引用 approved path 且复述了不应出现的 injection 文件名。 |
| LH07 | TN | 八个 service 均被反复读取，前六各重复约 12 次；没有任一 mutation、report 或 verifier 成功，随后格式预算耗尽。 |
| LH08 | TN | request、policy、invariant 和三个 config 均已观察；一直回到读取阶段，未应用最高优先级 reserve=70，也无 compensation。 |
| LH09 | FP | create transient retry、query、update、409 replay、finalize 全部正确；api_result.json 自创多层审计 schema，而非要求的 `{resource,finalized}`。 |
| LH10 | FP | math 代码、测试和 README 正确；release_manifest 错把 test 文件纳入并遗漏 README digest。 |
| LH11 | TN | 第一阶段 important facts 已看到，但 list/artifact001 重启；未产生任一 phase checkpoint 或 memory_summary，协议在长上下文中退化。 |
| LH12 | TN | requirements、stub、tests 和 input 都反复读到；从未执行 write/patch，最终反而声称这些已存在的输入文件“缺失”。 |

LH native 为 `0/12`。这不是旧版本的 16-Task frontier 限制：当前直接工具已经能读取 15、40、
甚至递归集合。新瓶颈是读取事实无法变成跨 rollover 的覆盖表和下一阶段行动。

## 五、从后向前的共同放大链

### 5.1 Final/终止层

- 35 个 FP：`final_answer` 是 RWKV 自己的决定，Controller 没改文本，但当前投影没有把“最后 verifier
  nonzero”“要求的输出从未发生 mutation”“集合已经/尚未覆盖”压缩成稳定事实。模型因此把 action success、
  自产文件存在或纯口头计划当完成。
- M16/M17/M21 的 HTTP generation outcome unknown 未被 `run()` 捕获。`_terminal_output()` 只在正常
  loop break 后执行，所以三个状态保持 running、Final 为空；不是 transition budget 本身遗漏。
- 不能用 Controller 自动把 failed 改成正确答案。应持久化 transport-unknown，等待 endpoint 恢复后让同一
  RWKV 生成 terminal answer，并保证每条路径追加一个 terminal causal event。

### 5.2 恢复层

- 当前 failure key 包含完整 action arguments、target artifact revision 和 workspace digest。
  在 write→test 循环中，每次写会改变 revision/digest，即使测试 traceback 完全相同也形成新 key。
  M24 有 50 个 failure keys、每个最大 count=1，但相同失败 observation 重复 50 次；H11 同类失败
  重复 44 次以上。
- 成功 observation 没有重复计数。H04 同一 list 成功 33 次，LH03 单一路径 list 48 次，H11
  成功 write 72 次。成功循环不会消耗 failure budget，却最容易把 prompt 推入 rollover。
- 执行/idempotency identity 与 observation fingerprint 必须分开。前者继续包含完整 action/workspace；后者只对
  operation、显式 target/argv、outcome、exit/error/output 做稳定 digest，向 RWKV展示 exact repeat count。
  Controller 不提出修法，也不改变 verifier 结果。

### 5.3 状态/rollover 层

`LongHorizonModel._assignment()` 只生成 immutable request、当前 workspace manifest 和最近最多 12 条
Action。超过输入上限后，`_rollover_if_needed()` 尝试保留最后 12/8/4/2/0 条，旧 observation 从在线
投影消失。它没有：

- discovered member 与已读 member 的累计集合；
- 每个 path 的 first/latest observation 和内容 digest；
- 最后一个 command verifier 的稳定结果与重复次数；
- 当前 step 的 objective/done_when；
- 多输出任务中尚未执行的 RWKV-owned obligations。

这直接解释 H12/H14/LH03“全部读过后重读”、H13/LH11 分阶段重启、H15/LH12 一直观察不进入实现。
129 次 rollover 的审计本身正确，但“最后 N 条 transcript”不是 long-horizon working state。

### 5.4 行动意图层

v17 删除 Task DAG 和 reviewer 是正确的，但也删除了 Round46 有效的局部 Task→Action 因果绑定。
当前每轮只有 tool+params；模型不需要说明这个 Action 服务于哪个 immediate objective、看到什么事实后应换阶段。
因此出现：

- B12 已读文本后改用 read_json；
- H10/H15 读取尚未创建的输出；
- LH02 连续 15 次 checkpoint 后忘记 final config；
- M23 把计划文件当成 manifest；
- 35 个 FP 在一次成功 mutation 后直接 final。

不应恢复两套进度系统。更小的通用 contract 应与直接调用同一次生成，例如固定字段
`step={objective,done_when}` + `function` + `params`。step 完全由 RWKV 写，Controller 只登记和回显；
不生成 Task、不建依赖 DAG、不用 step 内容 gate Action 或 Final。

### 5.5 工具/协议层

- 66/90 用例出现至少一次协议拒绝，共 299 次；18 题耗尽 12 次预算，占 216 次拒绝。
- v17 已有 content→value、text→new、count="all"、shell=false 等简单转换；它们在 B27 等题有效。
- M30 的 `timeout_ms` 是常见单位接口，且业务产物完全正确；可增加透明的 milliseconds→seconds 转换并保存
  raw/normalized 值。这不是补答案。
- M28 缺少标准 move action；B08 缺少标准 file digest/verify action。为普通 Agent 增加通用文件移动和
  字节摘要能力是能力补全，不是用隐藏验收选答案。
- 不应为 H16 增加题目专属 `check_invariants`，也不应根据名字自动改选 check_command。题目脚本应通过通用
  argv command 执行；错误选工具仍由 RWKV负责。
- 大量 malformed envelope 出现在集合重读和 prompt 膨胀之后，是状态丢失的下游结果。继续增加格式别名
  不能修复首因。

### 5.6 评价数据层

M10 的 `replan_applied` 和 H09 的 `action_returned` 属于旧架构事件名。当前 v17 的等价可见事实由 immutable
causal events 和 action_finished/action_result 表达，因此两题业务结果正确却被判 External false。
LH02/LH11 也检查旧 `attempt_started`，但它们还有真实产物失败，不影响总 Strict 归类。

不得运行后改 Round118 结果。下一轮应把当前 E2E-90 v1 保留作历史对照，同时另行版本化一个架构中立的
v2：检查 observable behavior/causal property，不要求某个历史模块的事件名称。数据版本、摘要和生成方法
必须重新登记。

## 六、下一轮单一结构：v18 Causal Step + Progress Projection

这不是多个补丁并列，而是对一个缺口的两面修复：**让每次直接 Action 有当前意图，并让所有真实
Observation 在 rollover 后仍可见。**

### P0：先保证链路事实完整

1. **Terminal transaction**：捕获 generation outcome unknown；持久化 transport 状态，进行有界重连/重试；
   endpoint 恢复后只让 RWKV生成 `final_answer`。所有退出必须有 completed/interrupted/failed terminal event，
   不允许运行结果停在 running。禁止 Controller 合成用户答案。
2. **双 fingerprint**：保留现有 execution/idempotency identity；新增 stable observation fingerprint 和 exact
   success/failure repeat count。相同 traceback、相同 read/list 结果必须被 RWKV看见为“第 N 次相同事实”。
3. **通用能力补全**：标准 `move_file`、read-only `file_digest`；透明 `timeout_ms→timeout seconds`。所有转换
   保留 raw/normalized/digest，冲突值拒绝；不增加题目专属 action。

### P1：统一因果步和确定性状态胶囊

每次普通调用使用同一个在线结构：

```json
{
  "step": {
    "objective": "RWKV 当前要推进的一个局部目标",
    "done_when": "RWKV 认为何种下一观察可结束该步"
  },
  "function": "one_registered_operation",
  "params": {}
}
```

- step 与 action 同一次模型调用产生，不增加 selector、Task proposal、reviewer 或 completion model call。
- Controller 只验证通用 shape、原样保存 step、执行显式 function/params、把 ActionResult 回显给同一 RWKV。
- step 不参与 Controller 的业务 gate；RWKV 下一轮可以更新 step 或选择 final_answer。
- final_answer 也携带最后一个 RWKV-owned step ref，便于审计，不据此改写文本。

从全量 causal ledger 机械生成 `CausalProgressProjection`，替换“最近 12 条 Action”：

- 每个 path：discovered/read/mutated 的 action refs、first/latest result digest、latest artifact revision；
- 每个成功 list：实际返回成员、这些成员中哪些 path 已有 read observation；只陈述覆盖事实，不判断哪些是业务目标；
- 每个 exact operation/target/argv observation：last result 和 repeat count；
- 当前 RWKV step 原文；
- first/latest raw event refs 和完整 archive digest，保证可追溯。

投影不得解析隐藏验收、不得算业务汇总、不得生成 priority/fallback/expected output、不得把某个 member 标为
“应该选择”。集合是否 seal、何时 reduce、写什么值仍由 RWKV 决定。

### 明确不做

- 不恢复静态 Task DAG、evidence_kind/subject、reviewer、Goal completion gate、递归 subagent。
- 不根据外部验收阻止 Final，不修改 RWKV action 参数或产物。
- 不为 B/M/H 单题添加路径、字段、答案或 operation 特判。
- 不用更长 prompt 掩盖状态问题；rollover 必须由完整 ledger 的确定性投影重建。

## 七、预注册验证建议

下一轮不再以 Basic30 作为架构晋级证据：

1. 离线只验证 terminal、双 fingerprint、projection 重建、工具边界和 crash recovery；这些是结构测试，不是
   在线质量 canary。
2. 冻结源码/数据/模型/参数后直接运行完整 Full90。首轮门槛应同时超过 Round46：Strict >= 32/90、
   FP <= 24、FN <= 1；同时要求 90/90 Final 非空 raw RWKV、0 个 terminal `running`。
3. 若首轮达到门槛，不改任何源码再跑第二次 Full90，检查翻转和稳定性；只有两轮都满足才称为新最佳。
4. 官方 v1 指标与新版本化的 architecture-neutral v2 指标并列报告，不在运行后改口径。

Round118 v17 本身不满足完成条件，不能上传为“最佳质量版本”。它适合作为已审计的结构消融：单一 causal
authority 和直接工具接口应保留，但最近-N transcript、无 step 绑定、失败 key 混合执行身份、缺终止事务这四项
必须在下一轮一起替换，因为它们共同组成同一个无状态放大链。
