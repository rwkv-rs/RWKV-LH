# Round12 预注册：RWKV Witness-Intent Lifecycle

预注册日期：2026-08-12（任何 Round12 RWKV 请求之前）

## 固定依据

Round11 在解除初始完整 criterion 覆盖硬门后，真实 RWKV-E2E-90 得到
External `18/90`、Strict `0/90`、Completed `0/90`、FP `0`、FN `18`。
90 题共有 232 次 criterion assertion evaluation，但 82 条已生成 claim 全部被拒绝，
最终 VERIFIED CriterionEvidence 为 0。主要直接拒绝原因是：

- 非直接依赖引用 58 次；
- transform contract 无效 30 次；
- JSON Pointer 非 RFC6901 格式 17 次；
- JSON Pointer key 不存在 6 次；
- 无参数 action-output operator 被填入多余参数 7 次。

这些不是五类互不相关的缺陷，而是同一个生命周期问题：RWKV 在任务动作完成之后，
才被要求同时决定 semantic pass、criterion ownership、actual/expected source、底层 source ID、
JSON Pointer 和 transform；结构错误只能在 ProofEngine 末端暴露，随后又被通用 failure recovery
放大为动作重跑和 goal obligation 扩图。

- Round11 results SHA-256：`dedcc2db250b3a563d5cb6271596a2a941a4ca6900452cdf631b24164fbeedbf`
- Round11 专项因果 JSON SHA-256：`4338b6e2698368a56777856bf3da50fc0bd27f05a23dd1647de3efc512a2373e`
- Round1--Round11 反向因果 JSON SHA-256：`c915bf7360ab6ff8e8ac9db95dfab26012203e807517638b9dda982895954463`
- Round11 通用因果 JSON SHA-256：`30ba0f311f6812fb3256875851af95ae0454bef77cf1f25fef409dd7fb4c5cb1`
- RWKV-E2E-90 v1 manifest SHA-256：`6c0378fdb0e876ae6acf0350273726d5a68060c79f8421a84acbd76ea842d885`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`

## 唯一结构变量

实施 `rwkv_witness_intent_lifecycle.v1`，用一个持续、可恢复的 RWKV 证据意图生命周期
替换 Round11 的事后 `criterion_assertion_intents -> per-claim complex binding` 生命周期：

1. 对每个显式 `satisfies_criteria` 的任务，RWKV 在动作执行前为每个 criterion 提交一个
   WitnessIntent：criterion、subject、producer、`exact_equals`、actual source kind、expected source
   kind；若 expected 是 Goal literal，Goal 精确 quote 和 typed value 也必须由 RWKV 提交。
2. Controller 只验证字段、Immutable Goal criterion ID、任务作用域、直接依赖关系、source kind 枚举、
   Goal quote 是否为原请求的精确非空子串，以及一 criterion 一 intent。它不得推断、补齐、替换或排序
   RWKV 的语义选择。意图与全部修订历史持久化到权威 RunState。
3. 动作返回后，系统从本次 raw action result、完整作用域 workspace、全部直接依赖 artifact/memory，
   以及 RWKV 自己声明的 Goal literal，确定性生成不透明 WitnessHandle 目录。目录按来源完整枚举；JSON
   子值使用实际存在的 RFC6901 path；既有 proof transform 只按输入类型枚举所有合法应用。不得读取
   hidden acceptance、Codex reference、相似度或 criterion 文本来生成、过滤、排名 handle。
4. 每个 handle 保存 source owner、read operator、原始 arguments/transforms、source/value hash、value type、
   有界可见值和 catalog digest。RWKV 只选择 actual/expected handle ID；系统仅做逐字 ID 展开，不能尝试
   备选 handle、交换两侧或修改 transform。
5. ProofEngine 继续执行现有独立来源、直接依赖、hash、typed exact equality 和 provenance 检查。
   Proof 失败时，精确机器错误和上次 RWKV 选择返回同一个 task-local RWKV lane，最多允许 2 次
   witness binding 修订；修订只可改变 RWKV 的 handle 选择或显式 WitnessIntent，不重跑已成功 action，
   也不自动增加任务。只有 RWKV 明确返回 `replan` 或局部预算耗尽后，才进入原有 recovery。
6. 每一步记录 pre-action prompt/raw/parsed/normalized intent、意图状态迁移、完整 handle catalog 与 digest、
   RWKV raw binding、逐字展开结果、proof input/output/error、修订前后 diff、最终 evidence commit。
   恢复后相同 attempt 必须重建相同 catalog digest；否则 fail closed。

这六点是一项变量，因为它们共同定义一个从“证据意图预承诺”到“透明绑定、局部修订、证据提交”的
单一生命周期；不得同时改 Goal 容量、任务计划、动作选择或最终答案策略。

## 不作弊边界

- criterion 的含义、producer/subject、来源类别、Goal literal typed value、handle 选择、semantic pass/replan
  和最终答案始终由 RWKV 决定。
- 系统可以做的仅是穷举当前作用域内已经存在的原始读法及类型合法 transform、分配不透明 ID、验证
  schema/scope/hash/type，并逐字展开 RWKV 所选 ID。
- handle 枚举不得依据 criterion 描述、hidden acceptance、Codex reference、历史正确答案、外部通过结果
  或相似度；不得只暴露“看起来正确”的候选，不得自动选择相等值。
- 系统不得增删改查 RWKV 的最终答案；final 仍为 byte-exact raw RWKV 输出。
- Codex reference 和 acceptance 只在正式 E2E-90 全部结束后用于结果对比和因果归类。

## 明确不改

- Goal parse 的 1--5 criterion 上限、初始 task decomposition、persistent goal-obligation lifecycle、
  goal recovery budget 3、action catalog/G1i action protocol、deterministic verifier、failure analyzer、
  sampling、并发 8、max transitions 200、数据集、外部验收和相似度算法不改。
- 不增加 verifier，不增加 obligation budget，不从 witness 失败自动生成任务，不修改动作输出或 workspace
  来让 proof 通过。
- Round11 之后修复的 StateCapsule 实际 token `<=5000` 且 recorded token 等于实际 token 的边界修复保留，
  但不作为 Round12 E2E 变量计分。

## 固定数据与运行

- 数据：RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；Codex reference 仅 post-run 使用。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`，`vllm-rwkv-rapid`。
- 并发：8；max transitions：200；sampling 继承 Round11。
- 正式运行前：完整产品测试、LH-Control-30，且不得发生正式数据生成。
- 正式运行后：同一冻结实现再次运行完整产品测试和 LH-Control-30；必须生成 90/90 audit、
  model trace、event log、state timeline、raw final equality 和 Codex reference 对比。

