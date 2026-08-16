# Round86 四题逐题因果分析

## 固定结果

- Strict：`0/4`
- Agent completed：`1/4`
- External acceptance：`1/4`
- B03 为假阴性；H04 为假阳性。

## 逐题链路

| 题目 | 链路 | 根因与后续整改 |
| --- | --- | --- |
| B01 | Goal 正确；首次 Task wrapper 把完整 operation call 又嵌进 `params.arguments`；后续多次已接近正确，但额外复制模型事件顶层的 `scope_id`，连续 12 次协议拒绝后 blocked。 | wrapper 内层 `arguments` 与外层 call-envelope `arguments` 同名，且模型可见事件仍带 runtime `scope_id`。整改为唯一 `operation_args`，并新增只供模型使用的事件投影；`event_id/scope_id/version` 只留在权威状态和审计。 |
| B02 | 首次 wrapper 多嵌一个 `operation`，纠正后成功执行 `read_file`；随后错误选择 `read_json` 读取纯文本并长期重复。重复 Harness 执行后来虽被抑制，但每次仍创建 Attempt、再次调用 Task cross-check，最终 19 个 attempt、50 个请求后 blocked。 | unchanged-observation 抑制接入位置太晚。整改为在 Attempt 创建前拒绝相同 action+workspace，不再执行 Harness/verifier，也不生成合成 Attempt；相同稳定指纹最多返回三次纠错观察。 |
| B03 | 成功 `read_json`、`patch_json`，workspace 达到外部正确；随后反复 `read_json`。重复观察导致 23 个 attempt，rollover 投影越来越大，后期 RWKV 开始把 attempt/runtime 对象整体回填进 `operation_args`，最终协议预算耗尽。 | B03 证明原子接口可让 RWKV 做出正确修改，也证明重复状态膨胀会反向污染协议。除提前抑制外，rollover attempt 投影改为最小 `step_ref/operation/result/checks`，不再展示可直接复制的完整运行态对象。 |
| H04 | 首次 wrapper 多嵌一层后纠正；`write_file` 写入 `scope preserved`，缺少要求的换行；RWKV 随后提交 Task/Goal done，Agent completed 但外部失败。 | 写动作参数同时生成了 deterministic verifier 的 expected value，写后实际值与 expected 同源；Task done 只要求任意 evidence ref，无法阻止 RWKV 把局部 action 成功误判为自然语言 postcondition 完成。整改为：任何 mutating action 后必须再有一个成功的只读 observation，RWKV 才能提交 Task done。控制器不解析答案或自动完成。 |

## Round86 对架构的判定

原子 Task wrapper 方向可以继续验证，因为它消除了 Round85 的 `70/87 lh_chunk_map` 顶层工具竞争，并在 B03 产生了正确修改。但 Round86 版本不能保留为候选最优结构：其可见 runtime 标识、重复 Attempt 和同源完成证据分别造成协议污染、请求爆炸和假阳性。Round87 只验证上述三项系统整改，不改变四题、采样或评价口径。

