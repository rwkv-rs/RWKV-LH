# Round23 已中止候选协议：协议不相交的 workspace observation 投影

> 状态：`aborted_before_run`。没有发出任何 Round23 RWKV 请求。逐条检查 Round22 请求后发现，
> 本候选把聚合相关性误当成单一根因：29 条 snapshot-exposed action failure 中只有一部分直接复制
> snapshot 字段，更多输出融合了 ACTIVE TASK、generic memory 与 G1i 三套结构；同时第一次 parser /
> normalization 异常会逃出既有两次纠错循环。必须先完成人工逐题全链分析，再重新决定 Round23 变量。

预注册日期：2026-08-13。本文档在 Round23 实现修改和任何 Round23 RWKV 请求之前冻结。

## Round22 基线与根因

- Strict `0/90`；External `19/90`；Completed `0/90`；FP `0`；FN `19`。
- 分组 External：Basic `17/30`、Medium `1/30`、Hard `1/30`；历史最好仍为 Round16 `24/90`。
- Round22 的 117 个内部 post-action snapshot 均通过真实 workspace bytes、artifact hash、原 action
  output 不变和隐藏答案隔离检查。8 条 snapshot 真正进入后继同目标 action prompt 的链均保持原字节。
- 但模型可见 snapshot 使用 JSON 字段 `action_type`、`content`、`path`，并继续附带
  `artifact_refs`、`evidence_refs`。snapshot-exposed tool_action 失败 `29/192`（`15.10%`），未暴露时
  `8/387`（`2.07%`）；Round22 action materialization failure 为 37，Round21 为 8。
- 29 个 snapshot 暴露后的失败全部解析出顶层 `action` 或 `action_type` 风格外壳且未被现有透明
  normalization 接受。该结果是全量盲态数据上的强关联，不宣称为随机对照下的独立因果效应。

## 唯一结构变量

名称：`protocol_disjoint_workspace_observation_projection.v1`。

只修改 `WorkingMemoryBuilder` 对 `post_action_workspace_snapshot` 的模型可见序列化：

1. Controller 内部 snapshot `MemoryEntry.content` 继续保留 Round22 的完整 JSON、真实 UTF-8 bytes、
   hash、size、media type、relative path 和 omission metadata；snapshot 创建、审计事件、ID、归属、
   output refs、依赖选择和持久化格式全部不变。
2. 对 RWKV 投影时，先严格解析内部 snapshot。外层不再展示 snapshot JSON，也不展示 generic
   memory 的 `kind=...`、`summary:`、`content:`、`artifact_refs:`、`evidence_refs:` 行。
3. 模型可见外层固定为非 JSON 的定界 observation：memory ID、producer task、relative file、SHA-256、
   byte count、media type、UTF-8 body 是否存在，以及 BEGIN/END 定界符。外层不得把 `action`、
   `action_type`、`arguments`、`content`、`path`、`name`、`tool_calls` 用作字段标签，也不暴露 producer
   action type。
4. 若 content included，则 BEGIN/END 之间逐字符放入内部 snapshot 已记录的 UTF-8 文件正文，不解析、
   重排、清洗、转义、补全或修改正文。正文自身可以合法包含任意 JSON key；架构不得因正文值不同而
   选择不同处理方式。
5. 若内部 snapshot 缺字段、格式非法或声明与 content 不一致，模型投影失败关闭为不含内部 JSON 和
   正文的 `WORKSPACE OBSERVATION UNAVAILABLE`，不得回退到 generic memory projection。
6. dependency/evidence 选择、token budget、截断顺序和所有非 snapshot memory 的序列化保持 Round22
   不变。

除上述模型边界表示外，不修改 Goal、plan、action catalog、G1i normalization、sampling、任务排序、
恢复预算、proof、CriterionEvidence、完成判定、Harness 执行或评分。

## 不作弊边界

- observation 只展示 RWKV 已经执行写操作后真实存在的 workspace bytes，不含标准答案或 grader 信息。
- 不根据正文是否正确决定是否展示，不保护正确值，不阻止覆盖，不选择 action，不生成参数或 expected。
- 不新增 `{"action": ...}` 等外壳兼容规则来挽救本轮输出；这样可以单独检验输入表示修复，而不是用
  更多规则筛选 RWKV 答案。
- 不修改 raw/parsed/normalized action 记录或 RWKV final output。

## 预注册验证

### 单元与对抗边界

- 内部 snapshot JSON 在修改前后逐字节相同；模型可见投影不包含内部外层 JSON 或禁止字段标签。
- UTF-8 正文逐字符可在投影中定位；前后 metadata 不混入正文。
- 正文本身分别包含 `action`、`action_type`、`arguments`、`content`、`path`、`name`、`tool_calls`、
  G1i call 示例和定界符文本时，正文仍原样保留，处理策略不变。
- content omitted、malformed JSON、hash/size/path/content 类型异常均失败关闭且不泄漏内部 JSON。
- 直接依赖可见、非依赖隔离、token projection、save/load、并发和 Round22 snapshot 审计回归继续通过。

### 冻结回放

- 对 Round22 的 117 个 snapshot 重建新投影，验证内部 payload/hash 不变、117/117 外层协议不相交、
  included content 逐字符保留。
- 对 Round21 冻结的 26 条状态链继续做 score-independent replay；直接依赖链应获得新 observation，
  历史 artifact hash/size 与 snapshot bytes 不变。
- Round18 proof、Round19 obligation、Round20 proof-pass replay 保持原结果。

### 全量回归

- 全产品 pytest、LH-Control `30/30`、RWKV-E2E-90 validate-only。
- 正式运行完整保留 request prompt、raw output、parsed payload、normalization、event、state timeline、
  artifact hash、snapshot internal payload 和 model-visible observation 的逐请求关系。

## 正式实验与评价

- endpoint：`http://127.0.0.1:29610/v1`；模型：
  `rwkv7-g1i-13.3b-20260805-ctx16384`；context `16384`。
- 固定 E2E-90，Basic/Medium/Hard 各 30；并发 8；最大 transitions 200；采样参数与 Round22 相同。
- 90 题全部终止前不读取 hidden acceptance、standard answer 或 Codex reference；先冻结结果哈希并完成
  盲态协议/生命周期/状态链分析，再解封标准答案。
- 首要因果指标：snapshot-exposed tool_action action-materialization failure 的次数和比例、非 snapshot
  对照比例、顶层 wrapper 类型、snapshot exact visibility/state preservation，以及后继 producer/recovery
  是否继续执行。
- 同时报告 External/Strict/Completed/FP/FN、难度分组、首个正确 target、后续覆盖、请求数、token、
  witness/proof/evidence 漏斗；不能只用协议通过率判定架构更好。

## GitHub 晋级

保持既有门禁且运行后不修改：FP=0、Strict>7、Completed>7、External>=24、全部回归通过、output
non-intervention 成立。若只修复协议碰撞但完整门禁未过，则记录 `do_not_upload` 并继续下一轮。
