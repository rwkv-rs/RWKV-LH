# Selector Frontier 权限整改预注册

日期：2026-09-04（Asia/Shanghai）

## 冻结基线

- 源码起点：`e69543cd` 加已预注册的 Stateful Goal 停滞预算修复；Selector Head v2 SHA-256 固定为 `49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a`，zero State，不做 StateTune。
- 固定 canary：`AGENT-LADDER-L1-FIX01`，Strong `goal_stages`、progressive disclosure、最大 240 transitions、2.9B Selector 与 13.3B Executor 原生推理链。
- 停滞修复后基线：8 个 action、0 次协议拒绝、0 个完成 step，以 `identical_failure_budget_exhausted` 阻断；操作为 `date_diff ×1`、`run_command ×2`、`check_command ×5`。
- Planner 的 `S1@1` 只有 `read_roots=[pricing.py, verify_project.py]`，没有 `write_roots`。其 runtime eligible labels 却包含有副作用的 `run_command`，并漏掉固定分类标签 `ABSTAIN`。
- 第 1、3、4、5、6、7、8 次 Selector 的 25 类 raw-logit 全局最大值是 `ABSTAIN`；服务因 eligibility mask 被迫选择其他标签。第 1 次被选标签置信度仅 `0.0071633687`。

## 根因和固定整改

- `_goal_step_operations` 声称为无写根步骤移除工作区 mutation，但实现只匹配一个具体 `side_effect_class` 字符串，漏掉 `run_command` 的 `local_process_mutation`。修复为依据 ActionDefinition 的统一 `side_effect` 权威字段过滤；不新增工具分类或规则选工具。
- independent Selector 的常规路径会提供 `ABSTAIN`，但 Strong Planner frontier override 原样覆盖了它。非终局 action frontier 必须在调用 Selector 时保留 `ABSTAIN`；`final_answer` 仍保持协议规定的 singleton menu。
- `ABSTAIN` 是 Selector 的合法“不执行工具”决策，不是 Executor 参数格式错误。Stateful Goal 收到它后不得调用 Executor、不得累计 `protocol_rejection_recorded`，而应以既有可恢复阻断语义记录 `run_blocked(reason=selector_abstained)`，由显式恢复或后续 Planner 变更处理。
- 不改变 Head logits、不按规则替 Selector 选择 `read_file`、不修改状态作用域、不增加模型调用、不修改评价数据或阈值。

## 固定验证

- 无 `write_roots` 的 Planner step 中 `run_command` 和所有其他 side-effect operation 均不可选；`check_command` 和文件读取操作仍可选。
- action frontier 的请求中包含 `ABSTAIN`；终局请求仍只有 `final_answer`。
- Selector 选择 `ABSTAIN` 时恰好一次选择、零 Executor 请求、零 action、零 protocol rejection，并以 `selector_abstained` 阻断。
- 运行 Stateful Goal、Selector、runtime 与完整测试集；随后使用同一 canary 复跑。能力仍按 verifier 判定，不因工程阻断而宣称通过。
