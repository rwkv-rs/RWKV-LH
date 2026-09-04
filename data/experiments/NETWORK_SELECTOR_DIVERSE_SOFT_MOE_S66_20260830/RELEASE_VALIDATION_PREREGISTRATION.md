# S66 本地 Agent 第一版真实发布验证预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 选择器：已通过一次性 locked test 的 `S66-M1`，head SHA `858982e45822b975c3c4cf0badf4a89c12b2c85a76e7157da85809a246b7c304`
- 选择器 locked result SHA：`5d24d7abedaa54d0cb586e5500a39ffb8a62f918f1fbb7bd3e418b78f153ed0d`

## 固定目的

用冻结的 10 例 Agent Capability Ladder 验证真实 harness，而不是再测单一分类环节。强模型只担任 Planner/Reviewer；2.9B S66 只选择工具；13.3B 按任务固定使用 G3 offline 或 G6 network state 执行；同一 run 不切 state。三例 Harness bugfix canary 是这 10 例的固定子集，从同一次运行派生，避免重复启动和重复模型请求。

## 固定运行

- 远端实验服务：物理 GPU0、18075，经既有本地 29613 访问；产品 18070 全程保持健康。
- 本地选择器：物理 GPU0、29621、zero state、V7 问题末端、一次 Hidden(mean+last)。
- Planner/Reviewer：`gpt-5.4-mini`，reasoning `none`，Planner 4000 tokens，Reviewer 2400 tokens。
- `agentladderv1` 原 10 例、原 acceptance、并发 3、最多 300 transitions、progressive disclosure、independent Selector。
- Executor 原始响应 append-first；不得修改、删除、重排、隐藏、截断、修补或替换任何 RWKV 原始输出。

## 固定评价

沿用 Ladder V1 口径：前四层 8/8 strict 且第五层至少 1/2 strict 才是第一正式版本候选；能力上限为从 L1 开始连续全过的最高层。另记录 external、agent_completed、每例路由、G3/G6 绑定、原始输出哈希完整性、三例 bugfix 子集和联网证据。

若失败，只按“正确路由后的执行残差”判断 13.3B state tuning 需求；不得用 13.3B 掩盖 Selector 错误，不得用 Ladder 数据训练或反向修改 S66。
