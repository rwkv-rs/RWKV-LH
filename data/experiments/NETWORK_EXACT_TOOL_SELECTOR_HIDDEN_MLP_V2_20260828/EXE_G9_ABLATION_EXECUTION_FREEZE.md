# EXE-G9 离线消融执行冻结

冻结时间：2026-08-30；G9 训练运行中，任何 G9 checkpoint 推理之前。

- runner：`temp/run_exe_g9_stable_schema_contrast_ablation_20260830.py`，SHA-256
  `e0a5cac6fc435823bb58340ef41b46ef68ad7ed424c877a03ba5289ac522e9f4`；
- checkpoint validator：`temp/validate_remote_exe_g9_state_checkpoints_20260830.py`，
  SHA-256 `613997cb7ef5f3b4b768610644e8a99f2d32e9da0dd1e08f9cb1df89a3bfca66`；
- frozen service/evidence base SHA-256：
  `da9368e10e09896940f3beed610a9fef5e9e4377d56a41e997ce109bb4768365`；
- raw-first evaluator SHA-256：
  `f482e1503d2acaeb1a7bb1e71517b1da10f31b01b505de75242c8e979b6be048`；
- variable-row integrity validator SHA-256：
  `eb5a0ad2a02195f74b3efb3d265372cf90fc9552dab1b1bb3c774405ff7439de9`；
- G9 candidate launcher SHA-256：
  `4ed2582e1744055e4892e172f71b2b0cc60025af768fad6008cfd9fb4b5e43be`；
- G6 parent launcher SHA-256：
  `3d6f0841959e4929e178c3cf42ecabb66ea38558f6919d4785999e3c3d13c69a`；
- G9 preregistration SHA-256：
  `0c50e9d185ffe5732fffb9eeba3e3affd535e59b425eb619f9646f9f3678c54a`；
- G8 holdout metadata amendment SHA-256：
  `926a64325907e0b53df382e52179d31bd5cab12caa53b576d32fcc5049452b1f`；
- G4 dev480 SHA-256：
  `f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d`；
- G6 dev480 SHA-256：
  `f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee`；
- G8 holdout metadata-v2 240 SHA-256：
  `0b7bc953b40eedb4f0d6169e88e85ad615180ca34d75abf02023e7d14399c48d`。

G6 parent 的 G4/G6 证据继续复用冻结结果；G8 holdout 对 parent 在 G9 输出中只运行一次。
G9 step250/500/750/1000/1250/1500/1750/2000 全部运行 G4+G6+G8 holdout，
每 checkpoint 1,200 行。sampling 固定 temperature0.1、top-p1、top-k0、seed1067，
concurrency8；每行一次请求，hidden retry=0，postprocess=false，raw-first append-only。

checkpoint validation 文件在训练自然结束后生成，其 SHA-256 必须作为显式 CLI 参数注入；
runner 不接受缺失、格式错误或内容不符合 G9 contract 的报告。选择规则为预登记全部门槛的最早
checkpoint，但仍必须评完八组。18075 仅候选推理使用，产品 18070 每个 arm 前后保持健康。
任何原始 RWKV response body、text、token IDs 均不得改写、删除、重排或隐藏。