## 预注册结构诊断门

Round12 结构变量成立必须同时满足：

- pre-action WitnessIntent 对所有进入 criterion validation 的 task/criterion 精确覆盖；恢复投影一致；
- handle catalog 不使用 criterion/reference/acceptance，catalog digest 可重建且完整审计；
- Round11 的 `not_direct_dependency`、非法 JSON Pointer、无参数 operator 多余参数和类型不合法 transform
  不再由 handle 展开器生成；
- 至少一条 proof passed、至少一条 VERIFIED CriterionEvidence、至少一题真实 Completed、Strict `>0`；
- 至少一题 proof 初次失败后通过 task-local RWKV 修订恢复，且已成功 action 没有被重跑；
- FP=`0`、Offline 全过、Control `30/30`、因果链 `90/90`、raw final byte equality 全过；
- Round12 总请求数和 prompt tokens 均不得高于 Round11 的 `2175` 和 `5,460,587`。

## 预注册 GitHub 晋级门

结构诊断成立不等于允许上传。Round12 只有同时满足以下条件才提交并推送：

- FP=`0`；
- External `>=18`，不回退 Round11 的真实外部结果；
- Strict `>7` 且 Completed `>7`，击败当前可回档最佳 Round2 的 Strict `7/90`；
- 完整产品测试、Control `30/30`、90/90 因果记录、raw final equality 和数据 hash 全部通过；
- 请求数与 prompt tokens 不高于 Round11。

否则保留全部 Round12 本地数据和分析，结论为 `do_not_upload`，远端仍停在 Round2 checkpoint
`b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
