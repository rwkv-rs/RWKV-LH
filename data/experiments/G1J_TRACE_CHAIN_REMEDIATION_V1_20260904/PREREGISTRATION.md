# G1J trace 全链路工程整改预注册

日期：2026-09-04（Asia/Shanghai）

## 输入与冻结边界

- 诊断输入：`data/experiments/LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_g1j_zero_state_public_dev_canary_b01_b14_p01_p07_v1/`。
- 有效完成 trace：B01-B14、P01-P06，共 20 个；P07 是人工停止记录，不计成功率分母。
- 不修改上述原始 trace、既有冻结数据集、Head 或用户已删除的实验记录。
- 本记录只验证工程控制链路，不把本轮结果冒充 StateTune 能力结果。

## 已观测基线

- 20/20 case 成功数为 0。
- 1124 次精确工具选择中，`list_directory=1044`、`move_file=80`，其余工具为 0。
- 20/20 case 的首次选择均为 `list_directory`。
- 20 个有效 trace 合计 2813 次协议拒绝；执行器原始输出大量退化为代码围栏或重复 Tool Call 标记。
- P07 在 222/240 calls 时由操作员停止，证明当前拒绝预算不能跨 controller slice 生效。

## 待验证根因

1. Selector feature 提取脚本把每条样本都接在同一个 bootstrap State 后独立计算，却把产物标记为 `persistent_history_replayed=true`；在线服务则真实延续上一轮 Selector WKV。
2. 训练样本是显式单工具的孤立模板，在线输入是包含 Planner 步骤、工具描述、Harness 结果和 audit feedback 的 `GoalFrontierStateV1`，不属于同一分布。
3. Executor 把每次已接受输出和后续工具 schema 累积进同一个 WKV，导致旧工具与格式锚点惯性。
4. 同一次已消费 Selector handoff 的参数失败可以无限生成新的“同工具重试”，且本地拒绝计数在每个 controller slice 重置。
5. Selector progress 把 run 生命周期累计拒绝数作为当前 delta 发送，和 parent checkpoint 的增量语义不一致。

## 固定整改范围

- G1J Head 必须声明真实的持久因果轨迹训练身份；旧 Head 缺少该身份时 fail closed。
- 旧 feature 提取脚本必须如实声明独立样本，旧训练入口不得再从该产物生成可发布 Head。
- Executor 在每个新 Selector 决策前从配置的角色初始 State 干净启动，并通过确定性状态投影携带最近 Harness 事实；同一 handoff 只允许一次参数修复。
- 协议拒绝预算按连续 action 拒绝持久计算，跨 controller slice 生效；一次成功 action 后重新计数。
- Selector 的 `protocol_rejection_count` 改为相对 parent Selector checkpoint 的增量。
- 修正当前环境示例、角色配置说明、协议身份与模型源文件 SHA 的漂移。

## 固定验证

1. 定向单元测试覆盖：Head 身份拒绝、持久 Selector continuation、每 action 干净 Executor、单次同工具重试、跨 slice 拒绝预算、Selector rejection delta。
2. `git diff --check`。
3. 完整 `pytest -q`。
4. 静态重放 20 个有效 trace，输出选择分布、拒绝分布和格式退化统计；不改变原始 trace。

## 判定

- 工程整改通过：上述测试全部通过，旧错误 Head 无法加载，无限重试路径被关闭，Executor 新 action 不继承上一 action 的 WKV。
- 模型能力不在本轮宣称通过：必须用新的在线同分布持久轨迹数据重新训练 Head，并在固定 Ladder 数据集上重新运行，才可比较成功率。
