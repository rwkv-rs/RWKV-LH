# Round4 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 运行前离线命令：`.venv/bin/python -m pytest -q -s --disable-warnings`
- 运行前离线结果：`140 passed in 25.37s`
- 运行后离线命令：`.venv/bin/python -m pytest -q -s --disable-warnings`
- 运行后离线结果：`140 passed in 26.92s`
- 运行后 LH-Control 命令：`uv run rwkv-lh-control --output data/experiments/Round4/lh_control_30`
- 运行后 LH-Control 结果：`30/30 passed`

LH-Control 的 30 个任务及验收条件未改变。Round4 只把控制集假模型从旧 validation v1/二元返回值
迁移到 validation v2 `CriterionClaim`；它仍由假模型明确给出每个 proof 字段，控制器没有从验收条件
生成答案。

## 数据摘要

- Control catalog：`benchmarks/architecture_regression/lh_control_30/tasks.json`
- catalog SHA-256：`0606877c66360aefbf243b848a19fb349927e7a32e86565dbdc58e41ddcfbe80`
- Control runner SHA-256：`418ccf238ca1942373d603e73747dd5523afb22669583709ace0946b9ac51063`
- Control results SHA-256：`0b118acd48467205d38da638e3d1428dd3e287d13bb6a765a90f42431b3f6488`
- 用途：验证状态迁移、隔离、恢复、并发、证据持久化和协议边界，不替代真实 RWKV-E2E-90。
- 生成方式：运行上述固定入口；每题保留 `audit.json`、状态、事件和最终验证。
