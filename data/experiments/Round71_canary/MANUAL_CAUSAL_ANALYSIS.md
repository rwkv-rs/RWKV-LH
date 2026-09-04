# Round71 fixed-15 人工因果分析

## 实验身份

- 数据来源：`data/e2e90/tasks.json` 中固定的 15 个历史失败入口，由 `RUN_PROTOCOL.json` 记录具体选择。
- 版本：Round71，协议归一化器 `transparent-protocol-boundary.v10`。
- 用途：逐题定位最早错误环节、后续放大环节和系统性根因；不能由聚合脚本结论代替人工链路判断。
- 运行产物：本目录 `results.json`、各题 `model_trace.json`、`event_log.json`、`state_timeline.json`、`causal_ledger.json`。
- 结果：Strict `0/15`，External `1/15`，Agent `0/15`；相对 Round70 的 Strict `1/15` 发生回退。
- 生成方式：逐题交叉检查原始 RWKV 输出、协议事件、Task 状态、动作结果、外部验收和终止原因后人工记录。

## 总体结论

Round71 不是单纯“模型答错”。15 题中，最早失败集中在五个公共边界：

1. Goal/审核输出被过小输出上限截断，导致正确 Goal 草案尚未进入计划阶段（LH11、M18）。
2. Task、Attempt、Action 结果和 Memory 的证据引用没有统一进入一个可选择注册表，导致模型选择真实存在的引用仍被协议拒绝（B10、LH05）。
3. 当前任务、当前动作和当前动作结果没有在决策提示末端形成唯一权威包，旧失败和抽象措辞覆盖了新事实（B02、H12）。
4. 常见 G1i 表示在固定边界没有被透明归一化，语义相同的重复 identity、内联参数和观察装饰触发硬阻塞（B02、B10、M01、M03、M06、M16、H12、LH05）。
5. Task 图缺少“每个 Task 是否能由已注册动作直接建立或推进”的 RWKV 自审，产生读取不存在输出、无动作可承载的纯内存变换和不必要验证任务（B01、B24、M01）。

其中 2、4、Goal 输出上限和 `8` 个 ready Task 上限是基础设施缺陷；1、3、5 是 RWKV 与协议共同形成的问题。不能用控制器替模型挑选正确答案，但可以消除这些无语义的结构阻塞。

## 逐题链路

### E2E-B01

- 正确进展：T1 的 `write_file` 创建了内容完全正确的 `greeting.txt`；外部验收通过。
- 最早错误：计划额外生成 T2“再次验证文件”，尽管生产动作已经有自动快照和确定性检查；T2 又选择 `read_json` 读取普通文本。
- 放大过程：`read_json` 得到 `JSONDecodeError` 后，RWKV 明确改选语义正确的 `read_text`，但注册动作实际名为 `read_file`，三次均以“未注册”阻塞。
- 根因：冗余验证 Task、工具词汇边界缺少闭集同义名，以及当前 action catalog 没有在恢复提示末端重新锚定。
- 性质：产物正确但 Agent 阻塞，是 Round71 唯一 FN，也是相对 Round70 的直接回退。

### E2E-B02

- 正确进展：T1 成功读入 `input.txt`；T2 首次误用 `read_json` 后，后续 `read_file` 已成功观察文本，Task commit 也正确判断 `open`，说明下一步应写 `report.json`。
- 最早错误：继续动作选择被更早的 `read_json` 失败吸引，未以最近成功读取和当前 postcondition 为主。
- 放大过程：随后输出 `{"action":"read_json","type":"read_json","arguments":...}`；两个 identity 值完全一致，却被当作未知字段硬拒绝三次。
- 根因：当前决策包位置不够权威，加上固定工具边界不接受相同 identity 的常见重复表示。

### E2E-B10

- 正确进展：RWKV 已读取测试和当前实现。
- 最早错误：T1 Task commit 选择 `T1-A1`、`T1-A1-R1`，这些是本次 Attempt/Artifact 的真实引用，但 `AVAILABLE EVIDENCE` 只注册了 `ACTION:`、`CHECK:` 和部分 `M-` 引用。
- 放大过程：同一 Task 被判失败；恢复动作的完整 `read_file` 调用又复制了 `task_id`、`continuation_cursor`，固定边界未识别后者，连续三次拒绝。
- 根因：同一证据在状态中存在、在提示中可见、却不能在统一注册表中选择；随后常见观察装饰再造成第二次阻塞。

### E2E-B24

