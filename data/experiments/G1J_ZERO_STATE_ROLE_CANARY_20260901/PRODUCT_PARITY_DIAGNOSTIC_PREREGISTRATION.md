# G1J 13.3B 产品模板一致性诊断预注册

- 登记日期：2026-09-01；登记早于本诊断的任何推理请求。
- 原因：首轮旧 prompt canary 发现其请求遗漏产品 stop suffix，而且 13.3B 二次工具选择已从最新架构删除。该结果不修改、不覆盖；本诊断单独验证最新 Executor/Auditor 单职责模板。
- 模型、服务、zero-State 与采样身份沿用本目录主预注册；请求额外发送产品 `JSON_CALL_STOP_SUFFIXES`。

## 固定三例

1. Executor：Selector 已唯一选择 `write_file`；当前要求为“Create status.txt containing exactly ready.”。要求输出 `write_file`，`path=status.txt`，`content=ready`。
2. Auditor：当前步骤只检查 `settings.toml` 完整读证据 `A00001`。要求严格 `continue/S1/complete/A00001`。
3. Auditor retry：当前步骤只检查 `service.log` 完整读证据 `A00007`，并给出上次 parser rejection。要求严格 `continue/S1/complete/A00007`。

Executor prompt 使用 `render_independent_executor_bootstrap` + `render_independent_executor_tool_disclosure`；Auditor prompt 使用当前 `rwkv-lh.role-pure-goal-audit.v1` 材料顺序、`GOAL_AUDIT_DEFINITION` 与 `render_bootstrap`。`current_requirement/current_question` 必须为尾字段。

## 判定

- parser/严格字段失败：`output_protocol`。
- parser 通过但 operation、path/content 或 Audit 语义不一致：`semantic_quality`。
- HTTP、身份、服务失败：`infrastructure`。
- gate：`3/3`。本诊断不使用 State，也不启动 State Tuning。
