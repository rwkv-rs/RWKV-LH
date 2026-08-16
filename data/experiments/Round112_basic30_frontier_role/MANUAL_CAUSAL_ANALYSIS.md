# Round112 Basic-30 手工逐题因果分析

## 结论

Round112 的 Strict E2E 为 `6/30`，低于 Round101 相同 Basic-30 的 `10/30`。混淆矩阵为：

| 分类 | 数量 | 用例 |
|---|---:|---|
| TP：Agent completed / External PASS | 6 | B03、B07、B13、B17、B19、B28 |
| FN：Agent blocked / External PASS | 6 | B01、B04、B05、B06、B29、B30 |
| FP：Agent completed / External FAIL | 9 | B02、B08、B14、B15、B16、B18、B22、B23、B25 |
| TN：Agent blocked / External FAIL | 9 | B09、B10、B11、B12、B20、B21、B24、B26、B27 |

Round101 的对应分布是 TP `10`、FN `7`、FP `6`、TN `7`。Round112 不仅少了 4 个 Strict PASS，FP 还从 6 增至 9，违反本轮预登记的“FP 不增加”要求。外部实际做对的题目也从 17 降到 12，不能把变化解释成仅仅更保守。

本文件的结论来自逐题读取 `audit.json`、Task/Attempt、原始模型调用、最终工作区与外部检查；汇总数字只用于交叉核对，不代替逐调用分析。

## 逐题分析

