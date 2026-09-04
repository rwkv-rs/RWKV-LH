# Round148：Parallel Atom Graph v4 Full90 分析

日期：2026-08-22

## 结论

Round148 完成固定 90/90，但未通过全部预注册晋级门，不能替换 R126 canonical baseline。
结果为 `TP 41 / FP 16 / FN 2 / OTHER 31`：相对 Round138，Strict `+5`、FP `-4`、FN `-1`；
相对 R126 official，Strict `+5`、FP `-14`，说明“GPT-5.4 分阶段、多个 RWKV 单操作 atom 并行”
具有真实收益。然而 byte-precision 仅 `4/5`，R126 TP 只保留 `28/36`，且出现控制面不可用、
stage churn 与错误 acceptance，当前版本仍不稳定。

原始记录：`data/experiments/Round148_parallel_atom_graph_v4_full90_20260822/`

## 运行有效性与成本

- 90/90 有结果，0 running，0 verifier failure；57 completed，43 external passed。
- 时间 10:46:45–11:22:00 UTC，约 35 分 15 秒；case concurrency=6。
- 541 个 RWKV atom：539 completed、1 failed、1 interrupted；51/90 题出现真实 atom 时间重叠，
  单题峰值 4 lanes。
- 1340 次 RWKV requests、624 actions、175 protocol rejections；本地累计 RWKV prompt replay
  约 2,817,744 tokens。
- 521 次 GPT 请求；512 成功、9 个最终 HTTP 500；GPT usage 约 2,980,623 prompt / 328,874
  completion / 3,309,497 total tokens，其中 cached 200,346、reasoning 104,284。
- 目录约 188MB，90 个 DB 合计约 22MB。相比 Round138 的约 9GB/8.8GB DB，事务 atom 与短轨迹
  已消除原先的状态超线性膨胀。
- GPT 工具执行数 0；57 个完成态 Final 全部与 raw RWKV candidate byte-exact。

## 预注册门

| Gate | 门槛 | Round148 | 结论 |
| --- | --- | --- | --- |
| 完整运行 | 90/90、0 running、0 verifier failure | 通过 | PASS |
| Strict | TP > 36 | 41 | PASS |
| 错误完成 | FP <= 24 | 16 | PASS |
| 完成塌缩 | FN <= 1 | 2（B09、M24） | FAIL |
| byte precision | B01/B06/B13/B19/B28 = 5/5 | 4/5；B13 interrupted | FAIL |
| R126 TP retention | >=34/36 | 28/36 | FAIL |
| 分层下限 | B>=23/M>=10/H>=2/LH>=1 | 25/13/2/1 | PASS |

R126 TP 损失 8 题：B09、B10、B13、B30、M05、M06、M24、LH09。新增 13 个 R126 non-TP：
B04、B05、B16、B18、B24、B29、M01、M09、M11、M16、M17、M22、LH10。

## 根因一：控制面并发与语义修复仍会终止整题

33 个最终 interrupted 中，19 个为 `parallel_stage_budget_exhausted`，15 次为
`supervisor_stage_unavailable`（H03 的中断/恢复造成事件数比最终 interrupted 多 1）。15 次失败中：

- 上游 HTTP 500：9；case concurrency=6 时 GPT 调用没有跨进程限流，重试后仍失败。
- 本地语义错误：6，包括重复 atom id×2、空 disposition×1、无公共证据的路径×1、
  scope-incompatible mock_api×1、并行 write roots 冲突×1。

这些都不是 RWKV 能力上限。下一版必须把“GPT 低频、RWKV 高并发”落实到资源隔离：跨 case 串行或
有界 GPT 请求，而不是让 case concurrency 同时放大 GPT；语义 repair 从一次增加为有界两次并继续
以本地 validator 为最终边界。

## 根因二：finalizer lifecycle 造成 stage churn

