# Round1 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 离线命令：`uv run pytest -q -s`
- 离线结果：`112 passed in 19.65s`
- LH-Control 命令：`uv run rwkv-lh-control --output data/experiments/Round1/lh_control_30`
- LH-Control 结果：`30/30 passed`
- LH-Control 明细：`lh_control_30/results.json` 与 `lh_control_30/REPORT.md`

两项门禁均在 RWKV-E2E-90 全量运行完成后执行。LH-Control 不计入 90 题模型成绩。
