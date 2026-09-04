# Round153：Split Reasoning + Literal Review B04 预注册

日期：2026-08-23

相对 Round152 只允许：

- contract Planner reasoning_effort=low；contract Reviewer=medium；
- Planner predicate 必须保留其义务涉及的 exact request literals；
- Reviewer 明确按请求中写出的 destination path 解释 “relative copied path”，不得相对 manifest 目录
  重新计算。

不修改 controller acceptance、任务、verifier、RWKV、tools、graph budgets 或 Final。

固定 E2E-B04，case concurrency=1，atom concurrency=4。通过门：manifest exact
`archive/2026/source.txt\n`，source/destination digest 相等，strict PASS；常规逻辑 GPT calls=2；Reviewer
无公开证据矛盾 acceptance；Final byte-exact raw RWKV；GPT tools=0。

通过后才恢复 13 题 canary。
