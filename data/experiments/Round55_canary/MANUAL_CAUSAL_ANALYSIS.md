# Round55 Canary 人工逐题因果分析

## 结论

Round55 不进入完整 E2E-90，也不上传为最佳架构。

- 固定 15 题相对已上传 Round46：Strict `6 -> 3`，External `7 -> 4`，FP `7 -> 9`，FN 均为 `1`。
- `continue` 共被 RWKV 真实选择 8 次：M06 `1` 次、H12 `6` 次、LH11 `1` 次；没有产生任何新增 Strict 通过。
- Round55 证明“同一 Task 可以执行多个动作”是必要能力，但仅增加枚举分支不能使弱模型稳定维护集合完成度，也不能修复 Goal evidence 的语义空洞。
- 最严重的新证据来自 LH02：系统只读取一次 `early/requirements.json`，RWKV 随后在 17 个“语义裁决+选源”混合请求中都输出无 reason 的模板化 `pass + M-T1-A1 + GOAL`，同一个 memory ref 因而被登记为全部 17 个 Goal criteria 的 verified evidence。持久 Proof 只能重验 actual ref 与 Goal ref 是两个独立、可追溯的来源，不能重新建立“observation 语义上满足 criterion”的事实。

## 与 Round46 的固定 Canary 对照

| Case | Round46 | Round55 | 人工逆向归因 |
| --- | --- | --- | --- |
| B01 | Strict pass | Strict pass | 正常单步链：list → write → read；四次 Task commit 均为 pass，没有使用 continue。多余 report Task 不影响真实文件。 |
| B02 | Strict pass | Strict pass | 正常 read → derive → write；两次 commit 均基于真实 observation。 |
| B10 | Strict pass | Agent blocked / External fail | 测试首轮已经暴露 `multiple---spaces`。后续 RWKV 写入 `'-'.join(value.split('-'))`，并错误声称测试通过；外部 unittest 仍失败。Goal obligation replan 又回显 capsule 而非 task batch，最终阻塞。没有使用 continue，属于代码修复决策与恢复协议双重失败。 |
| M03 | Strict pass | Strict pass | read 原 JSON → write 完整迁移对象 → read_json；未使用 continue。 |
| LH02 | FN（External pass） | FP（Agent complete / External fail） | 只执行一次 read requirements，没有 checkpoint 和 final/config。Goal evidence commit 把同一个 `M-T1-A1` 绑定到 GC1–GC17，Controller 的 proof 只验证 provenance refs 存在且独立，因而全部标 verified，随后错误完成。 |
| M01 | FP | FP | planner 直接生成三次 write_json，但从未读取三个 service JSON；写入时丢掉 port/threads/theme。Task commit 只确认“写出的值就是刚写的值”，放大了上游未读取导致的信息丢失。 |
| M06 | FP | FP | T2 首次重新读取 selection 后正确选择 continue；第二动作却直接写 manifest，并虚构相同 digest，未执行任何 copy_file。随后 commit 把“读取 selection + 写 manifest”误判为“复制完成”，下游只验证 manifest 自洽。continue 通路可运行，但不能保证下一动作符合 Task。 |
| M16 | FP | FP | 初始 DAG 只覆盖 01–03 的部分 primary/fallback，且 fallback/item_01 not_found 后改读 primary/item_01，却仍把错误 Task 标完成。没有 recovered.json，Goal evidence/coverage 在不完整 frontier 后结束。 |
| M18 | FP | FP | 已列出 a.txt、b.json、nested/c.txt，但“All contents” Task 只读取 a.txt 就 pass；随后用 `inputs/a.txt` 作为错误 key 写单项 digest_map。未选择 continue，集合 postcondition 仍被单成员 observation 提前关闭。 |
| H02 | FP | 初始化失败 | 两次 goal_parse 都生成过长、重叠 criteria 并在输出上限处截断，最终 `goal proposal has no success_criteria array`。这是 Goal 归一协议失败，与 continue 无关。 |
| H12 | Agent fail / External fail | FP | 这是 Round55 唯一明显的多动作推进：T2 顺序读取 shard_01–07，前六次均正确 continue；第七次却声称 15 个已全部读取并 pass。随后只用 7 个 observation 生成错误 aggregate。说明真实历史被保留，但模型缺少稳定、显式的已观察成员状态，靠自由文本回看会错误计数。 |
| H13 | FP | FP | 只列目录并读取 doc_01–04，随后 frontier 被 Goal evidence 提前关闭；六个 checkpoint 和 summary 均不存在。这里 planner 生成的是四个原子读取 Task，continue 不适用；缺口在 frontier/Goal coverage。 |
| LH11 | FP | FP | 五个 Task 基本都只 list_directory，不读取 artifact 内容。T4 一次 continue 后仍再次列同一目录并 pass；没有任何 checkpoint/summary。continue 没有提供明确的阶段/成员进度。 |
| B24 | Strict pass | FP | sorted.log 正确，但最后“preserve log.txt”Task 选择 write_file，把原输入覆盖成排序结果。Task commit 只验证覆盖后的 snapshot，自洽通过。错误起于 effect role/action selection，post-action 同源验证放大为完成。 |
| M12 | Strict pass | FN（External pass） | RWKV 实际写出的 math_utils.py 已通过外部测试，但计划后续继续重复 read/noop，没有运行其计划宣称的测试；Goal obligation replan 回显 capsule、违反 task-batch schema后阻塞。真实产物正确，流程无法承认完成。 |

