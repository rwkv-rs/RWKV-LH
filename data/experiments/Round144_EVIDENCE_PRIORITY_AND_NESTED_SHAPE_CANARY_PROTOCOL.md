# Round144：证据优先级与 Nested Shape Canary 预注册

## 固定配置

与 Round143 完全相同：B04/M16/LH06、GPT-5.4 Planner、当前本地 RWKV、single-operation atom graph v4、case concurrency 1、atom concurrency 4、max stages 8、mutation budget 1、read budget 1–4、顶层 transition 200。

## Round143→144 唯一变更

仅调整通用 Planner 合同：

1. direct action result/artifact/manifest 高于 RWKV candidate summary；
2. nested object exact keys，独立 provenance mapping 不在 item 内重复；
3. 禁止无具体物证矛盾的风格性重写，fresh finalizer支持所有 material clauses 时及时 accept。

不修改 runtime、RWKV、fixture、评价器、任务参数或隐藏目标。

## 成功门

沿用 Round143：external `3/3`；至少 `2/3` 真并行；所有 mutation atom 1 action；failed/interrupted atom、ScopeViolation、InputBudgetError、stage failure 均为0；每题不超过8 stages；exact RWKV finalizer output；失败 snapshot 不提交。

