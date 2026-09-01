# G1J 零 State 架构修订

- 登记时间：2026-09-01；截至登记时，G1J 13.3B 推理请求仍为 `0`。
- 原因：原预注册把“复用 G1I Head/State”混入了基础权重替换，无法区分模型能力、跨权重身份错误和 State 迁移错误。
- 本文件替代原预注册“继续使用 G3/G6 State”与“S60 Head 可直接跨权重复用”的部分；固定 case、顺序、acceptance、相似度和阈值不变。

## 新固定边界

1. Selector 与 Executor 均从零 State 开始；不得加载 G1I State profile。
2. Selector Head 必须基于 G1J 冻结特征重新适配并登记身份；这是分类头适配，不是 State Tuning。
3. Planner、Selector、Executor 只通过角色配置绑定模型，代码和协议不得包含 G1I/G1J 或参数规模分支。
4. 先修复跨 HTTP 调用 State 的工程传递，再运行固定三例；不得把 State 丢失造成的失败记为模型能力缺口。
5. 只有工程门全部通过后仍可复现的 RWKV 语义错误，才进入 verified correction 数据收集和 State Tuning 决策。

## 当前身份

- Selector base PTH SHA-256：`966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239`
- Selector vLLM artifact SHA-256：`c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`
- Executor base PTH SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`
