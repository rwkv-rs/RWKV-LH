# Round89 全调用逐题因果分析

## 结果

- Strict `2/4`：B01、B03 通过。
- External `2/4`；Agent completed `3/4`。
- B01 从连续两轮假阴性提升为 Strict PASS；B03 保持 Strict PASS。
- B02 仍双失败。
- H04 出现新的假阳性：Agent completed，但目标文件根本没有创建。
- 四题仍全部有非空、精确来自 RWKV Final lane 的回答。

## 逐题

| 题目 | 直接格式与 recovery capsule 效果 | 最终结果 | 归因 |
| --- | --- | --- | --- |
| B01 | direct Task done 被通用转换层接受；写后 completion gate 要求独立观察，RWKV 读取精确文件后完成。没有再进入 JSON 失败循环。 | Agent/External/Strict 全过，2 个 Attempt。 | direct representation 兼容消除了非语义摩擦，独立观察 gate 保住正确性。 |
| B02 | 首次 `read_file` 成功，随后一次真实 `read_json` 失败；每次重复后 recovery capsule 都排除了旧 Assistant bytes，但保留成功读取与真实失败。 | blocked，2 个 Attempt，Final 如实回答。 | 失败模式不是只由已提交候选污染造成；capsule 中失败观察的显著性仍使模型选择 `read_json`。第一批 Task 不能完成，Goal 因而不能继续 report Task。 |
| B03 | direct completion 和 capsule 兼容后仍走完整三 Task；格式噪声被回退但未破坏实际读写。 | 保持 Strict PASS。 | 正向能力稳定，不是 Round88 偶然。 |
| H04 | 初始 Goal Task 正确声明“创建文件”，但 Task 首个操作选择 `list_directory`；随后 direct `lh_task_done` 被接受。运行时只要求存在任意 Task evidence，且没有 mutation，所以 post-mutation read gate不适用。 | Task/Goal completed；外部因 `safe/result.txt` 不存在而失败；Final 甚至错误宣称文件已创建。 | 根因是 Task proposal 的自然语言 `done_when` 没有可执行的结构证据类型。Task lane 的完成决策被过早接受；direct 兼容只是让该既有缺陷更早暴露，不是答案修改。 |

## H04 假阳性的结构根因

当前 Task 只有 `objective/done_when/after`。`done_when` 是自然语言，Controller 为避免
作弊不解析它；因此它无法区分以下两种 Task：

- “创建文件”必须有真实 workspace mutation；
- “列出文件”可以由 `list_directory` 完成。

只根据已执行 action 推断 Task 类型也不成立：H04 恰恰先选错了 `list_directory`，再用同一
错误路径证明自己完成。要恢复 FP 控制，证据契约必须在执行前由 RWKV 的 Goal lane 明确声明，
运行时只验证所声明的结构类是否真实出现。

## 已实施的下一项整改

Task proposal 增加必填 `evidence_kind`，由 RWKV 在规划时选择：

- `workspace_change`
- `content_observation`
- `collection_observation`
- `command_observation`
- `outcome_observation`

Task done 只在 Task 自己的 Attempt/chunk/workset 中存在该结构证据时可提交。Controller 不从
自然语言推断类别、不选择 operation、不判断答案值。写后独立读取要求继续叠加。

这会让 H04 的“创建文件”Task 在只有 `list_directory` 时被拒绝，同时仍允许真正的目录列举
Task 用 `collection_observation` 完成。该结构已由新增离线回归验证，未进入本 Round89 结果。
