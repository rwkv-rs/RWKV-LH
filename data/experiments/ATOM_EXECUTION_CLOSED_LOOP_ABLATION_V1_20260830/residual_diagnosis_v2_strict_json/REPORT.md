# ContractProgress B 臂剩余失败归因 V1

| 层 | 固定观察 |
|---|---:|
| 用例 / worker | 10 / 146 |
| InputBudgetError | 2 |
| 依赖交接最大字符（旧→当前） | 126421 → 8488 |
| Reviewer 丢失外部 evidence（旧→当前） | 4 → 0 |
| Selector 调用 / ABSTAIN | 880 / 8 |
| Selector deadline 非 mutation | 179 |
| Executor rejection rate | 0.128703 |
| accepted mutation root coverage | 0.6 |
| external verifier pass | 0 / 10 |
| graph patch / review / replan | 36 / 36 / 26 |

- 当前统一投影重放闭合已识别工程缺陷：`True`。
- 2.9B 定向 state tuning：`True`。
- 13.3B 定向 state tuning：`True`。
- Planner/Reviewer 闭环整改：`True`。
- 必须在当前代码上重新运行固定端到端集，不能把投影重放当作发布验证。
- 原实验、RWKV raw output、阈值和评价口径均未修改。
