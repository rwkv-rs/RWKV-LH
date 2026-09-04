# Round87 全调用逐题因果分析

## 固定结果

- Strict E2E：`0/4`
- Agent completed：`0/4`
- External acceptance：`2/4`（B01、H04）
- H04 的 Round86 假阳性已消失：写入后，RWKV 确实执行了独立 `read_file`
  才提交 `lh_task_done`；但随后卡在 Goal 协议边界。

## 按链路逐题分析

| 题目 | Goal | Task 决策与接口 | 执行与证据 | 完成链 | 最早根因与放大器 |
| --- | --- | --- | --- | --- | --- |
| B01 | 正确生成一个写入并验证的 Task。 | 首次 `write_file` 完全正确。第二次正确选择 `check_command` 验证，但把可选 `env` 写为 `null`；Harness 只接受 object，接口拒绝。 | 写入及 deterministic checks 均通过，外部文件完全正确。没有执行验证命令。 | 协议纠正后，RWKV 重复 `write_file` 四次；重复动作未执行，但每个被拒绝的 Assistant 候选仍先进入 committed lane，最终 unchanged loop blocked。 | 最早是“可选 null 与 omitted”接口差异；放大器是语义拒绝发生在模型候选 commit 之后，错误输出反复进入 recurrent/replay 状态。 |
| B02 | 只生成“读取 input.txt”这一最小 Task；后续本应在 Task 完成后由 Goal 继续生成 report Task。 | `read_file` 正确并读到 `project=Orion, count=7`。随后错误选择 `read_json`，产生真实 JSONDecodeError；接着五次重复同一失败调用。 | 第一次读取得到完整源数据；第二个错误读取形成失败 Attempt，后续重复均未执行。 | 未提交第一个 Task done，Goal 无机会产生后续写入 Task，故外部失败。 | 首个模型语义错误是把文本再当 JSON；放大器仍是拒绝候选被 commit，纠正事件总跟在刚提交的同一错误后。Goal 的分阶段能力没有真正得到机会。 |
| B03 | 正确生成 read → patch → verify 三个因果 Task。 | T1 首次 `read_json` 成功且完整；第二次错误把 `byte_end=72` 当作下一游标，得到 “start_byte is at end”。后续改回 `start_byte=0`，但又重复同一完整读取。 | 两个真实 Attempt：一次成功完整读取、一次失败的末尾游标；后续重复未执行。 | T1 未完成，因此正确的 T2 patch 与 T3 verify 从未启动；外部文件未修改。 | 最早是结果事件同时暴露大量 cursor/runtime 字段，弱模型误把 `byte_end` 当续读输入；放大器是 committed rejection 与冗长结果投影。 |
| H04 | 正确生成一个安全范围内的写入 Task。 | 首次 `write_file` 正确含换行；首次 Task done 多带 inner `task_id` 被零参数严格校验拒绝；纠正后因缺独立观察被语义拒绝；RWKV 随后正确 `read_file` 并再次 Task done。 | 写入和独立读取都成功，Task 的两步证据链正确，外部三个检查全过。 | Task 已完成。Goal 首次错误复用 `lh_task_done`，随后四次改为正确 `lh_goal_done`，但把可见 task result 的 evidence/digest/ref 字段复制进 params；零参数 exact-keys 校验全部拒绝，最终 blocked。 | 最早完成层接口把“零业务参数控制”误实现成“必须生成空对象且不能携带注释”；放大器是 Goal progress 仍回灌完整嵌套 runtime 记录，字段形状很像函数参数。 |

## 跨题共同根因

1. **协议校验和运行时可接受性不是同一事务。** JSON/schema 通过后立即 commit；
   Harness 适用性、重复检测、完成证据和 workset 约束稍后才判断。后判断失败时只追加
   rejection，而未把 lane head 恢复到候选之前，导致错误模式被反复强化。
2. **接口只接受一种内部精确形状。** 可选参数的 `null` 与省略在执行语义上等价，
   零业务参数控制的额外注释也不改变函数名所表达的完成决策，但都被当作致命协议错误。
3. **模型事件仍过于接近权威存储结构。** 虽然 event/scope/version id 已移除，
   Goal progress 和 action result 仍包含多层 Attempt、tool_result、checks、digest、refs 与 cursor
   元数据。弱模型会复制这些字段，或把 observation 元数据误当作下一次 action 输入。
4. **恢复预算限制了成本，但没有修复 recurrent 状态。** pre-Attempt suppression 已阻止
   Harness/verifier 爆炸，却没有阻止相同错误 Assistant 输出进入 lane；所以请求从几十次降到
   7–11 次，但完成率没有同步提升。

## 下一轮结构整改

- 对“未执行或未接受”的 schema-valid Task/Goal 候选实施 lane-head rewind，再把拒绝事件
  追加到候选输入 checkpoint；raw output 与被拒绝事实仍完整审计。
- 格式层只增加两项通用、无语义转换：可选 `null` 按 omitted 处理；零业务参数控制以
  operation/function 名作为完整决策，额外 params 只审计、不参与语义。
- 将 action result 与 Goal task-results 改成面向模型的紧凑观察投影；权威 RunState、Attempt、
  artifact、validation 与 raw audit 不删减。完整读取显式显示 `observation_complete` 和
  `next_start_byte`，避免把 byte_end 误当续读游标。
- 对 chunk child/reduce lane 应用同样的独立协议恢复；任何一个格式错误不得直接废弃整个
  大文件并行汇总。

以上整改均不选择或修改 RWKV 的 operation、参数值、答案或完成函数；它们只修复事务边界、
接口等价形状与可见状态表达。
