# Round3 预注册：失败等价 observation 抑制

预注册时间：2026-08-12（任何 Round3 RWKV-E2E-90 模型请求之前）

## 1. 数据依据

Round2 固定 90 题共有 69 次 `criterion_cross_check`。排除 cross-check 自身输出、时间戳和
attempt id 后，`unchanged_observation_analysis.json` 找到 5 次重复观察，涉及 4 题、4 个任务：

- `E2E-H06/T11`：A2、A3 重复 A1 的失败观察；A2 是协议错误，不能成为缓存来源。
- `E2E-LH04/T3`：A3 重复 A2 的有效 `replan` 观察。
- `E2E-LH07/T7`：A2 重复 A1 的有效 `replan` 观察。
- `E2E-M29/T3`：A3 重复 A2 的有效 `replan` 观察；A1 是协议错误，不能成为缓存来源。

这些重复调用没有产生新的 workspace 或 deterministic verifier 证据。Prime Agent 固定提交
`a3b3e753490d0a6ed180e905200c1a6690d78608` 的 autonomous gate 使用工作树 snapshot 避免在
工作区未变化时重复运行失败 gate。Round3 只借鉴这个状态/协议原则，不复制其 Git 假设或通用
Agent 产品形态。

## 2. 唯一结构变量

增加 `failed_equivalent_observation_suppression.v1`：

1. 每次 RWKV cross-check 前生成可审计 observation capsule，固定包含 Goal digest、约束与绑定
   criterion、任务的语义字段、动作及完整 action result、此前确定性 verifier 结果、依赖产物摘要，
   以及工作区所有可纳入文件的路径、类型、字节数与 SHA-256。
2. capsule 使用 canonical JSON + SHA-256 生成 observation digest。状态、时间戳、attempt id、
   recovery 自由文本和前一次 cross-check 文本不进入 digest，避免把同一事实伪装成新观察。
3. 只有 action definition 明确声明 `failure_observation_cacheable=true`，且工作区 snapshot 完整、
   无符号链接、无读取竞态、未超过固定边界时，观察才可复用。内建文件读写、目录读取和证据绑定
   可声明；`check_command`、`run_command`、`noop` 与自定义动作默认不可声明为可缓存。
4. 只有第一次 **协议有效且 decision=replan** 的 RWKV 失败结论可写入当前 RecoveryState。
   `pass`、异常、超时、截断、JSON/协议错误一律不缓存。
5. 同一 recovery lineage 再次出现完全相同 digest 时，不再次调用 RWKV cross-check；生成一条
   `passed=false` 的验证记录，逐字引用第一次 RWKV 的失败理由和原 validation ref，然后照常消耗
   recovery budget，并继续由 RWKV failure analysis 决定 retry/reselect/replan。
6. artifact、workspace、任务、动作、criterion、依赖或 deterministic verifier 任一字段变化，
   必须重新调用 RWKV。不同 lineage 不共享失败结论。

## 3. 审计要求

- 首次与重复观察都保存 capsule、canonical digest、cacheability 和不可缓存原因。
- 抑制事件保存原 task/attempt/validation ref、当前 task/attempt、digest 与复用的 RWKV 原始理由。
- `model_request_started/returned` 数量必须证明被抑制路径确实没有伪造一次模型调用。
- 状态时间线继续一事件一完整 checkpoint，输入、raw output、parsed/normalized payload 与 state delta
  不得丢失。

## 4. 不作弊边界

- 该 gate 不能产生通过结论、criterion、任务、参数、动作值、文件内容或最终答案。
- 不能按题号、题面、隐藏 acceptance、Codex 标准答案或预期产物决定是否复用。
- 不能修改、筛选或替换 RWKV 最终回答，也不能把多个 RWKV 候选投票选优。
- 规则只复用同一 RWKV 已对同一可观察事实作出的失败决定；后续纠正策略仍由 RWKV 决定。
- Round3 不同时修改 prompt、采样、题集、并发、transition 上限、验收或相似度算法。

## 5. 固定运行与门禁

- 数据集：冻结的 RWKV-E2E-90，Basic/Medium/Hard 各 30；标准答案运行时不可见。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`；backend profile、temperature policy、并发 8、
  每题 200 transitions 与 Round2 完全一致。
- 预运行：离线全回归、LH-Control-30、重复观察/工作区变化/外部动作/协议错误/历史恢复专项测试。
- 正式运行：90/90 必须有终态和完整因果链；运行后再执行离线全回归与 LH-Control-30。
- 诊断指标：抑制次数、cross-check 请求数、总请求数、input/output token、恢复预算与终止阶段。
- 质量门槛从本轮恢复：FP 不得高于 Round2 的 12；目标同时观察能否回落至 Round1 的 6。
- 新 GitHub 最佳回档仍要求 External 高于当前最佳 8、FP 不增加、非干预全过、90/90、Control-30
  和离线回归全部完成。若只降低请求而正确率未提高，则保留 Round3 数据但不标记为新最佳。

## 6. 反证条件

出现下列任一项即否定本实现并回滚该变量：不同 observation 被错误合并；协议错误被缓存；外部/
时效性动作被缓存；artifact 变化后未重新验证；复用产生 pass；最终输出不再与 raw RWKV 字节一致；
因果链缺口；离线或 LH-Control 回归；FP 超过 12。
