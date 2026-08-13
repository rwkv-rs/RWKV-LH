# Round33 Basic30 逐题、逐环节因果分析

## 固定结果

- Cases：`30`
- Strict E2E：`5/30`
- Agent completed：`7/30`
- External acceptance：`21/30`
- Strict PASS：B01、B05、B07、B14、B20
- 假阳性（Agent completed、External FAIL）：B04、B27，共 `2`
- 假阴性（External PASS、Strict FAIL）：`16`
- 进入 Goal evidence 收口：仅 B01、B04、B05、B07、B14、B20、B27，共 `7`
- 未进入 Goal evidence 收口：`23`

因此，Round33 的主要瓶颈不在最终 Goal commit：`23/30` 在更早的规划、动作提交、局部 Task postcondition 或恢复链已经失败。以下分析按“最终结果 ← Goal 判定 ← Task 完成 ← 动作 ← 规划/上下文”的方向回溯最早错误点。

## 逐题回溯

| 题目 | External | 最早错误环节 | 后续放大方式 | 根因类别 |
|---|---|---|---|---|
| B01 | PASS | 首次 Task commit 多输出字段 | 协议重试后自行纠正，没有污染结果 | 格式/输出约束摩擦 |
| B02 | PASS | 规划额外增加“验证 report.json”Task | T3 已读取正确结果，但 RWKV 把读取误判为不足；随后 replan 外壳、schema、`local_id` 连续错误而阻塞 | 过度拆分 + 恢复协议放大 |
| B03 | PASS | 正确生产后继续规划多个冗余验证/更新 Task | Task commit 使用 `rwkv-lh.task-commit.v1` 或额外字段；replan 再产生错误外壳、schema 或依赖失败 Task | 过度拆分 + 常见格式差异 + 恢复放大 |
| B04 | FAIL | 复制时写入了字面量 `immutable-source\\nline-two`，manifest 路径也写错 | 最终 Goal commit 把真实但语义不充分的引用判为通过 | 模型内容错误 + Goal 语义假阳性 |
| B05 | PASS | 无导致失败的错误 | 链路完成 | 基线通过 |
| B06 | PASS | 正确输出之后又产生冗余验证 Task | action prompt 暴露内部 `model_action` 与 snapshot 元字段；RWKV 复制为工具名/参数，纠错提示又回显错误片段，第二次继续带 `source_label/source_url` | 上下文泄漏 + 错误回显放大 |
| B07 | PASS | 无导致失败的错误 | 链路完成 | 基线通过 |
| B08 | PASS | 已创建 manifest 后仍追加验证 Task；验证 Task 首次选择了读取而非生产 | 后续 replan 格式错误；新动作继续复制 `model_action`、`source_label` | 过度拆分 + 上下文泄漏 |
| B09 | PASS | 正确写出 `stats.json` 后追加验证 Task | RWKV 把 post-action snapshot 字段复制进 `model_action`，又给 `read_json` 添加不允许的 `start_char` | 上下文泄漏 |
| B10 | PASS | “运行测试”Task 选择 `write_file` 而非 `run_command` | 局部 postcondition 正确拒绝；replan 输出 task wrapper 或错误 `1.0.0` schema，Task commit 复制完整 causal-state 对象 | 动作选择错误 + 过宽上下文 + 恢复放大 |
| B11 | PASS | 正确输出后追加验证 Task | 动作复制 `model_action`；Task commit 多字段/schema 错误 | 过度拆分 + 上下文泄漏 |
| B12 | FAIL | RWKV 算术得到 `sum=15`，正确值应为 `25` | 后续恢复扩展更多 Task，仍未纠正结果并最终阻塞 | 模型推理/内容错误 |
| B13 | PASS | 完成动作后 Task commit 仅把 schema 写成 `rwkv-lh.task-commit.v1` | 同一格式错误重复并耗尽机会 | 纯常见格式拼写差异 |
| B14 | PASS | 无导致失败的错误 | 链路完成 | 基线通过 |
| B15 | PASS | 正确输出后新增验证读取；RWKV 认为读取不能验证结构 | replan 缺 `local_id`；纠正动作复制 `model_action` 和 `source_label` | 过度拆分 + 上下文泄漏 |
| B16 | PASS | 验证动作混淆 `read_file` 与 evidence binding，加入 `start_line/end_line` | 又复制内部 `model_action`，精确参数校验拒绝 | 接口投影不紧凑 |
| B17 | PASS | 结果已正确后继续 filter/sort/count/create/verify 链 | T3 复制 `model_action`；纠错时给 `write_json` 混入 `write_file` 的 `overwrite/create_parents` | 过度拆分 + 工具 schema 混淆 |
| B18 | PASS | 首次 `write_json` 已产出正确文件，但 Task commit 使用 schema 别名 | 纠错阶段改成错误的 `content` 参数，继而混入额外写文件参数 | 格式摩擦触发语义退化 |
| B19 | PASS | 正确输出后追加验证链；读取 manifest 后 RWKV 要求重新计算源 hash 才算 Task 完成 | Task commit/重规划格式继续失败 | 过度验证 + 局部完成定义不清 |
| B20 | PASS | 中途多次重试/恢复 | 最终完成，未形成结果错误 | 可恢复通过但请求过多 |
| B21 | PASS | 早期正确动作的 Task commit 因 schema 别名/额外字段被拒 | 冗余 Task 再复制 `model_action` 和错误 `write_json` 参数 | 格式摩擦 + 上下文泄漏 |
| B22 | FAIL | RWKV 把目标 checklist 写成普通项目符号，缺少 checkbox | 恢复又把文件覆盖成 Task1..Task10 的 JSON 对象 | 模型转换错误 + 恢复破坏正确方向 |
| B23 | FAIL | primary JSON 无效后，backup 读取成功；RWKV 却称 Task 缺 completion criteria | replan 输出错误 schema `1` 后阻塞，未生成 selected.json | 局部 Task capsule 缺乏清晰契约 + 恢复格式错误 |
| B24 | FAIL | RWKV 写出的内容未正确排序、去重 | postcondition/replan 阶段未纠正并阻塞 | 模型转换错误 |
| B25 | FAIL | Goal 解析把绝对 workspace 路径写入约束并暴露给后续 prompt | RWKV 复制绝对路径；Harness 正确拒绝越过相对 workspace 协议，两次均无 Attempt | 运行时路径泄漏到模型协议 |
| B26 | FAIL | 初始任务顺序先列出尚未创建的 `output` | list 失败；failure analysis 的核心 decision 有效但附带大量 `next_*` 字段，严格解析两次拒绝，运行中断 | 规划依赖错误 + 恢复对象过宽 |
| B27 | FAIL | 只替换了精确的 `protocol=v1`，遗漏 `fallback_protocol=v1` | Goal commit 仍把引用判为通过 | 模型转换不完整 + Goal 语义假阳性 |
| B28 | PASS | 正确输出后追加写入/验证 Task | replan 先用 `rwkv-lh.task-batch.v1`，再缺 schema，最终阻塞 | 过度拆分 + 格式拼写差异 |
| B29 | FAIL | RWKV 写入占位描述 `source.txt content is observed`，没有复制真实源内容 | 后续验证/恢复继续扩展但未纠正 | 依赖内容投影不足 + 模型使用摘要代替原文 |
| B30 | PASS | 代码已正确后追加“运行测试”Task | 动作复制 `model_action`/审计字段；第二次转而写测试文件且输出不完整 | 过度拆分 + 上下文泄漏 |

