# G1J per-stage State Tuning v1：zero baseline readiness 预登记

登记时间：2026-09-02T13:11:47+08:00。本文在本轮服务器模型启动和任何新 G1J 模型请求前固定。

## 目的

建立以后 StateTune A-I 消融共同使用的初始 zero-State 对照，并严格区分：

1. 源码与冻结 Agent Ladder 可复现性；
2. 服务器、G1J 基础权重和 native recurrent-state 服务能力；
3. Gate 0、五个生产 renderer、五套数据和 evaluator 的 readiness；
4. 五个逐环节 zero-State Dev 指标；
5. 全 zero 固定 Agent Ladder 的严格端到端结果。

本轮不加载旧 Head、旧 State、旧 checkpoint、旧 profile、旧数据代号或旧实验结果，不训练 State，不选择 checkpoint，不更新默认 profile，不修改产品代码。

## 冻结身份

- branch：`chase/rwkv-goal-loop-v2-cleanup`
- commit：`9ae5eda1b8c5196ef401b62414e7d9ffd9243120`
- tracked diff SHA-256：`65ab18f8e5e529891c9faf7b3c0520178fa8f9907bc70c4dd7a8768c316d26c8`
- `rwkv_lh/` 与 `scripts/` 源码聚合 SHA-256：`0afdf064c25b86baf18985304358ef86337021e62c3f39bcf8120cfbe7eb23f3`
- E2E runner SHA-256：`72af86fa6684e1dde5dadfb3b05c74f56de57043d40dba0e607044d0bc754eee`
- StateTune 冻结协议 SHA-256：`c98908b2e24b863a54e6056c6b98e72f4b86cf53573b311a720e47362fcda6ed`
- 脱敏运行配置 SHA-256：`d43ef93904b0a266a278f2d9370f51b789d03e5bb6e843c1f3acc09d7066e408`
- Agent Ladder tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`
- Agent Ladder hidden acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`
- G1J 2.9B 基础权重 SHA-256：`966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239`
- G1J 13.3B 基础权重 SHA-256：`559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`
- State：五个角色全部为 `zero/unset`；训练 State 数量为 `0`
- 允许 GPU：远端物理 GPU 0 和 3；GPU 1/2 不探测、不停止、不复用

## 固定顺序与停止规则

按冻结协议顺序执行：Gate 0 -> source registry -> generators/evaluators -> datasets -> five zero Dev -> all-zero Agent Ladder。

若 Gate 0 模块、独立角色生命周期、新 V8 Head 身份、五个生成器/evaluator 或正式数据任一缺失：

- readiness 记为 `FAIL_CLOSED`；
- 只允许完成源码测试、数据 catalog 校验和服务器只读/zero-State capability preflight；
- 不运行五个正式 Dev，不运行正式 Agent Ladder，不生成可与 tuned State 比较的分数；
- 不以旧 V7 Head 或旧兼容运行填补缺口；
- 不把 `not run` 记为模型失败或 `0` 分。

## 固定判定

- 结构测试：记录 passed/failed/warning，失败必须保留完整首错和同类范围。
- 数据 catalog：tasks/acceptance identity 与隐藏验收隔离必须通过。
- 服务：模型名、基础权重 SHA、GPU UUID、`/v1/models` 与 native-state capability 必须一致。
- State 注入：不得出现非零 profile ID/SHA、initial-state path、checkpoint 或父 State。
- 正式 zero Dev 与 Agent Ladder：只有上述先决条件全部通过后才允许产生指标。
- 所有 INVALID/FAIL_CLOSED 结果单独记录，不进入以后 StateTune 增益分母。

