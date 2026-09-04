# Network Exact-Tool Selector Hidden+MLP v2.2 — 任务/阶段分离预注册

## 继承

- 冻结时间：2026-08-28（Asia/Shanghai），早于 v2.2 数据生成。
- 完整继承 `PREREGISTRATION.md` 与 `PREREGISTRATION_V2_1.md` 的类别、数据量、split、相似度算法/投影/阈值、模型、特征、训练参数、指标、门槛和 state 消融。
- v2 run_r0 与 v2.1 run_r1 均保持 rejected，不重算、不覆盖、不改报。

## 唯一修订：真实 task/stage 因果边界

- 数据集版本改为 `rwkv-lh.network-exact-tool-selector.v2.2`。
- `task_request` 固定为总体用户目标、约束和任务对象，不再逐字包含当前 `stage_objective`。
- `stage_objective` 只表达当前唯一操作需要解决的原子目标。
- 两者可共享任务实体，但不得将完整 stage 文本复制进 task。
- 这是正式 runtime 的真实边界：task 在 Selector bootstrap 只输入一次，stage 作为每步 causal delta 追加。
- 模板/surface 不得通过自动删除、split 移动或不可解释噪声逃避阈值；每行保持自然、可读、具有单一 operation 真值。

## 固定拒绝条件

- 继续对 canonical `task_request/stage_objective/stage_role/progress` 使用 `utf8-byte-5gram-cosine.v1`、同类阈值 0.95。
- 任一 pair ≥0.95，整批拒绝并记录；不得修改同一次实验的评价投影。
