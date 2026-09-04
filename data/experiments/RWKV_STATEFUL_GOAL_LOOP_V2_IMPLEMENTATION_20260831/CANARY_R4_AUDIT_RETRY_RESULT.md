# Stateful Goal Loop v2 Audit 原地纠错 canary R4 结果

运行时间：2026-09-01（Asia/Shanghai）

## 固定能力结果

- case：`AGENT-LADDER-L4-LEDGER01`。
- completed/external/strict：`0/1`、`0/1`、`0/1`；状态 `running`。
- 13.3B requests：17；Actions：1（`file_digest`）；protocol rejects：12。
- 最终 yield：`protocol_rejection_budget_exhausted`。

该结果不通过能力门，不运行完整 Ladder，也不通过任何结果筛选或口径修改改写为成功。

## Audit 隔离结论

同一个 `observation_complete` 边界真实执行了 3 次同 profile 13.3B Audit fork：

1. attempt 1 生成直接对象，但额外包含 kernel-owned `audit_id/schema_version`，被六字段协议拒绝；
2. 主 State 追加第 1 条 `goal_audit_retry_feedback` 后，attempt 2 已去掉多余字段，但生成了 `{"audit_decision": {...}}`；运行时公开协议要求标准 `{"function":"audit_decision","params":{...}}` 调用封装，因此仍被拒绝；
3. 主 State 追加第 2 条 retry feedback 后，attempt 3 只生成不完整代码围栏 `````，解析失败。

计数：`goal_audit_recorded=3`、`goal_audit_rejected=3`、`goal_audit_accepted=0`、`goal_audit_retry_feedback=2`。三个 candidate 均 `authorizes_execution=false`、`wkv_merged=false`。因此“拒绝后停留在同一审核边界”和“审核 WKV 不合并”实现成立，但预注册的 `goal_audit_accepted >= 1` 结构门失败。

根因层是 13.3B Audit function-envelope/结构输出能力，不是 Strong Planner 的 `ContractGraphPatch` 或所谓 `PlanPatch` 格式失败。不能通过接受任意 wrapper、删除 evidence kernel 或放宽 `ready_for_final` 语义来掩盖。

## Frozen Planner gate

该门也失败。R4 没有命中预期的 R3 cache，而是发起 1 次真实 `contract_plan` HTTP 请求：

- provider/model：OpenAI-compatible `gpt-5.4-mini`；
- phase：只有 `contract_plan`；Strong Reviewer 请求为 0；
- cache key：`2cd4787386b619bfa7b473ad1d92b8bf9a64be16ce5649beecba72380c794e20`；
- response SHA-256：`46540eadf71aacaa76def58cec024e68976b3f1cb1ff99c821c0b237dbac7c00`。

新增响应已原样保存在 R4 输出目录的 `strong_planner_cache_miss_response.json`。随后只移除了本轮新增的 cache 文件，使 R3 cache 恢复预注册的原始三文件及原哈希；R4 仍按 frozen-planner gate 失败记录，不重跑、不挑选结果。

## 报告层整改

R4 的 `RUN_PROTOCOL.json` 暴露了两项旧架构元数据：`strong_model_dependency=false` 和 `independent_terminal_review=true`。这与实际 Stateful 运行路径冲突：Strong Planner 是必需依赖，而 Strong Reviewer 不在主循环。

运行后仅修复 observability：Stateful 报告现在登记 `strong_planner_required=true`、`strong_model_dependency=true`、`strong_reviewer_enabled=false`、`rwkv_audit_required=true`；`REPORT.md` 明确 Strong 只做 Planner。该修改不改变 R4 原始结果，原始输出保持不覆盖。

## State-tuning 落地

按预注册停止继续 live canary。R4 attempt 2 的真实错误形态保留在 causal ledger；训练数据不复制 Ladder 任务内容，而是在不相交的 `sandbox-log-inspection-audit-v1` project family 中复现同一错误封装，并给出标准 `function + params` 修正。

- 新样本：`V2-CORR-AUDIT-0002`；
- deterministic verifier：失败 wrapper 被拒绝，修正 wrapper 被接受，非 final `continue` 与 evidence ref 保持正确；
- correction corpus：3 accepted、0 rejected，train/dev=`2/1`，family overlap=`0`；
- 固定相似度：`utf8-byte-5gram-cosine.v1` 最大 `0.07102705857155676 < 0.95`；
- Strong Model label authority：false；
- 配额：`3/2480`，未达到 `2000/480`，不能启动正式 tuning。

## 结论

当前默认架构责任已经对齐：Strong Model 是 Planner，13.3B 是单主 State Executor 与自审核者。Top-K 接线修复曾提高 action throughput，但 R4 证明 13.3B 仍不能稳定生成 Audit 调用封装；当前版本不能标记为模型能力完成或正式可用。下一步应扩展不相交 project-family 的 Audit/operation/repair/final correction 数据并完成固定配额，再按预注册重新训练与全量评价，而不是继续调整 Planner patch。

运行后 observability、数据集整改与协议元数据锁定的最终全量回归：`756 passed, 1 warning in 154.49s`。唯一 warning 仍是既有 Python 3.13 多线程 `fork()` deprecation。