## 多题共同因果链

### 1. 规划过度拆分

很多题在真实输出已经满足外部验收后，又生成单独的 verify/read/run-test Task。系统本来已经为生产动作保存真实 action result 和 post-action workspace snapshot；规划器没有清楚理解这部分观察会由运行时自动提供，于是把同一个完成事实再拆成新任务。新任务不是无害冗余：每多一个 Task，弱模型都要再经历动作选择、参数协议、Task commit 和恢复协议，错误机会成倍增加。

这不是由控制器按规则删除“看起来多余”的任务来解决；正确位置是让规划 prompt 明确运行时已有的观察能力，并让 RWKV 自己生成最小的因果前沿。

### 2. 阶段 capsule 泄漏内部结构

动作选择上下文包含与该阶段无关的字段：`action.type=model_action` 占位符、空 completion criteria、commit status、causal-state schema、snapshot 的审计元字段等。RWKV 会从输入复制局部模式，因而出现：

- 把 `model_action` 当真实工具名；
- 把 `source_label`、`source_url`、`content_included` 等观察元数据当工具参数；
- 把一个工具的参数混入另一个工具。

局部 Task commit 同样接收到过宽状态，因此经常输出 `task_commit_status`、Task id 或整个 causal-state 结构，而不是固定三字段对象。

