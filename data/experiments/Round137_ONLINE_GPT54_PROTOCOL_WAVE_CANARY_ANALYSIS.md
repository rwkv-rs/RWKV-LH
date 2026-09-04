# Round137 protocol-wave canary 分析

日期：2026-08-22

## 固定 gate 结果

| Case | Strict | External | Completed | RWKV requests | GPT requests | Actions | Rejects |
|---|---:|---:|---:|---:|---:|---:|---:|
| E2E-B01 | PASS | PASS | PASS | 4 | 2 | 3 | 0 |
| E2E-M11 | PASS | PASS | PASS | 25 | 6 | 21 | 2 |
| E2E-H17 | FAIL | FAIL | PASS | 6 | 2 | 4 | 1 |

- 3/3 有效、3/3 completed、0 running；无 Supervisor transport/protocol failure。
- B01、M11 均 Strict TP。
- H17 在 A00004 改变 workspace digest；没有连续 5 次相同零信息 action，且没有长读循环。
- protocol rejection 合计 3 <= 6；无 12 rejection、64 directive 或 200 transition budget 耗尽。
- 10 次 GPT requests，GPT action count 0；全部 delivered Final 与 RWKV 原始文本 byte-exact。

因此 Round137 canary gate **PASS**，允许按预注册门槛进入 Full90。H17 仍保留为 Reviewer false
accept / 数据规格歧义证据，不把 hidden target 注入模型；Full90 的 FP/FN 与分层门槛会约束该风险。

## 协议波次的直接作用

M11 在第一次 action wave 后完成四个 service 迁移；后续 2 个 protocol rejections 被分摊进公开
outcome。GPT directives 把工作依次收敛到 summary 创建、三个 service 最终 read-back、summary
最终 read-back，最终五个 artifact checks 全通过并接受 RWKV Final。相较 Round136 的 12 rejects /
interrupted，新的 outcome boundary 把无法执行的调用错误转成了可到达纠正，没有放宽 schema。

