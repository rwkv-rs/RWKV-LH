# Round75 预注册协议：原始 Goal 直通与单一进度决策

## 依据与目标

Round74 offline 全部通过，但真实 short7 仅 Strict `2/7`、External `3/7`、Agent `2/7`、FP `0`、FN `1`。逐请求因果分析见 `Round74_canary/MANUAL_CAUSAL_ANALYSIS.md`。

本轮不再维护旧字段或旧调用次数的可比性。唯一目标是提高真实 RWKV Agent 的最终质量，同时保持：RWKV 自己选择 Task、动作、参数、完成决定和最终答案；程序不读取隐藏验收来指导运行，不选择或改写模型的语义输出。

## R75-1：用户请求是唯一 Goal 权威

- 删除生产入口的 RWKV `goal_commit` 重写。Goal objective 与唯一语义正文逐字使用用户原始请求；caller scope/safety constraints 作为独立运行约束保存，不能被模型扩写成用户验收条件。
- 不再让模型生成 success-criteria 列表。若当前持久化 schema 过渡期仍要求一个 criterion，只保存一个对原始请求的逐字引用；它不进入独立 criteria/obligation 状态机。
- 保存原始请求 digest、workspace scope 和 caller constraints。不得从题目、路径或隐藏 acceptance 生成额外目标字段。
- 因果预期：消除 B10 的“pytest”注入和 M03 的“不得原地修改/必须备份”伪条件。

## R75-2：一个完整初始 Task DAG，不再要求仅 discovery frontier

- 初始 `task_decomposition` 仍由 RWKV 一次提交，但改为覆盖整个当前可表达的因果 DAG，而不是只提交最小 discovery frontier。
- 内容未知时，RWKV可以创建读取 Task 以及依赖该读取的抽象 producer/verify Task；后者的动作参数在真实 observation 到达后才决定，不得提前猜值。
- planner 继续看到紧凑 action effect catalog 和批量 `read_files` 能力。
- 程序只校验闭合 Task schema、DAG、数量与 workspace scope，不补 Task、不改依赖、不推断答案。
- 因果预期：M12 初始 plan 不再只生成两个重复 directory-list Task。

## R75-3：Task completion 与下一 action 合成一个 RWKV `task_step`

- 每次真实 action observation 后，只调用一次 `task_step`。RWKV必须二选一：
  - `decision=complete`：给出直接建立整个 Task postcondition 的当前 evidence refs；
  - `decision=act`：给出下一个注册 action name、原因以及引用的当前 evidence refs。
- `act` 后只再调用一次固定 action 的 argument boundary；不重新采样 action name。
- 第一个 action 仍由相同 `task_step` 合同在“无 current observation”状态下选择。没有现存 evidence 时不得返回 complete。
- 删除生产路径上的 `task_postcondition_commit -> action_name_selection` 分裂链。程序不把 `open` 解释成下一动作，也不覆盖 RWKV 选择。
- 因果预期：M01/M06/M12 中“准确说 read 不足，下一调用却再次选 read”的矛盾不再跨请求发生。

## R75-4：唯一 Task-local 状态与紧凑失败 delta

- Task packet 只包含：逐字 Goal、active Task、该 Task 的有序 attempt ledger、直接依赖 observations、该 Task 当前 observations、一个紧凑 last-step delta、action effect catalog/fixed schema。
- last-step delta 只保留 `attempt_id/action/outcome/tool_success/workspace_digest/task_decision/reason`；不嵌入完整 validation results、evidence object、Goal digest副本或 recovery parent prose。
- 新 recovery Task 不继承被替代 Task 的自由文本 failure 作为自己的 authoritative last failure。跨 Task 只通过显式 dependency observation 传递事实。
- 同一事实在一个 prompt 中只出现一次；完整原始 observations 仍保存在 append-only trace/state，并在当前 Task evidence 区无损提供。
- 因果预期：消除 M01 的 state-envelope 回显锚定和 M12 T9 复制 T5 listing failure 的跨 Task 污染。

## R75-5：同状态重复 action 不执行，由 RWKV自行改选

