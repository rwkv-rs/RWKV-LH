# Round160 Terra/Sol FP Trap Canary 分析

日期：2026-08-23

## 结果

固定 M04/M08，两模型均未达到 strict=2/2：

| model | TP | FP | FN | OTHER | logical | physical | tokens | actions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.4（Round158 同例） | 0 | 2 | 0 | 0 | 4 | 7 | 33,701 | 14 |
| gpt-5.6-terra | 0 | 0 | 0 | 2 | 7 | 10 | 37,873 | 7 |
| gpt-5.6-sol | 0 | 2 | 0 | 0 | 8 | 10 | 67,661 | 20 |

- terra M04 的真实复杂 Planner 请求连续 3 次 500，证明 Round159 小 schema 的 5/5 不能
  外推到生产 contract schema；M08 生成了错误模板并在 3 轮后安全中断。
- sol 两例均完成，但都是 FP。M04 已包含 name/version，只缺最后 newline；M08 仍把 worker
  排在 web 前。Reviewer 均错误 satisfied。
- sol 在真实 contract 请求上的传输比 terra 更稳，但不能作为唯一 Reviewer；terra 更保守，
  但既有复杂请求 500 又没有 strict success。

结论：当前没有候选可直接替换完整 Planner+Reviewer。下一轮若做 phase-specific route，sol 只能
作为 Planner 候选，并必须先由 typed local predicate 兜住 exact bytes/order/schema；Reviewer 角色
仍需真实 canary，不得按模型名推断。原始目录为
`Round160_terra_fp_trap_M04_M08_20260823/` 与
`Round160_sol_fp_trap_M04_M08_20260823/`。

