# Frontend native stack smoke v6

- 来源：2026-08-31 前端部署验收需求，人工预登记的确定性项目目录盘点。
- 版本：`6.0.0`。
- 用途：从前端入口验证 Planner、2.9B exact choice-tool、13.3B native recurrent-state executor、隔离 harness 与 Goal 自主完成。
- 数据文件：`cases.json`。
- `cases.json` SHA-256：`c08879d05965f09497fe931fe5e84f07fae2116949351325ef049ca6f3a7df36`。
- 生成方式：固定写入两文件项目、预期递归清单、`contract_graph` 模式、离线 runtime policy 和精确 final；运行后不得修改评价口径。

## 固定评价口径

1. 运行由 `POST /api/runs` 创建，`stop` 入口必须不存在。
2. 至少提交一个 `contract_graph_patch_committed`。
3. 至少提交一次 2.9B exact selection，依据为 eligible raw-logit argmax，并保留 selector state 引用。
4. 13.3B 使用 `rwkv-lh.native-state.v1`，`static_replay_tokens=0`、`prompt_replay=false`。
5. 至少一个工具动作成功，目录完整观察与固定清单精确相等；审计中的网络动作和 workspace mutation 均为零。
6. Goal 仅由 RWKV explicit final 进入 `completed`，最终文本与预登记文本精确相等。

离线和隔离是 runtime policy，不要求 Reviewer 用正面工具结果证明“某动作从未发生”；验收器直接读取完整 action ledger 判定零次发生。
