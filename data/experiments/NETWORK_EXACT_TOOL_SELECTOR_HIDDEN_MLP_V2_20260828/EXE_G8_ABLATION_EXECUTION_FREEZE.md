# EXE-G8 离线消融执行冻结

冻结时间：2026-08-29；G8 训练运行中，任何 G8 checkpoint 推理与 G6 parent 的 G8 holdout 推理之前。

- runner：`temp/run_exe_g8_engineering_retention_repair_ablation_20260829.py`，SHA-256 `427dc69c445108eb2ec36eb97e618c74f7259e666519added6a675739ccd6f63`；
- raw-first evaluator SHA-256：`f482e1503d2acaeb1a7bb1e71517b1da10f31b01b505de75242c8e979b6be048`；
- variable-row integrity validator SHA-256：`eb5a0ad2a02195f74b3efb3d265372cf90fc9552dab1b1bb3c774405ff7439de`；
- G8 candidate launcher SHA-256：`eabc25fe9915465a06f3378ac2c696e2aeae161f469a74f93d61332bc0401fb5`；
- G6 parent launcher SHA-256：`3d6f0841959e4929e178c3cf42ecabb66ea38558f6919d4785999e3c3d13c69a`；
- G4 dev480 SHA-256：`f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d`；
- G6 dev480 SHA-256：`f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee`；
- G8 holdout metadata-v2 240 SHA-256：`0b7bc953b40eedb4f0d6169e88e85ad615180ca34d75abf02023e7d14399c48d`；metadata manifest SHA-256 `4bf71e676e9a1cc09969fdcf10a7fc13bec3f8340f5d3eb348c229952a9190f5`；
- G6 parent G4/G6 证据继续复用固定原始 run；G8 holdout 对 parent 仅运行一次并永久保存；
- 每个 G8 step250/500/750/1000/1250/1500/1750/2000 都完整运行 G4+G6+G8 holdout，共 1,200 条；即使早期候选通过或失败，也评完全部八组；
- sampling 固定 temperature0.1、top-p1、top-k0、seed1067；concurrency8；每行一次请求；hidden retry=0；postprocess=false；raw-first append-only；
- 选择规则与所有数值门槛完全采用 `EXE_G8_ENGINEERING_RETENTION_REPAIR_PREREGISTRATION.md`，不得根据结果修改；
- 候选仅用远端 18075 和 physical GPU0；产品 18070 每个 arm 前后检查，绝不停止；
- checkpoint validation 文件 SHA 在训练自然结束后作为显式 CLI 参数注入并写入最终结果，runner 拒绝无效或未固定的 SHA；
- 原始 RWKV response body、text、token IDs 均先保存且不改写、不删除、不重排、不隐藏。
