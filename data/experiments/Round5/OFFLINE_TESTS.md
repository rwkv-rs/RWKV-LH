# Round5 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 运行前离线结果：`146 passed in 10.81s`
- 运行前 LH-Control：`30/30 passed`
- 运行后离线结果：`146 passed in 9.99s`
- 运行后 LH-Control：`30/30 passed`
- E2E 目录与历史状态迁移、边界、异常、恢复、并发测试均包含在 146 项回归中。

LH-Control 的任务与验收条件未修改。fixture model 只从 validation v2 recursive claim 迁移为 validation v3
linear assertion，并继续明确给出 source、selector、literal、value 和 transform；控制器没有从验收条件生成
assertion。

## 数据摘要

- Control catalog：`benchmarks/architecture_regression/lh_control_30/tasks.json`
- catalog SHA-256：`0606877c66360aefbf243b848a19fb349927e7a32e86565dbdc58e41ddcfbe80`
- 运行前 Control results SHA-256：`17f95b30518d203ed37877c8aac315346a365c30044f697883ca0a6185297275`
- 运行后 Control results SHA-256：`6bd9e3d5b2d5b07be6ddbb3c0beff54cb94df5cb5520c2ccdc0118f6b594a50f`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`
- 用途：Control 验证架构不变量；reference 只在完整模型运行后做诊断相似度，不参与生成。
