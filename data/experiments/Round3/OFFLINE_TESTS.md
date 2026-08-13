# Round3 离线与确定性门禁

- 执行环境：WSL `UbuntuRecovered`
- 离线命令：`uv run pytest -q -s`
- 离线结果：`126 passed in 20.93s`
- LH-Control 命令：`uv run rwkv-lh-control --output data/experiments/Round3/lh_control_30`
- LH-Control 结果：`30/30 passed`
- 进程树专项：`test_command_timeout_terminates_descendant_process_tree` 通过；bubblewrap
  `--die-with-parent` 下超时后 descendant 未写出延迟 marker。

Round3 正式 E2E-90 前曾运行同代码的预检 Control-30；正式 90 题完成后又在最终测试代码上重新
运行上述 30/30 和 126 条离线回归。本文件记录的是运行后门禁。