- 若 RWKV在相同 workspace digest 下再次提交相同 idempotent action+arguments，Harness 不执行第二次。
- 系统追加一个确定性 `duplicate_no_progress` observation，记录原 attempt/ref/fingerprint，并再次调用 `task_step`；它不推荐替代 action，不生成参数或答案。
- 重复决策消耗固定 Task step budget；达到上限才进入一次 Task replan，不把成功 read 误标成 transient tool failure。
- 外部状态、非幂等 action 或 workspace digest 已变化时不得使用该抑制。
- 因果预期：M06 的 6 次 selection.txt 重读、M12 的同文件重读和 B01 的重复验证不再真实执行。

## R75-6：移除 criteria-driven goal-obligation 状态机

- 当当前 required Task graph完成时，只发一个 `goal_frontier_step`：基于逐字用户请求、当前 workspace manifest、完成 Task索引和真实 observations，返回：
  - `decision=finish`、非空原因；或
  - `decision=continue`、一个完整的下一 Task frontier。
- 不再逐 criterion 生成 gap、evidence draft/review、proof claim 或第二套 obligation ledger。
- `continue` proposal 与同一 workspace 下已完成 Task语义完全重复时，确定性拒绝为 no-progress，并把冲突 signature 反馈给下一次 RWKV frontier step；程序不生成替代 Task。
- `finish` 后再由 RWKV产生一次自由文本 final answer；返回值必须逐字等于该 raw visible output。
- 因果预期：B01 不再把一次成功 read扩张成五次验证；M03/M12 不再复制 stale Task链。

## R75-7：格式边界

- 不建立“允许哪些附加字段”的格式白名单，也不为每种模型输出维护一条规则。
- 只实现一个简单、通用、纯语法转换层：在模型 payload 的常见对象/函数外壳中查找唯一的 `工具名 + arguments object` 调用，将它投影为内部唯一的 `{name, arguments}` 格式。
- 转换器不读取 Task语义，不选择工具，不补参数，不删除或改写 arguments 内的键值，也不判断该动作是否正确。外壳中的其他内容只作为原始 payload审计保存，不进入 action arguments。
- 找不到调用、找到多个不同调用、工具名冲突、arguments 不是对象或内部参数合同无效时拒绝。拒绝依据是“无法唯一转换”，不是附加字段是否命中白名单。
- Task decision、evidence refs 与 final answer 使用各自的闭合协议，不经过工具格式转换层。
- 本项不得掩盖错误的重复 read：转换成功只表示格式可接入，不表示动作语义正确。

## 明确不做

- 不添加题号、路径、字段值或标准答案特判。
- 不使用 Codex/外部模型选择动作、修复代码、判断完成或重写最终答案。
- 不读取隐藏 acceptance、verifier target 或标准答案作为模型/控制器输入。
- 不添加 MCP、搜索服务、subagent、answer ranker 或 state-embedding action router。
- 不因效率改动采样参数；本轮仍以质量为唯一上线指标。

## 离线验证

- 新活动路径测试证明生产入口无 `goal_commit` 模型请求，Goal正文逐字等于用户请求。
- `task_step` 单次响应同时决定 complete/act；act 后不得再出现 action-name selector。
- 新 Task看不到 parent Task自由文本 failure；当前 observation 与 ledger payload不重复。
- 同 digest/idempotent fingerprint 的第二次调用不进入 Harness；workspace变化后可执行。
- graph完成后只有 `goal_frontier_step`，生产事件中不存在 criteria gap/goal-obligation/evidence draft-review 链。
- 全 pytest、compileall、diff check、LH-Control30、冻结目录/reference 与 31文件控制器回归。

## 在线顺序与门槛

1. 仍先跑固定 short7：B01、B02、B10、M01、M03、M06、M12。
2. 必须逐题记录最早错误与放大链；不得只看脚本总分。
3. short7 继续条件：Strict `>=4/7`，且 B01/B02/B10 全部 Strict，FP `<=1`、FN `<=1`。
4. 达标后跑 H12、H13、LH11、LH02；fixed15 门槛仍为 Strict `>=6/15`、FP `<=3`、FN `<=1`。
5. full90 上传门槛不变：Strict `>31`、External `>=32`、FP `<24`、FN `<=1`，final output 与 raw RWKV visible output逐字一致。

当前最佳已上传基线仍为 commit `14d864d71bf670b479a33f4fdb63b4772b69d3c8`：Strict `31/90`、External `32/90`、Agent `55/90`、FP `24`、FN `1`。未达到完整上传门槛不得提交或上传 Round75。
