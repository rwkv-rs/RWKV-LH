# Round147：Exact Dependency Observation Canary 分析

日期：2026-08-22

## 结论

Round147 固定三例门槛全部通过：`3/3` strict PASS。该结果支持将
`strong-supervisor-parallel-rwkv-atoms.v4` 晋级到固定 Full90，而不是开始生成训练数据。

本轮唯一变量是 dependency handoff：下游 atom 只接收有界的精确 action observations 与
artifact 元数据，不再接收 RWKV natural-language candidate summary。M16 的
`primary/item_05.json` 精确观测值 `13` 已正确进入 writer，`recovered.json` 不再被其他 scout
越界总结中的臆造值污染。

原始记录：`data/experiments/Round147_exact_dependency_observation_canary_B04_M16_LH06_20260822/`

## 固定结果

| Case | Strict | External | Agent | Stages | RWKV requests | Actions | GPT calls |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | PASS | PASS | completed | 4 | 8 | 4 | 4 |
| E2E-LH06 | PASS | PASS | completed | 5 | 19 | 9 | 5 |
| E2E-M16 | PASS | PASS | completed | 4 | 14 | 8 | 4 |

## 架构门核验

- 三题均出现真实重叠执行：B04 有 2 个并发 atom；LH06 有 4-lane scout 与 2-lane writer；
  M16 有 4-lane scout。
- 所有 mutation atom 均为一个 operation、一个 action；没有共享 snapshot 上的并发写入。
- 所有 18 个 atom completed；无 failed/interrupted atom、ScopeViolation、InputBudgetError 或
  supervisor stage failure。
- stage 数为 B04=4、LH06=5、M16=4，均不超过预注册上限 8。
- 所有完成态 Final 均为 byte-exact raw RWKV final output；GPT 没有执行工具或改写最终答案。
- B04 manifest 的实际字节为 `archive/2026/source.txt\n`；LH06 选择
  `requirements/approved.json`；M16 的 05 value 为 `13`，五项与 sources 映射均正确。
- 完整 Python 回归为 `139 passed`；定向架构回归为 `45 passed`。

## 剩余风险

三例只能证明已知的 path literal、authority/injection 与 dependency fact-integrity 链路，不代表
90 例上的总体收益。LH06 仍发生 2 次 RWKV 协议拒绝，并多出一次 EVIDENCE rewrite，说明 atom
执行质量仍有训练价值；但它们没有突破 action budget、scope 或事务边界。下一步必须用固定 Full90
量化 TP/FP/FN、各难度层、控制面可靠性与实际并发，不能据三例直接替换 R126。

