# Planner Semantic Schema Canary V1 数据说明

- 日期：2026-08-30
- 用途：验证 strong Planner 的严格 JSON Schema 能否直接排除错误的 `kind/effect_ceiling` 组合，并降低已有目标修改时的读取依赖错误。
- 来源：5 个公开、人工构造的最小任务。缺陷类别来自冻结的 V3 生产轨迹聚合统计；没有复制隐藏验收、RWKV 原始输出或强模型原始输出。
- 版本：`rwkv-lh.planner-semantic-schema-canary-cases.v1`。
- 生成方式：在 API 调用前人工冻结；运行脚本只把声明式 case 编译成 `ContractPlanRequest`，不得修改 case 文本、顺序或模式。
- 数据边界：只含公开请求、公开工作区路径和一个公开的已完成读取节点 ID。

文件摘要登记在同目录 `MANIFEST.json`；实验参数和阈值登记在实验目录 `PROTOCOL.json`。
