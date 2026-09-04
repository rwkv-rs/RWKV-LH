# RWKV-LH Selector 单协议收敛预注册

日期：2026-09-04（Asia/Shanghai）

## 冻结起点

- 源提交：`ac539c71`。
- 固定备份：远端 `chase/pre-cleanup-20260904` 指向 `3f23a6a6`；清理第一阶段提交已推送到 `chase/rwkv-goal-loop-v2-cleanup`。
- 本阶段不训练、不生成、不加载、不选择任何 StateTune，也不训练 Selector Head。

## 唯一保留协议

- 生产输入协议：`rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1`。
- 唯一分类域：`NETWORK_EXACT_TOOL_LABELS` 的固定 25 类顺序，即 23 个操作、`final_answer`、`ABSTAIN`。
- 唯一 Head 结构：一个 25 类 MLP artifact；运行时必须验证模型、Head 文件、Head 逻辑摘要、特征协议、输入协议和 State profile 身份。
- 唯一状态语义：`persistent-causal-sequences.v1`；同一 Planner step/revision 内继续 Selector parent WKV，换 scope 从角色初始 State 重启。
- 唯一选择规则：当前 eligible labels 上的原始 logits argmax；Selector 不生成文本、不填参数、不执行工具。

## 删除与改名范围

1. 删除 compact protocol v3-v8 及其注册、兼容分支和专属测试。
2. 删除退役的 20 类 `protocol.py`、本地 `client.py`、coverage runner 及其专属数据脚本和测试。
3. 删除 Soft-MoE、description、takeover、hierarchical takeover、objective gate 等多代模型实现及专属测试/生成脚本。
4. 将当前 MLP artifact 从代际命名 `model_v2.py` 收敛为职责命名 `head.py`；生产服务只接受该 artifact schema。
5. 删除旧 Selector 数据代次生成器、旧 StateTune/远端训练脚本和旧服务启动脚本；保留 G1J 当前数据冻结、特征提取和 Head 训练入口，但不在本阶段运行训练。
6. 更新仍属于当前产品链路的客户端、服务、状态投影、集成测试与脚本导入。

历史实验产物只作为不可执行记录保留；本阶段不改写未跟踪的数据目录。

## 固定验证

- 静态扫描不得再出现 `compact_protocol_v3` 至 `compact_protocol_v8`、Soft-MoE/takeover/objective-gate 或退役 20 类客户端的生产引用。
- 当前 G1J renderer、25 类标签顺序、eligible mask、父 State 连续性、Head 身份门和 Selector→Executor 交接测试必须通过。
- 完整 `pytest -q`、`compileall`、`git diff --check`、`uv lock --check` 和 wheel 构建必须通过。
- 结果、删除文件、测试数量和剩余阻断写入同目录 `RESULT.md`。