| 用例 | 结果 | 第一处偏差 | 后续放大链路 | 归因 |
|---|---|---|---|---|
| B01 | FN | RWKV 把包含写入与回读的完整 Task 标成 `prerequisite` | 文件已经完全正确，`lh_goal_done` 被角色门拒绝；后续修正先缺 `key`，再把 Attempt ref 写进 `after`，最终 blocked | `frontier_role` 新增假阴性；实际工作已经由 RWKV 完成 |
| B02 | FP | RWKV 把 `input.txt` 的 key=value 原文写进 `report.json`，没有构造 JSON 和 doubled value | `read_json` 已明确报错；恢复却把失败 Task 替换成仅 `read_file(report.json)` 的 deliverable Task，通用“读到文件”证据通过后 Goal 过早完成 | RWKV 内容错误；过弱完成证据和恢复降级把错误放大为 FP |
| B03 | TP | 无结果偏差 | 正确更新并验证 `config.json`，但用了 4 个 Task、14 次请求，存在重复验证 | 质量正确；链路仍偏长 |
| B04 | FN | RWKV 已创建目录、精确复制文件并写对 manifest，但验证 Task 在已经读到两个正确文件后继续重复读取 | unchanged-action 将验证 Task 阻塞；角色门与 blocked 状态覆盖了已正确的外部结果；Final 又复述完整嵌套状态直到被截断 | 任务完成协议、重复恢复和终止上下文共同制造 FN；不是模型内容错误 |
| B05 | FN | 完整 Task 被标成 `prerequisite` | RWKV 已删除目标行并回读验证，外部两项检查都通过；角色门要求再建 deliverable，模型随后错误使用 Attempt ref，最终 blocked；Final 反而幻觉 `app.env` 不存在 | 角色门和复杂引用协议制造 FN；Final 状态投影质量差 |
| B06 | FN | 三个实际完成的 Task 全被标成 `prerequisite` | `combined.txt` 精确通过外部检查，Goal done 被拒，最终错误声称 T3 未完成 | 角色门直接制造 FN，Goal/Final 对已提交状态理解不一致 |
| B07 | TP | 无结果偏差 | 正确读取 production 分支并只创建 production endpoint | 质量正确 |
| B08 | FP | RWKV 算对 SHA256，但把 manifest 的 `file` 写成 `manifest.json` 而不是 `payload.txt` | deliverable Task 只回读文件，未对字段和值逐项复核；Goal/Final 都声称完全正确 | RWKV 单字段错误；通用文件读取证据放大为 FP |
| B09 | TN | RWKV 读到 CSV 后在 deliverable Task 重复读输入，没有写 `stats.json` | unchanged-action 正确阻止无进展重放，最终诚实 blocked | RWKV 未推进；阻塞判断正确 |
| B10 | TN | Goal 把代码任务拆为多个窄 discovery Task；T1 已读 `slug.py` 和完整测试，却仍停留在“读取 slug.py”责任中 | Task lane 重复读取；恢复要求重建替换 Task，模型多次生成错误 `after`/重复结构，后续实现 Task 永远没有执行机会 | 过窄 Task 边界和复杂修复协议放大 RWKV 重复，不是缺少代码/测试观察 |
| B11 | TN | RWKV 一度写出 `normalized_name.txt`，但内容只是原文复制，没有 trim/title-case/RWKV acronym 处理 | Goal 状态形状接近 `lh_tasks`，模型反复回显为新命令，共创建 14 个同构读取 Task；最终 blocked | 首因是 RWKV 内容转换错误；命令形状态投影和无跨前沿重复抑制严重放大 |
| B12 | TN | RWKV 读取所有整数后，deliverable Task 继续重复读取 `numbers.txt` | 未写 `stats.json`，unchanged-action 后 blocked | RWKV 未推进；Task 提示未把已完整 EOF 观察转成下一操作 |
| B13 | TP | 内容最终正确 | Goal 重复创建对同一 `config.json` 的 deliverable 读取 Task，累计 13 Task、47 请求；Final 还说“将再次读取”而运行已结束 | 结果正确，但命令形状态回显和 Final 时态错误明显 |
| B14 | FP | 新 deliverable Task 没有依赖 T1/T2，Task lane 因此看不到左右文件的已读内容 | RWKV 把文字描述 `left.txt content, ...` 原样写入 `merged.txt`，回读后仍完成 | RWKV 忘写 `after` 是第一偏差；观察可见性完全依赖显式引用使小错误变成内容错误 |
| B15 | FP | RWKV 正确去重排序颜色，却把 `colors.json` 写成裸数组而不是 `{\"colors\": [...]}` | `read_json` 只证明 JSON 可解析，不能证明 exact object shape；Goal/Final 误报正确 | RWKV 结构错误；过弱证据放大为 FP |
| B16 | FP | RWKV 只把 MODE 改为 prod，保留了注释和空行 | Goal 多次创建相同 normalize Task，Task 反复写回同一错误内容，10 Task、51 请求后仍完成 | RWKV 没执行完整规范化；缺少同快照重复 Task 抑制和逐条完成复核 |
| B17 | TP | 无最终偏差 | 正确筛选、排序并写出 active names/count；前面仍有重复 prerequisite 读取与验证 Task | 质量正确；可压缩链路 |
| B18 | FP | RWKV 把 discount 加到 subtotal，得到 total=92，而正确语义是应用折扣后 total=68 | 首个 deliverable proposal还使用 Artifact ref 作为 `after` 被拒；格式修正时语义角色改变，错误 JSON 被回读后完成 | RWKV 算术错误；跨前沿引用协议与通用回读证据未能触发自我纠错 |
| B19 | TP | 最终内容正确 | T2 在错误命令/验证中消耗 36 Attempts，替换 T3 又用 33 Attempts，合计 97 请求/70 Attempts 才完成 | 质量正确，但恢复链路极不紧凑 |
| B20 | TN | 与 B10 同类：代码任务被拆成读取 `parity.py`、读取测试和后续实现；第一个读取 Task 重复 | 实现 Task没有机会运行，最终正确说明 stub 仍在 | 过窄 discovery Task 放大模型重复 |
| B21 | TN | 读到 CSV 后，deliverable Task 仍重复读取输入 | 未创建 category totals，blocked | RWKV 未推进；阻塞正确 |
| B22 | FP | RWKV 在标题和首个 checklist item 之间多写一个空行 | 回读只证明文件存在/可读，未按 exact content 自审；Final 展示的内容本身就暴露额外空行 | RWKV 精确格式错误；Goal 复核没有利用可见文本 |
| B23 | FP | primary 是坏 JSON，RWKV 正确读取 backup，但写出的 `selected.json` 缺少 `source` | read_json 成功后直接完成，Final 还反向声称 primary 可读且未使用 fallback | RWKV 漏字段；完成复核和 Final 对实际观察失真 |
| B24 | TN | 第一 Task 读完整 `log.txt` 后，第二 prerequisite Task 从 EOF offset 继续读并重复 | 没有执行去重、排序、写入，blocked | RWKV 忽略 complete/EOF；分离 discovery Task放大 |
| B25 | FP | RWKV 正确合并主要 nested 值，但漏掉 `enabled=true` | `settings.json` 可解析即被 Task done；Final 却声称文件包含 enabled | RWKV 漏字段；Task/Goal/Final 都没有逐条对照实际 JSON |
| B26 | TN | 并列 Task 中 T1 越过自身责任，额外创建 `output/c.txt`，之后又创建正确的 nested 文件 | 各 Task 局部回读无法对整个目录集合负责；验证 Task 循环，外部发现多余文件 | RWKV Task 越界；过细并列 Task破坏整体输出一致性 |
| B27 | TN | 第一个读取 Task 完成后，Goal 不断创建同一 `service.conf` 读取 Task | 14 个同构 Task、53 请求，始终没有 replace 操作；最终回答诚实说明未修改 | 命令形状态回显 + 缺少同快照重复前沿抑制 |
| B28 | TP | 文件结果正确 | 失败 Task/替换 Task共消耗 71 Attempts、109 请求；Final 先说 partially successful，后又说 all tasks completed | 结果正确；恢复和 Final 表达质量差 |
| B29 | FN | RWKV 已精确复制并写对 manifest，但所有前沿都标为 prerequisite | 角色门拒绝完成，随后重复生成 15 个读 source/backup/manifest 的 Task；Final 错称 backup 目录不存在 | 角色门、重复前沿和 Final 状态理解共同制造 FN |
| B30 | FN | RWKV 已把 `normalize_name` 实现正确，外部测试通过；模型自行选择了环境不存在的 `pytest`，而测试文件可直接由 Python/unittest 运行 | 两轮 replacement 继续重复同一不可用命令；全部 Task又标 prerequisite，最终 blocked；Final 误称测试文件被修改 | 运行器选择错误属于 RWKV；恢复没有从“命令不存在”转向其他观察到的测试入口，角色门进一步阻止完成 |

