# RWKV-LH native-state service fixed cases v1

- 来源：2026-08-31 手工构造的无标签、无项目私有事实 continuation 文本。
- 版本：`2026-08-31.v1`。
- 用途：比较同一 13.3B RWKV 服务的一次性 token 输入与 native state
  create/append/fork 输入；另用于 commit/rollback/import 和 cache eviction 生命周期验证。
- 生成方式：在首次 live state 调用前固定写入 `cases.json`；运行器只读取，不改写。
- 评价口径：固定 greedy 参数下比较原始 token id；不做文本修复、截断、重排或人工判定。
- 文件摘要：由实验运行器在调用模型前计算并写入正式结果，摘要不作为可调整参数。