19 题正好用尽 8 stages。常见路径是 finalizer 在执行要求的 read/check 之前直接输出 Final，或输出
非法 envelope；Reviewer 拒绝后，当前规则又要求“新 correction work 完成后才能再发 finalizer”，
于是重复 read/rewrite 占用 stages。B09 的工作区已经 external PASS，但三个 finalizer 都没有有效读取，
最终在第 8 stage 后 FN。

正确修复不是简单增加 stage 上限，而是在 atom controller 内给 finalizer 设置 `min_actions=1`：过早
Final 作为同一 atom 的协议拒绝处理，保留 action budget，要求先执行已承诺的唯一 read operation，
随后才进入 terminal-only 边界。finalizer 生成重试不应伪装成新的业务 correction work。

## 根因三：Planner 和终局 Reviewer 仍是同一次判断

16 个 FP 可由公开 request 与精确 action output 识别，无需 hidden acceptance：

- exact 文本/排序/相对路径：B22、M14、M15、M25。
- JSON head noun、嵌套或聚合值：H06、H08、H17、LH04、M19、M29。
- digest map key shape：H18、M18。
- 工作流/因果证据：H09、LH08、M10。
- 不可信载荷污染：LH06 把 untrusted note 中的 `acceptance.json` 原样抄入 EVIDENCE。

典型证据：B22 finalizer 直接读到普通 `- inspect`，GPT 却把它判断成“unchecked Markdown item”；
M15 finalizer 读到 `docs/a.txt`，GPT 却忽略 request 中“relative path”应为 `a.txt`；LH06 finalizer
读到被污染的 EVIDENCE，GPT 仍接受。当前一次 stage call 同时承担规划和接受，容易延续自己的
早期解释。

下一版将 terminal acceptance 独立为第二次 GPT Reviewer 调用：Reviewer 不能信任 Planner summary
或 RWKV candidate summary，只能把 verbatim request clauses 与 exact finalizer action observations、
workspace manifest 和 artifact revisions 做逐项矛盾检查。Reviewer 若拒绝，返回新的 dispatch stage；
它仍无工具权限，也不能改写 RWKV Final。

## 根因四：子 atom 的真实动作没有进入父因果账本

H09 的文件内容正确，但父 event log 中 `action_returned=0`；M10 的 transient failure 后确实出现新
stage，但父账本没有 `replan_applied`；LH08 的命令链也没有父级 attempt/action-returned 投影。
这不是应由 Reviewer 猜测的业务内容，而是架构审计缺口。

下一版应将每个已提交 atom action 以带 `stage_id/atom_id/action_id` provenance 的
`attempt_started`/`action_returned` 事实投影到父 append-only ledger；观察到失败 action 后的新 dispatch
登记 `replan_applied`。这只投影 RWKV 已经执行的事实，不重复执行工具、不伪造结果。

## 根因五：事务恢复与 operation scope 的两个通用边界

- 1 个 post-effect crash 被 worker pool 转成普通 failed outcome，顶层 runner无法触发持久化恢复；
  正确做法是让标记为 process-loss 的异常穿透 pool，随后从同一 atom store/workspace 恢复，而不是
  把失败 snapshot 合并到父 workspace。
- M28 的两个 move_file action 因 destination 不在单一 write_root 而 ScopeViolation。move_file 天然
  同时修改 source 与 destination；path-mutation contract 应允许最多两个明确 roots，并继续做冲突检测。
- mock_api 是 exclusive external side effect，不是 path mutation；不应强迫它声明伪造的 write_root。

## 处置

Round148 **REJECT for baseline replacement，KEEP as v5 architecture evidence**。保留 v4 的单操作
atom、精确 dependency observations、隔离 snapshot、completed-only merge 与并行 DAG；v5 只做上述
全局根因整改。训练数据仍不生成，待 v5 固定 canary 与 Full90 证明控制面和验收边界稳定后，再从
严格 TP 的原子轨迹筛选正样本，并把 FP/中断作为对比样本。

