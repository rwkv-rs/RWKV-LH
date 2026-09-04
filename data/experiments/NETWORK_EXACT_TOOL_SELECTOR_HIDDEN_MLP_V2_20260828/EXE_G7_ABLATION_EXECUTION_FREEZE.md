# EXE-G7 全 checkpoint 消融执行冻结

冻结时间：2026-08-29（G7 checkpoint 训练完成和首次候选推理之前）。

- 执行器：`temp/run_exe_g7_network_retention_repair_ablation_20260829.py`，SHA-256 `227a4ae1291eae9e5aa5c12f5118988b45f8af9688779db0689217631e078c05`。
- raw-first evaluator：`temp/evaluate_executor_g6_dev_temperature_0p1_20260829.py`，SHA-256 `f482e1503d2acaeb1a7bb1e71517b1da10f31b01b505de75242c8e979b6be048`。
- 远端 G7 vLLM launcher：`scripts/run_remote_exe_g7_network_retention_repair_candidate_vllm.sh`，content SHA-256 `6266c514fdd2e1b67e52de010544e0fc726e07ea229e9cbd773852040ecdaed9`，mode 0755。
- parent G6 ablation result SHA-256：`8ca74af573a0aaae7503e585d4196d70622e8b7bffaa538d5e986c1ad2c0df2e`；parent state 为 G6 step1500 vLLM SHA-256 `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`，直接复用已验证 raw evidence，不重跑 parent。
- G4/G6 eval 与 manifest SHA-256 分别为 `f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d` / `d8dad84b355df504a5162017fedf3fd97036f91485869314187a513b6e71d5cf` 和 `f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee` / `ba3bb05085c9055b3230fdb79ed859146ddf46d586c8d0f0f3c30b40c810eb3e`。

checkpoint validation 完成后以其显式 SHA-256 作为唯一运行参数。固定顺序为 step150/300/450/600/750/900/1050/1200；每个点依次运行 G4 dev480 和 G6 dev480，共 960 个单次请求。即使早期 checkpoint 已通过，也必须评完全部八点。并发 8，temperature0.1、top-p1、top-k0、seed1067；每行只保留并评价第一次 raw response，hidden retry=0、postprocess=false。

选择与发布门逐字沿用 `EXE_G7_NETWORK_RETENTION_REPAIR_PREREGISTRATION.md`。本冻结之后不得为改善结果修改数据、阈值、顺序、采样或评价算法。