- 正确进展：T1 完整读取 `log.txt`；T2 首次 `read_file` 后，Task commit 正确判断“只读取并未去重”，因此保持 `open`。
- 最早错误：计划把“从已观察文本中删除重复行”建成一个没有可观测产物的独立 Task。现有动作中没有“只改变模型内存”的执行效果；合理做法应把确定性变换与写入 `sorted.log` 合并为可执行生产步骤，或用命令直接产生文件。
- 放大过程：selector 反复选择 `read_file`，reviewer 又正确拒绝该动作不能推进去重 postcondition，三轮后阻塞。
- 根因：Task postcondition 与注册动作效果不可实现，而不是 reviewer 过严。需要计划阶段的执行可达性自审。

### E2E-M01

- 正确进展：T1 正确列出 `services/`。
- 最早错误：初始 manifest 已表明 `services/summary.json` 不存在，但计划仍创建无依赖 T2 去读取它；生产 T6 反而排在更新三项服务之后。
- 放大过程：读取不存在文件失败，恢复中的 `read_json` 又输出相同 identity 重复和 `type` 加内联 `path/start_char/max_chars`，三种常见表示均未归一化。
- 根因：缺少 producer-before-consumer 计划审计；格式边界随后把可恢复错误变成硬阻塞。

### E2E-M03

- 正确进展：T1、T2 连续读取 `users.json`，内容已经观察。
- 最早错误：计划本身重复读取同一输入，增加了上下文中的相似旧动作；迁移 Task 到来时，argument call 复制 `action` 与 `type` 两个相同 identity。
- 放大过程：三次相同表示均被协议拒绝，尚未执行迁移写入。
- 根因：冗余 Task 与常见重复 identity 未归一化；不是 JSON 迁移能力已被真实测试后失败。

### E2E-M06

- 正确进展：T1 已读取 `selection.txt`。
- 最早错误：T2 是复制资产的 mutation Task，却先后把文本选择文件当 JSON 读取，未利用已经存在的文本观察进入复制动作。
- 放大过程：相同 JSON 解析失败重复两次，之后 argument call 进入 `action/type` 重复 identity 硬阻塞。
- 根因：恢复提示仍突出旧失败而非当前 postcondition/最近观察，随后格式边界终止恢复。

### E2E-LH02

- 正确进展：RWKV 连续完成 15 个 checkpoint 和 `final/config.json`，所有已写文件均经过快照与 Task commit；长链状态传递明显改善。
- 最早错误：初始计划只覆盖 step01–step15，遗漏后续 checkpoint，却提前生成 final；Goal obligation 只能在 final 之后追加 step16–step20。
- 放大过程：T18 已选择正确的 `write_json` 创建不存在的 step16，但 reviewer 错误假定需要保留既有内容并建议未注册的 `append_json`；selector 随后复制该建议并阻塞。
- 根因：计划覆盖和依赖顺序不完整；reviewer 没有被“目标文件当前不存在”和注册动作闭集充分锚定，review reason 又污染后续选择。

### E2E-LH05

- 正确进展：T1 列目录、T2 读取 `recovery_rules.md`，动作与观察均正确。
- 最早错误：Task commit 选择真实的 `T2-A1`、`T2-A1-R1`，但它们不在 commit registry，导致协议失败。
- 放大过程：重新选择同一正确 `read_file` 后，reviewer 输出常见的 `{"review_action":"approve","reason":...}` 固定工具标量形式，未被固定边界转换，最终阻塞。
- 根因：证据命名空间断裂在先，固定 review 工具表示不兼容在后。

### E2E-LH11

- 正确进展：Goal draft 已保留五阶段、40 文件、10 个 IMPORTANT fact、checkpoint 和最终 summary 的关键要求。
- 最早错误：Goal audit 在 900/700 token 上限下三次均 `finish_reason=length`，完整外层 JSON 没有闭合。
- 放大过程：重试只追加格式提醒，但输出上限更低，RWKV 继续重复冗长 reason 和 issue arrays；运行在计划前终止，Task 数为 0。
- 根因：质量任务被输出预算截断；并非 Goal 草案不可用。效率不作为目标时，应给审核足够输出空间并把权威请求放在末端。

### E2E-B24 之外的重复说明

本轮固定集只有一个 B24；其根因已在上文记录，不存在第二个同编号用例。

### E2E-M12

- 正确进展：RWKV 已完整读取 `math_utils.py` 和测试文件，两个观察 Task 均通过。
- 最早错误：进入修复 Task 时，meta `select_action` 阶段输出了直接 `read_file` 调用，随后又把 `select_action` 本身写入 `action_name` 并附带嵌套 arguments。
- 放大过程：三次输出都表达“先读取源码”，但不符合两阶段 selector 合同，最终报“selected action is not registered”。
- 根因：meta 选择层与真实工具调用层存在格式/阶段混淆；同时当前 Task 包没有强到足以压过已经完成的读取行为。该题尚未真实执行编辑，不能归因为编码能力不足。

