# S60 发布门槛范围修正：当前阶段不以强 Planner 架构作硬阈值

登记时间：2026-08-29；发生在任一发布验证运行之前。

原发布预注册把 Round148 的 41 strict / 57 completed 设为硬门槛。复核其冻结协议后确认 Round148 是 `strong-supervisor-parallel-rwkv-atoms.v4`：GPT-5.4 在线 Planner/Reviewer，属于用户定义的中期目标，不是当前“补齐本地联网且不损失现有 Harness”阶段的同架构基线。继续把 41/57 当硬门槛会混淆目标，无法分离网络、Selector 与 Executor state 的效应。

在尚未运行发布 Full90 前，固定修正如下：

1. Round148 的 41/57 和结果哈希继续报告，但只作跨架构诊断，不作当前发布硬门槛。
2. 同轮依次运行三个可适用层级：`S53+G3` 保留基线、`S60+G3` Selector-only 候选；若因子实验选择 G5，再运行 `S60+G5` 最终候选。三者使用同一 Full90、参数、采样、Harness、完整性验证与物理 GPU0。
3. S60+G3 必须在 strict 数和 completed 数上均不低于 S53+G3，且 S53+G3 已 strict 通过的 case 零回归。
4. 若使用 G5，S60+G5 必须在两项计数上均不低于 S60+G3，且 S60+G3 已 strict 通过的 case 零回归。若选择 G3，最终候选即 S60+G3。
5. 三个运行均须满足各自输入协议完整性；V7 字节尾部只要求 S60 arm，S53 只作为 V4 保留对照，不得发布。

live2、retrieval9、全量 tests、原始输出不干预和配置切换规则完全不变。本修正避免用中期 Planner 成果替代当前 RWKV Harness 的同架构消融，也不依据任何本轮 Full90 结果调整门槛。

