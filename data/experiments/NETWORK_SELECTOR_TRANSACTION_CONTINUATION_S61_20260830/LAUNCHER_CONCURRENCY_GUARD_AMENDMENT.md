# S61 启动器并发训练检测修正

- 日期：2026-08-30（Asia/Shanghai）
- 已实际启动训练的启动器 SHA-256：`cbbb209a9e486ff18b0e57b42515a899dcda44eee4498dbee13374854393b689`
- 后续使用的修正启动器 SHA-256：`3f68ecaa0f3c81e1da34524aab128937c147a2e674f8c4b64434318af03a4855`
- 实际启动器存档：`run_s61_state_training_remote_preflight/launcher.used-for-training.sh`

训练启动后审计发现，旧并发检查只匹配带斜杠的 `.../train.py`，而本次进程命令行为 `.venv/bin/python train.py`。本次启动前已通过独立的完整进程表确认没有其他训练，且当前只有一个父训练进程及其两个 DataLoader 子进程；因此不重启、不改变本次训练。

后续启动器把判断改为同时约束进程名以 `python` 开头，并匹配相对或绝对的 `train.py` 参数。该修正只加强启动前 fail-close，不改变数据、模型、state、优化参数、RWKV 输出或当前运行中的进程。