### E2E-M16

- 正确进展：RWKV 为五个 primary item 建立并行读取 Task，三个合法文件成功观察。
- 最早错误：遇到无效 JSON 和缺失 primary 时，计划没有事先表达 fallback 发现/选择路径；失败 Task 继续固定在 `read_json(primary)`。
- 放大过程：恢复 argument call 又出现 `action/type` 重复，或把 `type` 混入已规范化 arguments，协议最终阻塞。
- 根因：异常输入的恢复前沿设计不完整，格式边界进一步阻止切换到 fallback。不能仅靠放宽 JSON 解析掩盖缺失文件分支。

### E2E-M18

- 正确进展：Goal draft 已正确表达递归 SHA256、排序相对路径、排除 `digest_map.json` 和按精确字节验证。
- 最早错误：Goal audit 反复产生超长 revise reason，三次均因 length 截断，Task 数为 0。
- 放大过程：重试降低输出上限且重复相同审核结构，没有改变失败条件。
- 根因：与 LH11 相同，是 Goal 审核输出预算/重试策略的系统性缺陷。

### E2E-H12

- 正确进展：目录和四个 shard 的读取动作都执行；T3–T5 的相同 postcondition 正确通过。
- 最早错误：T1 已取得完整目录 listing、T2 已取得 shard_01 内容，但 Task commit 分别把“listing”与“listing page”、“action observation”与“task-level artifact”人为区分，错误判断为 `open`。
- 放大过程：继续动作复制 `artifacts` 和 `observation_ref` 等当前观察装饰；`observation_ref` 未在闭集装饰中识别，三次拒绝。
- 根因：Task commit 末端缺少“成功 ACTION 输出本身就是 observation，不需要额外 artifact”的权威说明；随后常见观察装饰触发格式阻塞。

### E2E-H13

- 正确进展：初始与后续前沿共完成 doc01–doc15 的 15 个读取 Task，所有 Task commit 通过；恢复预算提高后长链没有在四轮过早中止。
- 最早错误：现有任务只覆盖部分文档且没有生成 phase checkpoint/最终 summary，Goal criterion proof 因证据不足转入 obligation replan。
- 放大过程：RWKV 一次提出 doc16–doc24 共 9 个彼此独立且可执行的读取 Task；控制器仅因“超过 8 个 immediately-ready entry tasks”拒绝整个合法前沿并直接阻塞。
- 根因：固定 `8` 上限把并行/批量读取质量任务当作协议错误。质量优先时应提高到结构可承受的闭合上限，而不能丢弃 RWKV 已生成的合法 Task。

## 环节归因矩阵

| 环节 | 直接受影响题目 | 对后续的放大 |
| --- | --- | --- |
| Goal draft/audit | LH11、M18 | 无法进入计划与执行，Task=0 |
| Task 图覆盖/可执行性 | B01、B24、M01、LH02、H13 | 产生冗余、读不存在输出、无可执行 effect、错序或合法前沿被拒 |
| Action selection/review 上下文 | B02、M06、M12、LH02 | 旧动作/旧失败压过当前 Task，或 reviewer 建议未注册动作 |
| 固定格式边界 | B02、B10、M01、M03、M06、M16、H12、LH05 | 可恢复语义被转成不可恢复协议阻塞 |
| Task evidence registry | B10、LH05 | 正确动作被记为失败，恢复进入错误路径 |
| Task commit 事实锚定 | H12；部分 B02 | 直接观察被误判为仍需额外动作 |
| 人工并行上限 | H13 | 9 个合法任务整体丢弃 |

## 下一步质量门槛

下一轮必须先修公共边界，不能增加答案筛选规则：

1. 只在唯一 `expected_name` 固定边界透明接受相同 identity、identity+内联已声明参数、固定 review 标量形式和闭集观察装饰；所有 raw/normalized payload 与转换名保留。
2. 将当前 Attempt 及其 artifact refs 全部加入同一个 Task commit registry，不生成、不替换模型选择的引用。
3. 把当前 Task、当前 ACTION 输出和 effect checks 放到决策提示最后；明确 ACTION 成功输出本身就是 observation。
4. Goal audit 使用足够输出上限；ready frontier 上限提高到已注册的结构容量，不能因第 9 个合法 Task 整批失败。
5. 单独预注册计划自审：由 RWKV 审查每个 Task 是否有 registered effect 可推进、是否读不存在输出、是否有 producer-before-consumer 依赖；控制器不修计划内容。
6. 固定 15 题至少达到 Strict `6/15`、FP `<=3`、FN `<=1`，且 B01/B02/B10 必须 Strict 通过，之后才允许运行完整 90 题。
