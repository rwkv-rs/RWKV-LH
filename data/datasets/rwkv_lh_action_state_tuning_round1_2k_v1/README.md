# RWKV-LH Action State Tuning Round1 2K v1

这是首轮失败驱动 state-tuning 数据，不是通用任务 SFT，也不是旧 pilot 的扩量副本。

- train：2000 条；dev：200 条。
- verified trajectory：1321。
- 每条训练行都指向 `failure_registry.jsonl` 中的历史错误状态迁移。
- prompt 来自当前 progressive Controller/ModelSession 真实回放；target 由本地 oracle 和
  ActionHarness 验证。
- rollover 使用 `action-result-decision-state.v1` 单一历史投影；action result 不再同时以
  exact record 与 retained event 重复注入。
- 网络证据为冻结 `.invalid`；隐私 Gate 样本 backend execution 为 0。

## 训练入口

使用 `rwkv_state_tuning.train.requires_target_suffix.jsonl`，并固定：

```text
--data_type jsonl --loss_mask target_suffix --peft state --op fla
```

`dev`、private oracle、preference seed 和冻结 holdout 不得进入训练。远程 tokenizer/ctx 检查
通过前，manifest 的 `remote_tokenizer_validated` 保持 false，不得启动训练。
