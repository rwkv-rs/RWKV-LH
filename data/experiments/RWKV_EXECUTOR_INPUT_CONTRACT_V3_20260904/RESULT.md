# RWKV Executor 匹配角色形状的状态尾部合同结果

日期：2026-09-04（Asia/Shanghai）

- E3 在固定 6 例、每例 3 次、共 18 次中严格通过 9/18，未达到 18/18 门槛，不进入生产。
- 三个用例 3/3 稳定选择 remaining path；另三个用例 3/3 稳定重复 completed path，说明主要不是 temperature `0.1` 的随机波动。
- E3 与 E1 的关键差异是把 completed action 再次投影到 bootstrap 的 `recent_exact_action_records`，同时在尾部 `execution_state` 表达 remaining state。结果表明这两个相互竞争的状态视图会使旧路径继续主导 WKV。
- 两次输出还生成了未授权别名 `filesystem-read_file`，证明 operation identity 也必须在唯一尾部合同中保持单一表达。
- 结果 SHA-256：`3c154b2b46e74ce5931dc9b4412e085e29bbe553585d2ac685b99a4a0b6abbd4`。
- 本实验没有使用 StateTune，也没有修改冻结矩阵、采样参数或评价口径。
