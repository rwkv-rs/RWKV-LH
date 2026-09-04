# S59 × G3/G4 因子实验采样配置一致性补充登记

日期：2026-08-29（任何 S53/S59 × G3/G4 真实 Harness arm 启动前）

## 发现

预注册固定 Executor temperature 为 `0.1`，G3/G4 dev480 评测和远端 vllm-rwkv 启动配置也使用 `0.1`。但 `LongHorizonModel._SAMPLING` 仍显式写为 `0.05`，该请求级值优先于 `.env.local`/`RWKV_DEFAULT_TEMPERATURE=0.1`。旧的 S53+G3 R2 trace 和 `RUN_PROTOCOL.json` 均如实记录实际值 `0.05`，因此旧结果只能作为历史观察，不能冒充本轮固定 0.1 arm。

## 处理

- 在任何本轮因子 arm 启动前，将 `LongHorizonModel._SAMPLING.temperature` 修正为预注册值 `0.1`；top-p `1.0`、top-k `0`、presence/frequency penalty `0.0`、penalty decay `0.996` 不变。
- 本轮仍重新运行 S53+G3、S59+G3，以及 G4 可用时的两个 G4 arm；因子效应只使用本轮同配置结果，不复用旧 0.05 分数。
- 增加运行配置回归断言。定向回归命令固定为 `uv run --no-project --python 3.13 pytest -s -q tests/test_current_rwkv_input_layout.py tests/test_independent_network_selector_integration.py tests/test_model_session.py`，结果 45/45 通过。
- 修正后的 `rwkv_lh/model.py` SHA-256：`7ff83eefa14688aa57fdb237338945402076d7672a3d67b8c2edcabea7d7226d`。
- 修正后的 `tests/test_current_rwkv_input_layout.py` SHA-256：`46ce412e745db857f42215177359163eb135f8afb1aa0fa7313c6dcfb025aeaf`。

该修正使实际请求与预注册、state 评测及服务配置一致；不改变数据、门槛、相似度算法或选择规则，也不读取、诱导、修改、删除、重排或隐藏 RWKV 原始输出。
