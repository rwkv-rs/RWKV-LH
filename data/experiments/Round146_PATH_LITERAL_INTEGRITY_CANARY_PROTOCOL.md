# Round146：Path Literal Integrity Canary 预注册

## 固定配置

与 Round145 相同：B04/M16/LH06、GPT-5.4、当前 RWKV、single-operation atom v4、max stages 8、case concurrency 1、atom concurrency 4。

## 唯一变更

1. atom objective/check/constraint 中的 path-like literal 必须逐字来自 immutable request 或 public workspace/artifact；
2. Planner不得相对输出文件重算用户给定路径；“relative copied path”保留请求中的完整 destination literal。

## 成功门

external `3/3`；至少 `2/3` 真并行；mutation atom严格1 action；无 failed/interrupted atom、ScopeViolation、InputBudgetError、stage failure；每题≤8 stages；exact finalizer output；失败 snapshot 不提交。