## 跨环节因果链

### 1. `frontier_role` 是有害的额外语义分类

这个字段要求弱模型在“规划 Task”之外再判断整个前沿是 prerequisite 还是 deliverable。B01、B05、B06、B29 的 RWKV 已经在所谓 prerequisite Task 内完成了写入和验证；控制器仍拒绝 Goal done。该字段同时没有阻止 B02、B08、B14、B15、B16、B18、B22、B23、B25 的错误 deliverable 被完成。因此它既不是可靠证据，也不是可靠防 FP gate，应完整删除，而不是继续补分类规则。

### 2. 普通 read→transform→write→verify 被过度拆分

初始 Goal 提示强烈鼓励 existing code/data 先生成 discovery frontier。B10、B20 证明，读代码和测试被拆成独立 Task 后，RWKV 即使已经拥有全部内容，也可能被窄 Task 的 done_when 和恢复状态锁住，后续实现永远不执行。B14 又证明下一 Task 的可见观察依赖模型正确填写 `after`；一个漏写就丢失正常 Agent 本应保留的工具结果。

下一版应优先使用最少的端到端 Task。普通小任务由一个 Task lane 自行读取、修改、验证；只有成员集合未知、确实需要先确定范围的大型集合任务才建立独立 discovery/workset。

### 3. 状态投影仍与命令形状过近

B11、B13、B27 的原始调用显示，Goal lane 会把历史状态重新输出成 `lh_tasks`，再被物化为新 Task。即使 `_goal_task_row` 名义上是只读状态，其中仍有 `objective/done_when/evidence_kind/evidence_subject/after_refs` 等与提案高度相似的字段。状态必须改成明显非命令的历史记录形状，并对“相同 Task 结构 + 相同完整 workspace digest”做无进展拒绝。

该拒绝只判断 RWKV 自己给出的字段是否完全相同以及外部状态是否未变；不推断语义、不选择替代操作、不修改任何参数。

### 4. 完成证据只证明“读过”，没有促使 RWKV逐条复核

B02、B08、B15、B18、B22、B23、B25 都有明确可见的错误结果，但 `file_content_read/read_json` 的确定性检查只证明路径存在、内容可读或 JSON 可解析。控制器不能读取隐藏验收并替模型改值；正确方向是让 RWKV 在第一次 `lh_goal_done` 后，基于紧凑的原始观察进行一次显式完成复核，再由 RWKV 选择确认完成或创建修复 Task。

复核只能重显已观察事实，不能生成 criterion、期望值、答案或成功 verdict。

### 5. 终止回答“非空”已经实现，但还不等于合格

30/30 都有非空 `final_output`。29/30 与有效解析的 RWKV Final 字节一致；B04 的 RWKV 最终输出复述嵌套 `observed_state` 并达到长度上限，交付的是截断 JSON 外壳，`final_output_matches_raw_rwkv=false`。

终止输出必须同时区分：

1. 有效 `lh_final_answer.text`：原样交付，不重写。
2. 有原始模型字节但协议无效/截断：完整审计原始字节，向用户交付明确标注的运行状态兜底，不把协议垃圾当回答。
3. 模型完全无字节或 transport 失败：交付同类运行时兜底。

任何兜底都不能改变 run status，也不能计为 Strict E2E 成功。

## 下一轮结构整改方向

1. 完整删除 `frontier_role/goal_role` 及其 Goal-done gate，恢复唯一 Task 结构。
2. 修改 Goal 规划指导：默认一个或少量端到端 Task，不为普通文件/代码任务强制 discovery frontier。
3. Task assignment 自动携带有界、按时间顺序的最近已提交观察；显式依赖仍用于调度，但不再是普通跨前沿信息的唯一通道。
4. 将 Goal 历史状态改为明显非命令字段；增加“相同结构 + 相同完整 workspace digest”的新前沿无进展拒绝。
5. 第一次 `lh_goal_done` 只进入一次 RWKV completion review；第二次仍由 RWKV确认或创建修复 Task。
6. Final 使用紧凑结构化事实胶囊和较短输出预算；无有效 Final 时只返回诚实状态兜底。
7. 保留现有简单格式转换层，仅转换常见外壳/参数别名；不得补语义值或修正业务结果。

以上修改均不允许控制器选择业务操作、计算答案、修改 artifact、重写有效 RWKV Final 或读取隐藏 acceptance 做在线判断。
