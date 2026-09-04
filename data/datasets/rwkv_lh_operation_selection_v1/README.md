# RWKV-LH operation-selection micro-dataset v1（历史归档）

该数据集用于已经删除的两阶段 `lh_select_operation` 架构，只为复核 Round80 历史实验保留，不代表当前直接工具调用协议。

- 来源：RWKV-LH `ActionDefinition` 注册表和统一 Task lane 控制操作；用例是人工构造的通用文件、JSON、命令、collection、chunk 和修复场景，不包含 short7、Round77 或 E2E 题目文本。
- 版本：`rwkv-lh.operation-selection-dataset.v1`。
- 用途：只隔离测试 Task lane 第一步是否严格输出 `lh_select_operation(operation)` 并选择正确 operation；不绑定参数、不执行动作、不评价完整规划能力。
- 覆盖：15 个公开 harness action 与 5 个 Task lane 控制 operation 全覆盖，共 30 例；额外用例覆盖易混淆操作和 observation 后续选择。
- 生成方式：先从本地注册表列出 operation，再为每个 operation 人工编写一个无歧义任务；补充 10 个差异化/续接场景。数据冻结后才实现 runner。
- 固定采样：temperature 0.05、top_p 1.0、top_k 0、presence/frequency penalty 0、penalty_decay 0.996、max output 96；每例 3 次，最多并发 8。
- 固定评价：严格 G1i 解析、exact operation、selector bypass、unknown operation、三次完全一致，以及 `utf8-byte-5gram-cosine.v1` 原始输出相似度；near-stable 阈值 0.95。
- 文件摘要：见同目录 `manifest.json`。
