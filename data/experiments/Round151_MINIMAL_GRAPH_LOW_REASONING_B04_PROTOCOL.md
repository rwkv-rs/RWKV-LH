# Round151：Minimal Graph + Low Reasoning B04 Smoke 预注册

日期：2026-08-23

## 固定变更

相对 Round150 只允许：

1. contract node response 改为最小 wire schema；其余字段本地从 immutable contract 确定性补齐。
2. contract plan/review JSON schema 名从 v1 升至 v2。
3. 第三方 OpenAI-compatible Chat Completions 请求显式带 `reasoning_effort=low`。

不修改任务、verifier、RWKV、full tool disclosure、graph budgets、评分或 Final 非干预规则。

## 固定运行与通过门

- E2E-B04；case concurrency=1；atom concurrency=4；transport retry=3；semantic repair=2。
- 初始 Planner 必须返回并提交 graph patch；物理 HTTP attempts 全部审计。
- 不得出现 HTTP 500、unknown operation、scope 或 graph invariant 终止。
- 至少执行 work batch 和独立 Reviewer；Reviewer 输入只有 result capsules，无 RWKV process 字段。
- strict PASS；completed Final byte-exact raw RWKV；GPT tool execution=0。

失败则继续停留在单题，不运行 13 题或 Full90。
