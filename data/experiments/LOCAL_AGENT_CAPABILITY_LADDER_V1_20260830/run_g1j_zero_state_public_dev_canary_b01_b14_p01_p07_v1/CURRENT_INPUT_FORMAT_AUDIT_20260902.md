# 当前完整输入提示格式审计（2026-09-02）

## 结论

当前 G1J 流程全局只保留一套文本生成边界：`PromptV1 + **Tool Call:** + ```json`。旧 Assistant 格式只存在于冻结的对照实验记录中，不进入当前运行链：

| 输入角色 | 唯一运行格式 | 固定样本结果 | 原始输出归一化 |
|---|---|---:|---|
| Selector-Intent | `SelectorIntentMenuV1 + SelectorIntentPromptV1`，无文本生成锚点 | 32/32 label 正确 | 不生成文本，不归一化 logits |
| Executor-Args | `ExecutorArgsPromptV1 + **Tool Call:** + ```json` | 32/32 可解析且函数正确 | `{name,arguments}` → `{function,params}` |
| Step Auditor | `AuditorStepPromptV1 + **Tool Call:** + ```json` | 协议解析 23/32 | `{name,arguments}` → `{function,params}` |
| Finalizer-Answer | `FinalizerAnswerPromptV1 + **Tool Call:** + ```json` | 协议解析 28/28 | `{name,arguments}` → `{function,params}` |
| Final Auditor | `AuditorFinalPromptV1 + **Tool Call:** + ```json` | 外层解析 32/32；协议解析 29/32 | `{name,arguments}` → `{function,params}` |
| Strong Planner | GPT-5.6-sol `/responses` + `text.format=json_object` | readiness 通过 | 本地完整 schema 校验 |
| Strong Stage Checker | Claude Opus 4.6 `/chat/completions` + `response_format=json_object` | readiness 通过 | 本地完整 schema 校验 |

## 互斥格式扫描

Executor 使用相同 train/dev 固定样本分别测试两个互斥候选；组合格式请求数为 0：

- `Assistant: ```json`：运行时解析率和函数正确率均为 7/32（21.875%）。
- `**Tool Call:** + ```json`：运行时解析率和函数正确率均为 32/32（100%）。

其他三个文本角色使用相同固定样本测试：

- Step Auditor：Assistant 协议解析 24/32；纯 Tool Call 为 23/32。为保证当前 G1J 绝对只有一套全局格式，固定纯 Tool Call；这 1 条差异作为 zero-State 基线能力结果保留，不通过参数或特判掩盖。
- Finalizer：两种格式均为 28/28；固定全局纯 Tool Call。
- Final Auditor：纯 Tool Call 外层解析 32/32、协议解析 29/32；原运行时 `Assistant:` 标签再接 Tool Call 为 31/32、29/32，固定为纯 Tool Call。

四个 G1J 文本角色按统一格式合计：纯 Tool Call 正确 112/124，旧 Assistant 正确 84/124。所有请求沿用生产 output token 限制；没有显式传 temperature，没有传 seed，没有训练 StateTune。

## 输入链排查范围

- 普通 controller event：G1J 路径只追加中性 `Function output`，不预开 Assistant JSON。
- 协议拒绝：G1J 路径重新渲染一个完整 Executor-Args 输入，不使用旧 retry Assistant 锚点。
- rollover：独立 Selector/Executor 路径的事件摘要不预开生成锚点；在最后角色提示处才打开唯一锚点。
- Executor history：严格按 checkpoint 的 `event_ids` 因果顺序读取最近 12 条，不再按含 UUID 的 event id 字典序排列。
- 当前 Executor 生成输入校验会拒绝紧邻 `ExecutorArgsPromptV1` 之前残留的旧 `Assistant: ```json`。
- Final Auditor 的 `current_question` 已对齐冻结 train/dev 模板；对齐后 Executor-Args 253/253 与 Final Auditor 80/80 的 train/dev prompt/target 字节均可由当前 renderer 重建。数据目录未修改。
- 产品 `stateful_goal` 启动时只接受 G1J Selector-Intent 协议；历史 Selector prompt 协议不能作为当前运行模式进入旧 Executor disclosure 分支。
- RWKV 只有规范化后的 `final_answer` 才拥有停止权；Auditor/Finalizer 候选本身不直接终止 Goal。

## Strong 模型请求边界

Planner 请求字段只有 `model`、`instructions`、`input`、`max_output_tokens`、`text`；Stage Checker 请求字段只有 `model`、`messages`、`max_tokens`、`response_format`。两者均不存在 temperature、seed 或 reasoning 请求参数。

首次串行 readiness 的 Planner 请求遇到一次中转站上游 HTTP 500；随后将两个 transport 独立重试，GPT `/responses` 与 Claude `/chat/completions` 均返回 `{"ready":true}`。该次 500 属于可重试 upstream 错误，不是输入格式或模型拒绝。

## 数据、版本与摘要

- Executor A/B 原始记录：`protocol_format_probe_v2_executor_anchor_ab/generation_records.jsonl`，SHA-256 `e1e98191a6c1396905c12c1f66b3f9d2102e0ba9abd47beb0784211af066c5fc`。
- Executor A/B 汇总：`protocol_format_probe_v2_executor_anchor_ab/SUMMARY.json`，SHA-256 `b3c50ed686a111d819b4679c2af5131e399e2c8c2b7977dc11b37045ca87c0e8`。
- 其余角色原始记录：`protocol_format_probe_v2_all_g1j_inputs/generation_records.jsonl`，SHA-256 `393f766af183fcf231340e0dd091a46ca9b0b4fa90987f5a473c8a35813ac054`。
- 其余角色汇总：`protocol_format_probe_v2_all_g1j_inputs/SUMMARY.json`，SHA-256 `635074d4aed95de9de048e055a651309ae4ada18951abe07cf0065c1712d0ea3`。
- Selector 固定记录：`protocol_format_probe_v1/selector_records.jsonl`，SHA-256 `9ed3d8f0d5a585311aa9ab039ce1925fdf163f3bdaf684f80aa6b0fa12a3a7ef`。

用途：在全 zero State 真实 Agent 基线前固定每个输入角色的唯一提示格式；这些记录不是训练数据，也不改变 train/dev 文件。
