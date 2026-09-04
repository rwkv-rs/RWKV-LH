# Agent Ladder V4 真实 Harness 复验预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- run：`run_s66_g3_g6_post_semantic_handoff_v4`
- 目的：在完全相同的十题、顺序、acceptance、G3/G6 Executor state 与 S66 zero-state Selector 下，测量 Planner v8 语义 schema 和 exact selection handoff 修复后的真实闭环结果。

## 相对 V3 的唯一处理变化

1. strong Planner 使用受支持的 Structured Outputs `anyOf` 分支，把 `kind/effect_scope` 合法组合和 finalizer 约束放入 schema；已有目标 mutation 的 latest-read 依赖仍由语义校验 fail-close。
2. Selector selection ID 经 Controller 进入 Executor 拒绝/重试事件；retry 只能继承同一已提交 operation/schema；`final_answer` 也必须经过独立 Selector handoff。
3. 2.9B state 消融已按预注册拒绝全部 S61 state，继续固定 S66-M1 zero state。

没有修改 Planner/Selector/Executor 职责，没有换 13.3B profile，没有隐藏 `final_answer`，没有增加控制器补动作，也不允许修改、删除、隐藏、重排、截断、修复或替换 RWKV raw output。

## 冻结比较

- 数据：原 Agent Capability Ladder V1 十题与原顺序，acceptance/verifier 不变。
- 对照：V3 `results.json` SHA-256 `27c8b495cbf58a3dead94505e98f38f80bb15195f9bcdb12633d938ddd6b7883`，strict/external/completed `0/10`。
- Selector：S66-M1，head SHA-256 `858982e45822b975c3c4cf0badf4a89c12b2c85a76e7157da85809a246b7c304`，zero state，物理 GPU0。
- Executor：offline G3 step2000 SHA-256 `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`；network G6 step1500 SHA-256 `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`；远端物理 GPU0；task 内 profile switch 必须为 0。
- Planner：`gpt-5.4-mini`，reasoning `none`，无 fallback，strict JSON；schema response name v8。
- 运行：concurrency 3、max transitions 300、progressive disclosure；18075 实验服务与 29621 Selector，18070 产品服务不得停止或替换。

## 固定评价

继续使用原 acceptance 计算每题 strict/external/completed 和连续层级，不因结果调整。另登记：

- Planner HTTP/JSON/语义拒绝与 retry；
- Selector 选择次数、ABSTAIN、eligibility、显式/继承 selection binding；
- Executor raw generation 接受/拒绝、schema/参数错误；
- mutation、验证、网络证据、终止原因；
- raw bytes/SHA/事件一致性和 profile switch。

## 禁止预设错因

运行前不把失败预归因给任何一层。每个失败必须按实际事件链分别检查：

1. Planner graph 是否与原请求和依赖一致；
2. Selector raw argmax、eligible argmax 与已提交 operation 是否正确；
3. selection ID、schema digest、retry inheritance 与 final handoff 是否连续；
4. Executor raw 输出是否满足被提交 schema、参数和执行目标；
5. Harness 执行事实、observation、transaction gate 与外部 verifier 是否正确。

只有在上游选择和绑定均有直接证据正确时，后续参数、内容、修复或总结失败才可计入 13.3B 候选残差；反之必须归回对应上游。即使 V4 仍出现 Selector 错误，也不能因 2.9B state 静态消融被拒绝而忽略。Harness/verifier 若存在系统性缺陷，同样按根因修复，不能通过模型 state 掩盖。V4 是 holdout 评价，任何题目文本、路径和 verifier marker 均不得进入后续 train/dev。
