# Round135 在线微任务 canary 因果分析

日期：2026-08-22

## 结果与处置

- 首轮目录 `Round135_online_gpt54_microtask_canary_B01_M11_H17_20260822` 因实际使用
  progressive tool disclosure，与预注册 full 不一致，判为无效。
- 有效 r2 目录 `Round135_online_gpt54_microtask_canary_B01_M11_H17_r2_20260822` 明确记录
  full disclosure、online microtask architecture、concurrency 3。
- r2：B01 Strict TP；M11 interrupted / External fail；H17 completed / External fail。
- 11 次 Supervisor requests，RWKV 37 requests / 29 actions，GPT action count 0；全部 delivered
  Final 与 RWKV 原始 `final_answer.text` 字节一致。
- 预注册 gate 失败：M11 不是 Strict TP，三题 protocol rejection 合计 7 > 6。因此停止 Full90。

## M11：纠正 directive 被旧预算截断

M11 的四个 service JSON 均迁移正确；summary.json 在 A00013 一度也是正确 name-to-port mapping。
RWKV 随后重复一个路径设置错误的 `check_command`，并在后续波次把 summary 回写为错误结构。
GPT 第 5 个 directive 已准确要求把 summary 恢复为 name-to-port mapping，但 controller 在提交该
directive 后立即触发旧的全局 `identical_failure_budget_exhausted`，导致纠正永远不可执行。

这是架构边界错误：在线 Reviewer 已产生新状态转移时，旧单模型的全局 5-failure terminal guard
不能优先终止。根修复是在线模式由 action-wave stagnation review、max transitions 和
max directives 共同限界，不再使用旧 guard；静态/纯 RWKV 路径保持不变。专项回归覆盖“5 次相同
失败后纠正仍可执行”。

## H17：循环被打破，但公开规格存在歧义

H17 从 Round134 的 200 次相同 read / 0 workspace change 改为 5 actions：读取 events、写入
ledger、两次读取验证并正常 Final；产生 workspace digest change，且没有连续 5 次零信息重复，
满足 Round135 对 H17 预注册的状态转移行为检查。

但 GPT 和 RWKV 都把请求中的 `one entry per unique event id in first-seen order, count, and
total_amount` 解释为“每个 id 聚合 count/total_amount”。隐藏 verifier 期待的是顶层对象
`{entries: 首次出现原记录, count: 唯一数, total_amount: 全局总和}`。Round134 的独立静态
GPT plan 也作了相同聚合解释，说明单纯再加静态 plan 不能解决。

此外，runner 的 `resume_no_repeated_completed_attempts` 当前把中断前后的全部 terminal action-id
列表要求完全相等，因此任何 resume 后的合法新进展都会使它为 false；H17 r2 同时暴露该独立
评价观察器缺陷。为保持本轮 frozen verifier 与历史 baseline 可比，本轮不修改 hidden acceptance
或把 target 暴露给模型。该数据规格/观察器应另行 version 化整改，不能作为在线 prompt 特判。

## Round136 唯一行为变更

仅移除 online_microtask 路径的旧 global identical-failure terminal；保留：

- 相同零进展 fingerprint 连续两次提前 review；
- 每 6 actions 正常 review；
- max transitions 200；
- max directives 64；
- full disclosure、同三题、同并发、同 frozen verifier 和同 gate。

