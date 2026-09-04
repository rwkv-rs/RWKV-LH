# EXE-G6 task-level Stage C 确定性引擎复验 R6 执行冻结

登记时间：2026-08-30；登记时 R6 inference call 为 0、输出路径不存在、远端 R6 evidence/log
路径不存在、18075 空闲、18070 健康。

冻结身份：

- R6 预登记 SHA-256：
  `ef10a7f1a8aa0adda0d19f71f4a0270f577c830fbae470dd7afe20d87dd9304b`；
- runner：`temp/run_exe_g6_task_level_stage_c_deterministic_r6_ablation_20260830.py`，
  SHA-256 `2fa480d98a58fa4b8509c822a075bad5a3f352a8eade131aacce12b192ce3f8e`；
- deterministic evaluator：
  `temp/evaluate_executor_multi_profile_recovery72_deterministic_v2_20260830.py`，
  SHA-256 `4b2ed1bfa6c4e693241ea36e1a48e06a39948cc76d77405af4d8f3dd2b281006`；
- preparation result SHA-256：
  `88fb9c7e3754b5807dcae35f6255e5011007629b128e3a6ee36a31e0e4711d0b`；
- invalid R5 result SHA-256：
  `3c9fba9daaef88a580fce95be7da2b40bb2e316ffd5e38a814b6035a6e2b436d`；
- R4 failed result SHA-256：
  `eb72ab75b420d2fab4b794d23bc3e70490ddaa7dce33e9b226055d50f1495b69`；
- diagnosis SHA-256：
  `916f2cdea971f6de12033129b89ce1af1ec681050b5660d841fb1898f9ba34f2`。

推理前的独立 import 检查确认 `base.EVALUATOR == R6.EVALUATOR`，两者都解析为绝对路径
`/home/chase/GitHub/RWKV-LH/temp/evaluate_executor_multi_profile_recovery72_deterministic_v2_20260830.py`。

运行后不得修改文件或口径；只有每组内部 evaluator/protocol/raw 身份检查和 R5 全部门禁同时
通过，才输出 `deterministic_engine_gate_passed`。
