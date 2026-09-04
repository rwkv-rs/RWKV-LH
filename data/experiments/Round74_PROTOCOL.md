# Round74 预注册协议：单一语义脊柱与无重复 action packet

## 目标

Round73 fixed15 仅完成 14 题，Strict `1/14`，且 `E2E-LH02` 在 revision `3669`、Task `88`、Attempt `112`、SQLite `2.1G` 时仍未收敛。人工逐题分析确认，主要失败不是工具缺失，而是同一个 RWKV 语义在 `draft -> audit/review -> final` 中被重复采样，并且 action 请求同时携带 execution capsule、dependency/evidence 副本和新增 live frontier，导致控制提示污染、旧 read 锚定、ledger 回显和重复恢复。

本轮只做协议脊柱减法，不引入规则答案、控制器 action selector、隐藏 acceptance、外部模型或最终输出修订。所有 Goal、Task、action、Task completion 和最终答案继续由 RWKV 产生。

## 冻结基线与输入

- 已上传最好完整基线：commit `14d864d71bf670b479a33f4fdb63b4772b69d3c8`，Strict `31/90`、External `32/90`、Agent `55/90`、FP `24`、FN `1`。
- Round72 fixed15：Strict `2/15`、External `2/15`、Agent `2/15`。
- Round73 已完成 14 题：Strict `1/14`、External `2/14`、Agent `1/14`、FP `0`、FN `1`；LH02 中断，不计入分母。
- 固定模型、endpoint、sampling、数据集、隐藏 verifier、相似度算法、case 并发和 transition 上限不变。
- 结构冻结后才运行在线题；不得读取隐藏 acceptance 或 Codex 标准答案来修改本轮方案。

## R74-1：单次 Goal commit

- 删除 `goal_draft -> goal_audit -> goal_final` 三次同模型回声链。
- 每次 run 只发一个 `goal_commit` 请求；协议重试只在 JSON/schema 无效时发生，不因语义不满意重采样。
- prompt 只包含 immutable user request、caller constraints、workspace scope 和一个紧凑 Goal 合同；不出现 `DRAFT`、`audit`、`review` 或要求模型填满 criteria 上限的文字。
- RWKV 返回完整 objective、constraints、success criteria；程序只校验闭合 schema、类型、非空和最大安全容量，不改写语义。
- 保存完整 prompt、raw output、parsed payload、sampling 和协议错误/重试记录。

## R74-2：单次 Task frontier commit

- 删除 `task_decomposition -> commit_plan_audit` 的第二次同模型 plan 审查。
- 初始 frontier 只保留一个 `task_decomposition` 语义请求；协议无效时仍允许结构纠错重试。
- planner 看到每个注册 action 的紧凑 effect、read-only/side-effect、批量能力和参数名，而不是只看到 action 名称；特别明确 `read_files` 能一次读取最多 64 个显式路径。
- frontier 总 Task 上限为 32，但 prompt 要求最小的下一可执行 frontier，并优先用批量 action effect 表达批量读取；内容未知时只提交 discovery barrier。
- 程序只校验 Task schema、DAG、数量和 workspace/action contract，不添加、删除、重排或修复 Task。

## R74-3：唯一 action authority packet

- action selection 与 fixed arguments 各只注入一次 `ContextBundle.to_prompt()`；删除追加的 `live_action_frontier`、重复 active Task、重复 dependency/evidence 和旧 execution capsule副本。
- action packet 固定顺序：immutable Goal -> active Task -> ordered current-Task attempt ledger -> direct dependency observations -> last material failure -> compact action catalog/fixed action schema。
- `build_action_commit` 中，current Task 的完整 observation 只在 evidence 区出现一次；ordered ledger 只保留 action identity、status、fingerprint、outcome、Task decision 和 workspace digest，不再复制 `observed_content`、metadata 或 artifacts。完整原始 observation 同时保存在 append-only state/model trace，可由引用审计，但不会在同一 prompt 中重复注入。
- prompt 明确：相同 workspace digest 下，若同一 idempotent action+arguments 已执行且 Task decision=open，不应再次选择；RWKV 必须自己选择不同动作或说明无法推进。控制器不替它选择下一动作。
- 每次 action request 仍保存完整 prompt/raw/parsed/normalized payload、ContextBundle、digest 和所选 action。

## R74-4：单次 Task postcondition commit

- 删除 `task_postcondition_draft -> task_postcondition_commit` 双次同义判断。
- 每个 action observation 之后只发一次 `task_postcondition_commit`；协议无效时才做格式纠错重试。
- evidence registry、当前 action result、deterministic effect checks 和单一 Task validation capsule只各出现一次。
- pass/open 及 evidence refs 完全来自 RWKV；程序只校验引用存在、pass 至少有一个引用，以及闭合 schema。

## R74-5：保留项与明确不做

- 保留 Round73 已有正向证据的直接执行链：`select_action -> fixed arguments -> deterministic schema/scope/safety validation -> execute -> observation -> Task commit`。
- 保留少量已登记透明格式归一化 v12；不继续为 arbitrary ledger envelope 增加白名单。
- 本轮不添加 source quote/effect-target 语义规则，不从 Task 文本推断 mutation、集合成员或答案；先测量单一脊柱本身的因果效果。
- 本轮不做 MCP、搜索服务、subagent、state-embedding router、外部模型、答案 ranker 或 controller-generated summary。
- 最终输出必须逐字等于 RWKV raw final output。

## 离线验证

### 在线运行前的实现澄清

本澄清在任何 Round74 在线题运行前登记：原计划写成“current Task observation 不放入 evidence、摘要只在 ledger”，实现检查发现这会牺牲模型读取文件原文的质量。最终实现采用“完整 observation 在 evidence 一次、ledger 仅保留因果索引”的唯一事实投影。它不改变去重目标、评价门槛或数据集，只避免为了协议形式丢失模型完成任务所需的真实内容。

- 完整 pytest、compileall、`git diff --check`、LH-Control `30/30`、frozen catalog/reference 和 31-file结构回归。
- 新增或更新回归以证明：
  - 正常 run 只有一次 Goal 语义请求，且 prompt 不含 DRAFT/audit；
  - 初始 plan 不再调用 `commit_plan_audit`，且 action effect catalog 包含 `read_files` 批量合同；
  - action selection/argument prompt 中只有一个 active Task、一个 attempt ledger、一个 dependency observation section，不含 `live_action_frontier`；
  - action commit ContextBundle 的 current Task observation 不在 ledger/evidence 两处重复；
  - Task postcondition每个有效 observation只产生一次语义请求；
  - raw/normalized/final-output 不干预保证继续通过。

## 在线顺序与门槛

1. 先跑短链固定七题：B01、B02、B10、M01、M03、M06、M12。
   - B01、B02、B10 必须 Strict；
   - 不得再出现 Goal objective 复制 DRAFT 控制提示；
   - action prompt 不得回显完整 live frontier；
   - 相同 read fingerprint 的无进展重复次数要逐题记录。
2. 再跑长链四题：H12、H13、LH11、LH02。
   - H12/H13 必须继续证明批量/多文件读取可以执行；
   - LH02 不得再次出现无界重复 Task frontier，运行到上限时必须完整落盘而非假装通过。
3. fixed15 总门槛：Strict `>=6/15`、FP `<=3`、FN `<=1`。未达标不跑 full90。
4. full90 上传门槛：Strict `>31`、External `>=32`、FP `<24`、FN `<=1`，且 raw final output逐字一致。

效率指标只记录，不作为通过条件；但 runaway、状态无法收敛或数据无法完整落盘属于质量失败。
