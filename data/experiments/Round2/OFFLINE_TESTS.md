# Round2 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 离线命令：`uv run pytest -q -s`
- 离线结果：`117 passed in 19.08s`
- LH-Control 命令：`uv run rwkv-lh-control --output data/experiments/Round2/lh_control_30`
- LH-Control 结果：`30/30 passed`

两项均在 RWKV-E2E-90 全量结束后执行；LH-Control 不计入模型成绩。
