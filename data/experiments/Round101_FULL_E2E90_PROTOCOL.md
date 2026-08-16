# Round101 full E2E-90 preregistration

## 固定范围

- 完整 `RWKV-E2E-90`：basic/medium/hard 各30题。
- 使用登记数据集、原外部验收与 Strict 口径；不把外部验收提供给模型。
- 模型与sampling沿用Round100。
- `max-transitions=200`；case concurrency固定为4，仅并行隔离用例，不并行同一run内的持久状态提交。
- 运行开始后不修改源码、数据、阈值或判分。

## 冻结源码

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `3790da4eb8f691793104ffa1de11bff46738730519529b970960aba31c9d5042`
- model_io `a50ed2ac82207df906b9c24dd21018de9fa6afa0fd2a421b58a143d806b8a533`
- controller `f11506ad6dbd6cffa5f0c3669480db5fb379ab6bb5eda449a79d959423bb0573`
- harness `78289e1c1f9aab5cc16047ec0826bcd42256eeb899ade5cc304537b3c13201cf`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- 离线 `96 passed`；Round100 Strict `4/4`。

## 命令

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round101_full_e2e90 \
  --max-transitions 200 --concurrency 4
```

## 事后分析

- 逐题读取raw generation、normalization、Task/Attempt、workspace和Final；标记第一次偏离及下游放大。
- 分别统计30题一组的Strict/Agent/External、FP/FN、请求/Task/Attempt。
- 检查90题Final非空和raw equality。
- 对每一类失败扩展到全部同类题与相关代码路径，不按单题修规则。
