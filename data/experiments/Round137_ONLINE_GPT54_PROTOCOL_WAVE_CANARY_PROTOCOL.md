# Round137 在线 GPT-5.4 协议拒绝波次 canary

日期：2026-08-22

上游：Round135/136 协议与因果分析。

## 唯一新增机制

online_microtask 模式把每 2 个尚未被 Supervisor 审阅的 `ModelProtocolError` 合为一个
`protocol_batch` outcome。GPT-5.4 在下一次 `next_directive` 中读取错误摘要和公开工具契约上下文，
只下发一个纠正微任务。Controller 不推断 operation、不补参数、不放宽 schema，Harness action
count 不增加。action wave、Final review 和恢复时必须用 rejection refs 保证同一错误批次只审一次。

固定边界：action wave=6；重复零进展 action=2；protocol rejection wave=2；全局 protocol hard
cap=12；max directives=64；max transitions=200。

## 固定运行与 gate

- Cases：E2E-B01、E2E-M11、E2E-H17；concurrency 3。
- RWKV：`rwkv7-g1i-13.3b-20260805-ctx16384`；GPT-5.4；full disclosure 显式 pin。
- 输出：`Round137_online_gpt54_protocol_wave_canary_B01_M11_H17_20260822`。
- frozen isolated verifier；无 hidden acceptance/model trace 泄漏；GPT action count 0；Final byte-exact。

Gate 不降低：3/3 有效；B01/M11 Strict TP；H17 有 workspace change 且无连续 5 次相同零信息
action；三题 protocol rejection 合计 <=6；无 directive/transition/protocol budget 耗尽。H17 的
External/Strict 如实报告但不替代 B01/M11。全部满足才允许 Full90，并沿用 TP>36、FP<=24、
FN<=1、byte 5/5 与无分层 collapse 的晋级门槛。