### 3. 错误纠正提示回显了错误对象

多个阶段在第二次请求中把 rejected output 原样放回 prompt。弱模型倾向复制最近文本，导致错误字段和错误外壳连续出现。纠错提示应该只提供确定性错误类别和唯一目标 schema，不能再次提供整段错误 JSON。

### 4. 格式表示差异

存在一类真正属于格式层的问题，例如三字段 Task commit 的 `schema_version` 写成 `rwkv-lh.task-commit.v1`，而内部唯一协议要求 `long-horizon.task-commit.v1`。如果对象字段和值完整不变，可以把这个已登记的常见 schema 拼写转换为内部唯一拼写。

格式层不得：

- 删除多余字段使对象“看起来合法”；
- 补 `local_id`、schema、工具参数、criterion 或答案；
- 根据题目语义选择 action/decision；
- 修改错误的路径、数值、文本或最终回答；
- 用外部验收结果筛选 RWKV 输出。

因此 B12、B22、B24、B27、B29 等内容错误不能由格式转换修复。

### 5. 真正的 RWKV 语义错误

B04、B12、B22、B24、B27、B29 的实际 workspace 结果错误，分别涉及转义/路径、算术、格式转换、排序去重、全局替换和原文复制。这些必须通过更清楚的任务与真实依赖内容投影，提高 RWKV 做对的概率；架构不能把错误结果改成正确结果。

### 6. Goal 收口仍有假阳性

B04 与 B27 都进入了新的 Goal 收口阶段，并且 RWKV 选择的引用真实存在，但内容语义不满足 criterion。Round33 的引用完整性校验只证明“证据真实且来自成功因果链”，不能证明“RWKV 对证据语义的判断正确”。控制器不能通过关键词规则或隐藏验收反向否决模型；后续只能改善 Goal 判断时的证据呈现和模型提问方式，并保持决定来自 RWKV。

## 对下一步结构的约束

1. 格式转换层保持纯转换：只处理预登记的常见外壳或 schema 拼写，输出一个内部形状；转换前后 payload 和变换记录可审计。
2. 每个模型阶段使用独立、最小的 deterministic capsule；动作阶段不再看到内部占位 action、状态机字段和与工具无关的审计字段。
3. dependency observation 区分“原始内容”和“摘要/审计元数据”；需要复制或计算时必须把真实内容明确呈现，不能让摘要冒充数据。
4. 纠错 prompt 不回显 rejected JSON，只说明拒绝原因与唯一合法协议。
5. 规划器知道 action result 与 post-action snapshot 会自动生成，避免把生产后的同一验证事实重复拆成 Task。
6. 绝对 workspace root 只属于运行时，不进入模型可见 Goal 约束；模型协议统一使用相对 scope `.`。
7. Goal 收口仍只由 RWKV作语义决定；改善 criterion 与证据的逐项呈现，但不得由 controller 补答案或根据外部验收翻转结果。

## 结论

Round33 已证明“Goal 判断阶段后移”能消除中间 Task 的提前证据污染，但 Basic30 的 `5/30` 不能上传为更优稳定版本。当前最大的系统性缺陷是模型阶段之间没有真正隔离：过宽状态和 rejected output 被反复投影，诱导 RWKV 复制内部协议字段；规划又增加不必要的任务，把一次可完成的工作放大成多次协议风险。下一轮应先独立验证纯格式别名的有限收益，再实施阶段专用紧凑 capsule，避免把两类因果变量混在一次实验里。
