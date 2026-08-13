# Round4 预注册：独立来源 Criterion Proof 边界

预注册日期：2026-08-12（任何 Round4 RWKV-E2E-90 请求之前）

## 1. 因果依据

Round2 有 12 个 FP、63 条 VERIFIED criterion evidence，其中 34 条由 read/list 等只读动作持有；
外部失败以 `json_equals` 12 次、`file_content` 2 次、`aggregate_shards` 2 次为主。当前 Controller
在 immediate postcondition 与 RWKV semantic cross-check 通过后，就把 Task 的
`satisfies_criteria` 直接提交为 Goal evidence；write 的 expected 常直接来自同一次 write 参数，read
又可能只证明文件存在，形成 self-confirmation。

Round3 仍有 9 个 FP；failed-observation gate 实际 suppression=0，未触及完成证据根因。用户提供的
分阶段计划因此支持把完成证据边界设为下一单变量，但计划中的 plan coverage、Goal obligation
recovery、criterion 容量、StateCapsule 与 G1i 改动本轮全部延后。

## 2. 唯一结构变量

实现 `independent_criterion_proof_boundary.v1`：Task postcondition 与 Goal criterion proof 分离。

### 2.1 RWKV 的职责

现有 `validation_cross_check` 仍由同一 RWKV作语义决定。若 decision=pass 且 Task 声明
`satisfies_criteria`，RWKV 必须在同一个结构化响应中为每个 claimed criterion 提出恰好一个
`CriterionClaim`：criterion、显式 subject/producer、actual proof expression、expected proof
expression、comparison 和理由。RWKV 选择所有 ref、selector、literal、operator 与 subject；程序
不得从 criterion 文本自动生成、补全或挑选 claim。

### 2.2 受限 proof 表达式

只接受递归深度、节点数、输入字节数有固定上限的纯数据表达式：

- `ref`：`workspace`、当前 `action_result`、直接 dependency 的 immutable artifact/memory；
- `literal`：RWKV给出 value，同时必须引用 `Goal.original_request` 中逐字存在的 quote；
- `count`、`sum`、`group_sum`、`object`、`object_set`、`sort`、`sha256`。

禁止 `eval`、Python、shell、正则推理、网络、glob 猜测、任意函数名和隐藏路径。workspace selector
只允许完整 text/JSON、RFC 6901 JSON pointer、directory entry set 或 file SHA-256，并保留实际 bytes
hash。dependency ref 必须属于直接 dependency，且当前 artifact hash 与登记 hash 一致。

actual 可引用当前 action/workspace；expected 禁止引用当前 attempt、当前 producer 产物或其 action
参数。expected 只能来自 Goal quote/literal、直接 dependency immutable ref 及其受限变换。两侧求值
后仅做 exact typed equality；没有模糊匹配、候选选择或答案规则。

### 2.3 双重门禁与状态

- immediate deterministic verifier 任一 required failure 时，不调用/不接受 criterion proof pass；
- RWKV decision=replan 时真实失败；decision=pass 但 claim 缺失、重复、越权、不可求值或 unequal 时
  也真实失败；程序不能把 proof 失败改成 pass；
- 只有 RWKV semantic pass **且** 每个 claim deterministic proof exact pass，才创建 VERIFIED
  `CriterionEvidence`；
- `CriterionClaim`、`EvidenceRef`、表达式、求值结果、artifact hash、observation digest、RWKV理由与
  validation refs 全部持久化；失败 claim 也保留；
- Task postcondition 可以完成 Task，但没有合格 claim 不能覆盖 Goal criterion；
- run 完成前使用当前 workspace 重新求值每条 active VERIFIED claim，hash/digest/结果变化则证据
  invalidated，run 不完成。本轮不自动生成修复任务。

## 3. 明确不改

- 不删除当前 legacy task binding 回退；不放宽初始 plan 的 required criterion coverage；
- Goal proposal 仍为 1–5 criteria；不加 Goal obligation recovery；
- 不改 task/action prompts、工具目录、G1i 外壳、参数修复、采样、并发或 transition 上限；
- 不添加 Repo Map、StateCapsule、subagent、多模型/provider 或 recurrent state；
- 不读取隐藏 acceptance、Codex 标准答案或题号来构造 proof；不修改 RWKV 最终输出。

## 4. 必测反例

1. read 成功 + file_exists + RWKV pass 但没有独立 exact proof，不能 VERIFIED；
2. write_json 用自己写入的 value 当 expected，必须以 expected-self-reference 拒绝；
3. expected dependency artifact hash 变化后 proof 失败；
4. 少一个 JSON 字段、少一个 shard、directory set 不完整时 exact proof 失败；
5. RWKV pass 不能覆盖 deterministic unequal；RWKV replan 不能被 proof pass 覆盖；
6. literal 没有逐字 Goal quote、dependency 越权、workspace expected 指向 current producer 均拒绝；
7. 后续 task 改写 artifact 后，final re-evaluation 使旧 evidence invalidated；
8. schema v2 未完成 run 的旧 evidence 迁移为 LEGACY_UNVERIFIED；已完成历史 run 只读可加载；
9. final answer 继续与 raw RWKV response 字节一致。

## 5. 固定运行和判定

- 模型、E2E-90、Basic/Medium/Hard 各 30、并发 8、200 transitions、temperature policy、标准答案、
  hidden acceptance 和 `utf8-byte-ngram-cosine.v1` 全部与 Round3 一致；
- 运行前后都执行完整离线回归和 LH-Control-30；90/90 必须有终态与完整因果链；
- 从 Round3 继承 FP 不增加门槛：Round4 FP 必须 ≤9；方向目标 FP=0，但不能靠全部阻塞冒充成功，
  同时报告 External、Strict、FN、completion precision 和 proof rejection stages；
- 新 GitHub 最佳回档仍要求 External > 当前最佳 8、FP≤9、非干预全部通过、Control-30 与离线全过；
  未达到则保留完整 Round4 数据但不上传为最佳点。

## 6. 反作弊判定

允许：RWKV选择 proof，确定性层像工具一样执行 exact computation。

禁止：程序根据自然语言 `all/every`、题号、隐藏检查或标准答案自动选择 proof/operator/expected；
根据多个 claim/candidate 的结果选一个能过的；修改 RWKV claim 或最终答案；把缺失 proof 规则补齐；
使用 action 自己的错误输出作为 expected。任一发生即整轮无效。
