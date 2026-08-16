# Round73 预注册协议：事实约束计划、直接执行与紧凑 live state

## 目标

Round73 针对 Round72 fixed15 人工逐题分析确认的四个公共结构根因：计划不受事实/effect 约束、pre-execution action review 与 Task completion 混淆、当前事实未形成末端状态胶囊、少量常见 G1i state-echo/meta-selector 格式仍被拒绝。

本轮质量优先；请求数、耗时、token 与并发效率只记录，不参与判断。控制器不得选择、修正、补写或改写 RWKV 的 Task、动作参数、证据结论和最终答案。

## 冻结输入与基线

- 已上传完整基线：commit `14d864d71bf670b479a33f4fdb63b4772b69d3c8`，Strict `31/90`、External `32/90`、Agent `55/90`、FP `24`、FN `1`。
- Round72 fixed15：Strict `2/15`、External `2/15`、Agent `2/15`、FP `0`、FN `0`。
- 人工证据：`Round72_canary/MANUAL_CAUSAL_ANALYSIS.md`。
- 固定题目、模型、endpoint、采样、并发、transition 上限和相似度算法不变。
- 运行后不得读取隐藏 acceptance 或 Codex 标准答案来修改本轮方案。

## R73-1：RWKV plan audit/commit

初始 Task frontier 通过结构校验后，必须再由 RWKV 在一个固定 `commit_plan_audit` 边界返回完整最终 Task frontier：

- `decision=approve|revise`、非空 `reason`、完整 `tasks`；
- 每个 Task 仍只有 `local_id/title/description/dependencies/postcondition`；
- `approve` 时 tasks 必须与 proposed tasks 逐字段相同；`revise` 时保存 RWKV 返回的完整 tasks；
- raw proposed/reviewed payload、digest、decision、reason 和 changed 标志全部持久化；
- 控制器只做 schema、Task ID、DAG、闭集数量和注册合同检查，不添加、删除、重排或改写 Task。

RWKV 审计问题固定为：

1. 当前 frontier 是否只依赖 immutable Goal、initial manifest metadata 和已观察事实；不得在读内容前猜内容派生值/分类。
2. 每个 postcondition 是否可由一个或多个注册 action effect 推进；不得创建无持久化载体的纯内存变换。
3. consumer 是否依赖 producer；不存在的输出不得先读。
4. 数据派生 mutation 是否依赖对应 observation；list metadata 不能充当文件内容。
5. Goal 中的路径、字段、数量、保留/删除合同是否逐字保持；不得增加用户未要求的中间产物作为完成条件。

本轮先对初始 frontier 量化；goal-obligation/recovery frontier 的同一审计复用作为后续扩展项，不用控制器规则替代。

## R73-2：移除 pre-execution 语义 action review

动作链改为：

`RWKV select_action -> RWKV fixed action arguments -> deterministic schema/scope/safety validation -> execute -> real observation -> RWKV Task postcondition commit`。

删除 `review_action` 语义 gate 和三轮 selector/reviewer 回声。原因不是降低安全性，而是 Round72 的 H12/M16 已证明该 gate 会把“Task 尚未完成”错误解释为“正确的下一次 action 不应执行”。

- action name 和 arguments 仍完全来自 RWKV；
- workspace scope、工具 schema、`shell=False`、路径与副作用限制不变；
- 控制器不批准/拒绝动作语义，只校验能否安全按原样执行；
- Task 是否完成只在 action 产生真实 observation 后判断。

## R73-3：确定性 live action frontier

在 action selection 与 fixed arguments 的响应边界末端加入相同的确定性状态胶囊：

- active Task 的完整五字段合同；
- dependency observations 的原文/无损结构投影；
- 当前 Task 的有序 Attempt ledger，包括已执行 action、路径、outcome、artifact hash 和 Task decision；
- 最近 material failure；
- capsule digest。

胶囊只重排已持久化事实，不生成“剩余文件”“正确值”“推荐动作”或自由文本摘要。旧 execution capsule 仍可保留，但末端 live frontier 是当前决策的唯一权威包。

## R73-4：透明协议边界 v12

只注册 Round72 已重复出现的两类表示：

1. `select_action` 固定边界接受 `{"action":"<registered>","reason":"..."}`，只把字段名 `action` 改为 `action_name`，值和 reason 原样保留。
2. canonical `action+arguments` 外层允许分离闭集 state-ledger echo：`attempt_count`、`attempts`、`projection`、`schema_version`、`task_decision`、`task_decision_reason`，并延续已注册的 artifact/task/workspace decorations。每个字段严格校验固定 JSON 类型，不进入真实 action arguments。

raw/normalized payload、双 digest、转换名和 normalizer v12 必须记录。冲突 identity、未知字段、错误类型、未注册 action 或缺参数继续 fail closed。

## R73-5：本轮不做

- 不接 MCP、搜索服务或外部 provider。
- 不引入外部模型、规则 router、answer selector/ranker 或 hidden-state 路由。
- 不把 task title、用户输入摘要或搜索摘要当 Goal/验收事实。
- 不实现自由 summary 作为事实源。RWKV-only、绑定 raw refs 的 file-local/search-result-local 派生 observation 留到 P1 独立实验。
- 不针对 fixed15 题号、路径或答案写特判。

## 离线验证

- 全量 pytest、compileall、LH-Control `30/30`、frozen catalog/reference 和 31-file parallel summary 回归。
- 新增：
  - plan audit approve 保持逐字段一致；revise 的完整 RWKV tasks 被保存；approve+changed、未知字段、坏 DAG fail closed；
  - propose_action 不再发 `action_commit_review`，提交事件标记 direct execution；
  - live frontier 位于 selection/argument prompt 末端，包含 dependency observation、attempt chronology 和 digest；
  - selector `action -> action_name` 只在固定 select boundary 转换；
  - state-ledger echo 的合法类型成功分离，未知/错误类型继续失败。

## 在线门槛

- fixed15：Strict `>=6/15`、FP `<=3`、FN `<=1`，且 B01/B02/B10 全部 Strict。
- 逐题人工记录最早错误；重点验证 B10 正确写入是否执行、H12 shard13 是否执行、M16 正确 fallback read 是否不再被 reviewer 拦截、M01/H13 是否不再在观察前猜内容派生值。
- 未达门槛不运行完整 90。
- 达标后完整 90 必须 Strict `>31`、External `>=32`、FP `<24`、FN `<=1`，且最终输出逐字节等于 raw RWKV，才允许提交上传。

