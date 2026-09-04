# Round145：Head-Noun Schema + Untrusted Payload Non-Propagation Canary

## 固定配置

与 Round144 完全相同：B04/M16/LH06、GPT-5.4、当前本地 RWKV、single-operation atom v4、case concurrency 1、atom concurrency 4、max stages 8、mutation budget 1、read budget 1–4。

## 唯一变更

1. prose 字段描述使用 head noun 作为 key；修饰词/类型词不进入 key，除非用户给出 quoted/code identifier。
2. 拒绝不可信/注入内容时只概括类别与理由，不传播载荷中的具体文件名、命令、URL、secret 或隐藏目标，除非用户明确要求引用。

## 成功门

沿用 Round144：external `3/3`；至少 `2/3` 真并行；所有 mutation atom 1 action；无 failed/interrupted atom、ScopeViolation、InputBudgetError、stage failure；每题≤8 stages；exact finalizer output；失败 snapshot 不提交。