## 从后向前的共同因果链

### 1. 完成层：Goal evidence 把“可追溯”误当成“满足”

LH02 是直接反例。`actual_ref=M-T1-A1` 与 `expected_ref=GOAL` 的来源确实不同，但“两个引用存在且不同”只证明 provenance，不证明 requirements observation 建立了 checkpoint/final-config criteria。当前请求虽然让 RWKV 同时输出 `pass|replan`，却又在同一小对象中要求选 refs，reason 还是可选；弱模型退化成 17 次模板 `pass`。之后 `rwkv_goal_provenance_commit` 把这个一次性语义选择与长期可重验的 provenance 状态合并为同一个 verified 标志，因此语义部分不可独立审计或重放。

影响范围不限于 LH02。H13、M16 等在只完成初始 frontier 后也能走向 Goal complete；M01、M18、B24 则让错误产物通过“自己写、自己读”的局部 Task 后，再被 Goal 层接受。

### 2. Task commit 层：自由文本无法稳定维护集合基数

H12 证明 memory/provenance 保留是必要但不充分：RWKV 已连续看到七个不同 producer actions，仍从 7 跳到“15 全部完成”。M18 从一个文件跳到“每个文件”，M06 从 selection+manifest 跳到“copy 完成”。Task commit 需要看到确定性生成的 observation ledger（动作序号、真实 target、outcome、是否完整/截断），但是否满足 postcondition仍必须由 RWKV决定。

### 3. Action 层：Task contract 没有约束 effect role

M06 的 copy Task 选择 write manifest；B24 的 preserve Task 选择覆盖 source；LH11 的 inspect Task 持续 list 而不 read。Controller 不能按题目规则替 RWKV选 action，但 action commit capsule必须把 Task contract、已观察 action ledger、未完成的 RWKV理由放在同一紧凑状态中，避免下一动作丢失因果位置。

### 4. Frontier/recovery 层：协议失败会截断正确或必要的后续工作

M12 的产物已正确，却在 Goal obligation replan 输出了输入 capsule而不是 task batch；B10 修复失败后发生同类阻塞；H02 在 goal_parse 过度展开 criteria直至截断。透明格式归一不能补语义字段，因此这里需要更小、更稳定的单一协议，而不是容错规则替模型完成。

## 对 Round55 变量的判断

保留架构认识，回退实现：

1. “一个 Task 可含多个真实 action”是正确的长期方向；H12 已证明运行时状态机可执行。
2. 当前 `pass|continue|replan` 三选一把“本动作是否有效”与“整个 Task 是否完成”压在同一个自由判断里，弱模型仍会在集合中提前 pass。
3. 在修复 Goal evidence 语义空洞和补齐 observation ledger 之前继续扩大多动作循环，会增加 FP；H12 从 agent fail 变成 FP 即为证据。
4. Round55 低于上传门槛，按预注册协议回退源码与测试，仅保留协议、原始结果和本人工分析。

## 下一结构优先级（质量优先）

1. **P0：拆开 provenance source selection 与 semantic criterion adjudication。** 第一次 RWKV请求只选择实际/期望来源；第二次 RWKV请求只看固定 criterion 与已选真实 evidence，按 reason-first 协议提交显式 `supported|insufficient`，并保留 raw reason。Controller/Proof 只验证引用、digest、scope、来源独立和“确有 RWKV supported 决定”，不得按内容代判或改写。`insufficient` 必须进入 Goal obligation，而不能生成 verified CriterionEvidence。
2. **P0：确定性 observation ledger。** 从真实 attempts 生成 `{attempt_id, producer_action, target, outcome, complete/truncated, memory_refs}`，不总结内容、不计算答案；同时投影给 action commit、Task commit、Goal obligation。它只报告发生了什么，不判断下一动作或完成。
3. **P1：Task commit 分离两个问题。** 先由同一次 RWKV响应声明 `action_progress=useful|not_useful` 与 `task_state=complete|incomplete`；`incomplete+useful` 才继续。仍由 RWKV决定，Controller只验证枚举和执行状态转换。
4. **P1：协议回显隔离。** Goal obligation request只给 schema 所需状态，避免把带 `schema_version/active_tasks/...` 的输入对象完整放在输出前景中；格式层只接受常见外壳，不把回显 capsule解释成 task batch。
5. **验证顺序。** 先用 LH02/H13/M16 验证“单一 observation 不再覆盖多个未满足 criteria”；再用 H12/M18/M06 验证 ledger 是否让模型维持成员数；最后用 B10/M12/B24 检查 coding、恢复和 source preservation。固定 canary改善后才跑 E2E-90。
