# Round147：Exact Dependency Observation Canary 预注册

## 固定配置

与 Round146 相同：B04/M16/LH06、GPT-5.4、当前 RWKV、single-operation atom v4、max stages8、并发4、mutation budget1、read budget1–4。

## 唯一变更

1. dependency handoff加入 bounded exact action observations；
2. dependency handoff移除 RWKV natural-language candidate summary；
3. 下游只以 action observations/artifacts 为依赖事实。

## 成功门

external `3/3`；至少 `2/3` 真并行；mutation atom严格1 action；无 failed/interrupted atom、ScopeViolation、InputBudgetError、stage failure；每题≤8 stages；exact finalizer output；失败 snapshot 不提交。

