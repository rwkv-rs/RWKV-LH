# EXE-G7 训练启动器预检修正补充登记

登记时间：2026-08-29 19:53（Asia/Shanghai），任何 G7 `train.py` 进程、输出目录或 checkpoint 产生之前。

首次启动 PID `2881627` 在 shell 预检阶段退出。远端训练日志为 0 bytes，训练输出目录不存在，GPU 未加载训练进程，checkpoint 数为 0。根因是启动器把 `jq -r '.target_suffix_audit.exact_label_match_rate'` 的有效输出 `1.0` 与字符串 `1` 比较；验证报告本身为零失败，数值也精确等于 1.0。

允许的唯一修正是把该字符串比较替换为 JSON 数值断言：

```bash
jq -e '.target_suffix_audit.exact_label_match_rate == 1.0' "$validation_file" >/dev/null
```

G7 数据、数据 hash、parent、base model、GPU0、训练超参数、checkpoint 步数、离线/在线评价数据、相似度算法和所有发布门均不改变。旧启动器、空日志和首次 preflight manifest 必须保留为 invalid pre-training evidence；修正后的启动器使用新 SHA-256，并重新生成 `pretrain.r2` manifest 后才能再次启动。

该事件没有 RWKV 请求或输出，因此 `raw_rwkv_output_modified=false`，也不存在需要隐藏、删除或替换的模型输出。
