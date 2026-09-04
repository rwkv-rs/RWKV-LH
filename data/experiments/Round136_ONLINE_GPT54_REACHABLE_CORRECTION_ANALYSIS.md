# Round136 可达纠正 canary 分析

日期：2026-08-22

- B01：Strict TP。
- M11：Agent interrupted / External PASS；四个 service 与 summary 共 5/5 hidden checks 通过。
- H17：Agent completed / External fail；产生 workspace mutation，无历史长读循环。
- 合计 Strict 1/3、External 2/3、protocol rejections 13（M11=12、H17=1），未通过 gate，
  不进入 Full90。

Round136 证明上轮根修复有效：M11 不再在第 5 个相同 Harness failure 后立即中断，后续 RWKV
动作把全部 artifact 修正确。但正确 artifact 后，RWKV 连续 12 次生成带未知 `max_tokens/path`
参数的 `check_command`，耗尽 protocol rejection budget。期间没有新 action，所以按 Round136
协议没有形成 action wave，GPT 也没有再次介入（全题仅 initial + 第一 action wave 两次调用）。

根因是在线 Reviewer 的 outcome 定义不完整：协议拒绝虽然没有 Harness side effect，却是 RWKV
状态转移的真实可见结果。Round137 将每 2 个新 protocol rejections 合为一个低频 review wave，
保留严格 schema 与 12 次 hard cap；GPT 只给纠正微任务，不执行或补全调用。该机制对所有工具
协议错误通用，不包含 M11、check_command、路径或参数特判。

