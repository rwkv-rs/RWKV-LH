# S61 远端启动器数值格式检查修正

- 日期：2026-08-30（Asia/Shanghai）
- 范围：只修正训练启动前的 JSON 数值检查；数据、模型、训练参数、评价口径与 RWKV 输出均不变。
- 原始预检报告 SHA-256：`7c3367d4e5adeafc5736f3269a75b5bb32dfb61ba898bf7518273995b099d62c`
- 远端验证结果 SHA-256：`c565f8a50f469da155e9530daaa531a38dab6918feff873604d675192519d3fe`
- 原启动器 SHA-256：`15fa48a953debdbbcf12a84ec444ad1176289fa24863a19737eb9b8946d433aa`
- 修正后启动器 SHA-256：`cbbb209a9e486ff18b0e57b42515a899dcda44eee4498dbee13374854393b689`

## 触发与根因

第一次启动在创建输出目录和执行 `train.py` 之前 fail-close。`bash -x` 证据显示，权重、train、dev、manifest、validation 的 SHA-256 全部一致，失败发生在 `exact_label_match_rate` 检查：验证 JSON 合法地序列化为 `1.0`，启动器却用字符串 `"1"` 比较。

## 修正

把字符串格式比较改为 `jq -e '.target_suffix_audit.exact_label_match_rate == 1.0'` 的数值比较。原失败启动器已逐字存档为 `run_s61_state_training_remote_preflight/launcher.precheck-numeric-format-bug.sh`；第一次启动没有训练进程、没有 checkpoint、没有输出目录，也没有影响受保护的 18070 产品服务。

修正后仍需重新通过以下门槛才允许启动：固定数据与 validation 哈希、GPU0 UUID、GPU0 空闲显存下限、18070 存活、18075 空闲、无并发 `train.py`、目标输出目录不存在。
