# Round59 固定 15 题逐题因果分析

## 结果

- Strict `1/15`，External `6/15`，Agent `1/15`，FP `0`，FN `5`。
- Round46 同组是 Strict `6/15`、External `7/15`、FP `7`、FN `1`。
- Round59 未达到预登记的 Strict `>=6`、FN `<=1`，不得运行 full90，也不得上传。

## 逐题首错与放大链

| 用例 | 外部/Agent | 最早偏离 | 后续放大 | 归因 |
|---|---|---|---|---|
| B01 | PASS/FAIL | `M-T2-A1.content` 把真实文件正文、两个分隔换行和 `ACTION RESULT METADATA` 拼成一个文本字段 | Goal GC2 把内部元数据前的分隔换行当成文件多出的换行，判 insufficient；replan 随后重复已完成任务 | 证据表示污染 → RWKV 语义误判 → 恢复重复 |
| B02 | PASS/PASS | 无 | 三个 criterion 均从正确的输入、写后快照和最终 read-back 得到 supported，final answer 与 raw RWKV 一致 | 正常对照 |
| B10 | FAIL/FAIL | Goal proposal 两次都只输出一个 criterion 片段并以 length 结束，没有完整 envelope | Run 无法创建 | 16K/输出预算内的 Goal 协议承载失败；正确阻断 |
| M01 | PASS/FAIL | 执行阶段正确更新三个 service 文件并写/读 summary | GC1/GC3 把 summary 的读结果错误描述成同时观察了三个 service 文件；GC3 第一次又把同一 ref 放在 actual/expected，被协议拒绝；第二次因“GOAL 没精确内容”判 insufficient | 全历史重新检索时发生来源含义漂移；独立 expected 约束进一步放大为 FN |
| M03 | PASS/FAIL | 最终 users.json 和 post-write/read-back 都已正确且无 `legacy_note` | GC5 却声称 `M-T5-A1` 的迁移内容仍含 `legacy_note`，与 catalog 原文相反，判 insufficient | 全历史相似版本竞争导致 RWKV 把旧字段投射到当前版本 |
| M06 | FAIL/FAIL | “copy listed files” Task 选择写 manifest，未复制任何文件 | 后续 verifier 读取 manifest 来判断 package 集合，Task 层出现错误 pass；Goal 前已因重试/格式失败阻断 | action 与 Task 语义不一致；正确外部失败 |
| LH02 | PASS/FAIL | 17 个文件操作全部正确；15 个 checkpoint 与 final config 均存在 | GC12 在 catalog 明列 checkpoint 快照时仍声称“catalog 没有 checkpoint files”，判 insufficient | 长 catalog 注意力丢失；按 criterion 重扫全部历史导致 FN |
| LH05 | FAIL/FAIL | 初始 5 个 Task 只有目录/规则检查，没有 20-shard 处理闭环 | missing reports 触发 make/list 名称漂移；Task 合同仍要求 listing，恢复耗尽 | 集合计划未闭包 + 恢复协议/工具名漂移；正确失败 |
| LH11 | FAIL/FAIL | 五个 phase Task 全部只是重复列同一个 40-file 目录，没有读取内容、checkpoint 或 summary | Goal 正确发现 phase01 不存在；obligation replan 无法形成有效后续批次 | 集合成员展开缺失；正确失败 |
| B24 | FAIL/FAIL | sorted.log 已正确生成，但“preserve log.txt”Task 反而用 deduplicated 内容覆盖原文件 | Task postcondition 错误 pass；Goal GC2 又只看原始 log，未把 sorted.log 写后证据与去重 criterion 关联 | action 选错破坏不变量；Goal 来源关系也未保持；正确外部失败 |
| M12 | PASS/FAIL | 两个并行 write Task 和 test Task 均正确，测试输出 `OK`，最终源码正确 | GC1 把 catalog 中明确为 `return a / b` 的当前快照幻觉成 `return a * b`，判 insufficient | 重复语义理解产生与原文相反的 RWKV 判断；执行正确但证据关系未沿 Task 传递 |
| M16 | FAIL/FAIL | fallback/item_04.json 读取成功，但原 Task postcondition 固定为“primary/item_04 observed” | Task commit 拒绝合法 fallback；failure analysis 反复选择同一 fallback/primary，恢复耗尽 | Task 合同无法表达 alternative outcome；正确失败 |
| M18 | FAIL/FAIL | 目录中有四个输入文件，但只读 a.txt 就写 digest_map | Task commit 把单文件读取当“目录内容均已读取”；GC4 最终正确发现 map 不完整 | 集合覆盖率在 Task 层过早完成；正确失败 |
| H12 | FAIL/FAIL | 发现 15 shard 后只读取前四个，没有 aggregate producer | Goal GC1 正确指出没有 `aggregate.json` 的 shard_count 证据 | 初始 frontier 没有继续集合展开/汇总；正确失败 |
| H13 | FAIL/FAIL | Task postcondition把“识别 PRIORITY signal line”错误解释成必须是 yes；doc_03 实际是 no | 对同一 read 重试直至耗尽，未进入其余文件和 summary | Task postcondition把观察任务变成值断言；正确失败 |

## 跨环节根因

1. **Observation 数据与 runtime 元数据同字段拼接。** B01 是直接证据；该格式还进入 Task、recovery 与 Goal 多个 capsule，任何精确文本 criterion 都会受污染。
2. **Goal 证据关系建立得过晚。** Task 执行、Task postcondition 和 raw observation 已经产生正确局部事实，但 Task 没有 criterion 绑定；图结束后才让 RWKV 从整个历史重新选择并重新理解，造成 M01、M03、M12、LH02 的 FN。
3. **集合没有显式覆盖状态。** `list_directory` 只产生成员列表，但 Task graph 不持有“已发现/已处理/未处理成员”；弱模型容易在一页或一个成员后过早结束，见 M18、H12、LH05、LH11、H13。
4. **Task 合同缺少合法替代结果。** primary invalid/missing 后读取 fallback 仍无法满足写死的 primary postcondition，见 M16。
5. **同一语义被多次重新决定。** Task commit 已判断正确，Goal 阶段不复用它声明的 criterion/证据关系，而是重新理解 raw history。第二次判断可能直接与第一次和原文相反，见 M12。

## 下一步结构方向

1. 把 action observation 改成 `observed_content` 与 `observation_metadata` 两个结构化字段；历史 state 读取时兼容旧 marker，但送模前分离。不得改写模型输出。
2. Task batch 保持紧凑执行结构；增加一个独立的 RWKV `task_criterion_binding` 请求，让 RWKV 为每个 Task 声明 `advances_criteria`/`satisfies_criteria`。Controller 只校验 task id 与 criterion id，不推断关系。
3. 满足 criterion 的 Task commit 后立即用该 Task 的因果依赖闭包做 criterion-local adjudication；不再在图结束时对所有历史盲搜。原始 observation 仍是证据，先前 Task commit 只作为模型状态连续性信息，不替代证据。
4. 对 list/read collection 引入通用 coverage state：观察到的成员、已处理成员、continuation token、聚合 producer；由真实工具输出更新，RWKV 决定后续任务，Controller 不计算答案。
5. failure analysis 明确区分“换 action 仍可满足原 postcondition”和“合法 fallback 改变了 postcondition”；后者必须 replan/supersede Task，不能在原 Task 内无限 reselect。
