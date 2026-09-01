# G1J 13.3B zero-State 单职责输出 canary 预注册

- 登记日期：2026-09-01；登记早于本 canary 的任何推理请求。
- 目的：在不加载任何已有 State profile 的条件下，区分 G1J 13.3B 的单职责输出质量与 native-state 服务插件缺失。
- 权重：`/mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth`，SHA-256 `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`。
- 服务：`rwkv-8222:18183`，模型身份必须为 `rwkv7-g1j-13.3b-20260831-ctx16384`。

## 固定输入

- 数据：`data/datasets/rwkv_stateful_goal_loop_v2_corrections_v1/verified_corrections.jsonl`。
- 数据版本：`rwkv-lh.stateful-goal-loop-v2-corrections.v2`。
- 输入顺序：`V2-CORR-OPARGS-0001`、`V2-CORR-AUDIT-0001`、`V2-CORR-AUDIT-0002`。
- 每例使用已冻结的 `input_context`，不添加失败输出、正确答案或额外提示。
- 请求：completions、`temperature=0.1`、`top_p=1.0`、`max_tokens=256`、并发 1。
- State：不发送 State profile、State ID、checkpoint 或续写 State。

## 固定判定

- operation case 使用 `parse_ranked_tool_choice`，候选固定为 `write_file/current_time/date_diff`，要求选择 `write_file`。
- audit case 使用 `GoalAuditDecision.parse_with_bindings`，要求严格六字段语义通过，并与已验证 correction 的 verdict、step、complete、evidence refs 一致。
- gate：三例全部通过。解析失败属于模型输出格式/协议质量；解析通过但语义不一致属于模型能力问题；模型身份、HTTP 或服务不可用属于基础设施问题。
- 本 canary 只评价旧固定 prompt 上的零 State 单职责输出，不代表最新 v8 Selector，也不代表完整 Stateful Goal Loop 产品链。
