# Round56 固定 15 题逐题因果分析

## 结论

Round56 不可上传。固定组结果为 Strict `3/15`、External `6/15`、Agent `3/15`、FP `0`、FN `3`；Round46 同组为 Strict `6/15`、External `7/15`、FP `7`、FN `1`。两阶段 Goal 证据链消除了本组假阳性，但以新增假阴性和 Strict 下降为代价。

这不是简单的“裁决过严”。三个 FN（M03、B24、M12）都从同一处开始：选源协议优先选择按任务顺序排在最前的旧观察，语义裁决随后正确判定该旧观察不能证明最终 Goal。恢复规划再重复已经完成的任务，最终阻断。另有一个边界泄漏：语义裁决提示中仍包含全部 Goal memory，导致 RWKV 有时引用未被选中的观察。

## 逐题链路

| 题目 | 外部/Agent | 第一个决定性偏差 | 后续放大 | 归因 |
|---|---:|---|---|---|
| B01 | 对/完成 | 无；写入和复读均正确，GC1/GC2 选择最终写入快照 | 两项裁决均由 RWKV 判 supported | 严格通过；两阶段链有效 |
| B02 | 对/完成 | 无；输入读取、JSON 写入和复读均正确 | GC1-3 首次裁决常漏固定 schema，但重试保持原语义 | 严格通过；暴露固定 schema 复述负担 |
| B10 | 错/阻断 | slug 实现没有折叠多个空格，测试已明确失败 | 恢复动作反复做无效 replace_text | 执行/恢复问题，早于 Goal 证据链 |
| M01 | 错/阻断 | 三个服务 JSON 用整对象写入，丢失 unrelated settings | GC1 又选了目录列表 M-T1；裁决判 insufficient，恢复规划重复验证 | 产物根因是非保留式写入；选源偏置是第二个问题 |
| M03 | 对/阻断 | GC1、GC2、GC3 均优先选择迁移前的 M-T1，而非迁移后复读 M-T3 | GC1 重试回答越过绑定引用 M-T3；GC3 仍基于 M-T1 判 insufficient；obligation replan 协议失败 | FN；首源偏置 + 裁决上下文泄漏 + 恢复放大 |
| M06 | 错/阻断 | 模型只伪造 manifest，从未复制 alpha.dat/gamma.dat，且两个 digest 相同 | GC2 选择 selection.txt 后正确判定没有复制证据；恢复仍生成重复任务 | 正确阻断；执行任务缺少真实 copy |
| M12 | 对/阻断 | GC1 选择修复前的 math_utils.py（M-T1），没有选择通过测试的 M-T5 | 裁决正确指出旧代码错误；恢复规划不能形成合法新增 frontier | FN；首源偏置 + 恢复放大 |
| M16 | 错/阻断 | 初始图把“读取五项”压成单文件动作，缺失合并与 recovered.json 写入 | item_02 读取失败后重复同一动作，未到 Goal 阶段 | 规划粒度/动作表达问题 |
| M18 | 错/阻断 | 只读取 inputs/a.txt，digest_map 只有一个键 | GC1 又选择目录列表而非 digest_map；即使换源，GC4 仍应因集合不完整失败 | 正确阻断；集合任务被单成员动作冒充 |
| H12 | 错/阻断 | “读取 15 shards”只执行 shard_01；聚合值只来自两个 item | GC1 绑定目录列表却在裁决中引用未绑定 aggregate；GC2 最终识别 item_count=2 不足 | 正确阻断，但证实裁决上下文泄漏 |
| H13 | 错/阻断 | 每个四文件阶段只读第一个文件，六个任务过早 pass | GC1 选择 doc_01 后判 checkpoints 不存在；恢复仍按未读取内容拟写 checkpoint | 任务 postcondition 与单动作覆盖范围不一致 |
| LH02 | 对/完成 | 本次规划实际生成 15 checkpoints 与 final/config，而非只读 requirements | 19 个 criterion 逐项选源和裁决，均有对应当前快照 | 严格通过；但与此前运行差异含模型采样影响，不能单独归功于 Round56 |
| LH05 | 错/阻断 | 目录仅观察到 18 primary，后续未读取任何 shard 内容 | 并行的报告/summary 任务在依赖不足时执行并捏造 0 值结果 | 初始依赖图与数据获取粒度错误，早于 Goal 阶段 |
| LH11 | 错/中断 | 初始图把 8 文件 phase 写成不存在的 `artifacts/009-016.txt` 等路径 | failure analysis 重复错误路径；随后一次服务连接断开 | 规划路径表达错误；本次还含传输中断，不能用于 Round56 Goal 消融结论 |
| B24 | 对/阻断 | GC1 选择原始 log.txt 读取 M-T1，而非最终 sorted.log 复读 M-T5 | 裁决正确说读取输入不能证明去重/排序；replan 重复全部已完成任务 | FN；首源偏置 + 恢复放大 |

## 跨环节根因

1. **选源是单引用、旧到新排列。** 对最终态 criterion，RWKV 在 M03、M01、B24、M12、M18、H13 的第一项都选择 M-T1。单个 `actual_ref` 还无法表达“多个服务文件均正确”这类集合证据。
2. **历史 expected 与当前 actual 没有真正的时间语义。** 当前规则禁止同一路径的两个时间点互为 actual/expected，并在重验时把历史 expected digest 与当前文件比较；这使“迁移后保留原字段”无法用迁移前后两份独立观察证明。
3. **语义裁决隔离不完整。** body 只展示选中来源，但 `_json_prompt_with_context` 又附加全部 memory。M03、H12 已出现引用未选来源的原始输出。
4. **固定 schema 复述增加协议失败。** 多个有效的 `reason+decision` 首答只漏固定 schema，第二次回答才被接受；请求类型本身已经能唯一确定 schema。
5. **恢复层放大选源错误。** evidence insufficient 后，Goal obligation planner 经常重复已完成任务或返回 capsule/旧外壳，导致一次错误选源直接变成 run blocked。

## 下一步结构要求

- 证据目录按最新到最旧展示，并显式标记 observation order、是否仍匹配当前 workspace、是否已被后续 revision 取代；这些只是可审计事实，不替 RWKV 选择。
- 选源允许 RWKV 返回最小的 `actual_refs` 集合，支持跨文件/跨任务 criterion；控制器只校验引用、所有权、摘要和时间关系。
- 允许同一路径的迁移前只读观察作为 historical expected、迁移后观察作为 current actual；历史 expected 只按 append-only memory digest 重验，不拿它和当前文件内容比较。
- 语义裁决请求只包含固定 criterion、RWKV 选中的 actual observations 和 expected source，不附加其他 memory。
- 固定 schema 由 request_type 在协议边界确定；RWKV 只输出具有语义的字段，格式层不得补 reason、decision、ref 或答案。

