# EXE-G6 task-level Stage C 引擎执行冻结

登记时间：2026-08-30；登记时 G9 step2000 尚未完成，最终 G9 `ABLATION_RESULT.json`
不存在，且本备用实验尚未复制远端隔离引擎、启动 18075 或发起任何推理。

只有 G9 最终结果为 `no_candidate_passed` 才允许执行。所有运行参数与门槛沿用
`EXE_G6_TASK_LEVEL_MULTI_PROFILE_FALLBACK_PREREGISTRATION.md`，SHA-256
`9b5956a70fa103256ca6cb880f64352aa7a57a0d2f1c0e2f6dfa5c845708a34e`。

冻结实现身份：

- remote preparation：`temp/prepare_exe_g6_task_level_stage_c_remote_20260830.py`，
  SHA-256 `7210dbeaa6cdcabd2ace50f1899f208e4d5a5e44cd93ea98e1acca09af1677d4`；
- multi-profile launcher：`scripts/run_remote_exe_g6_task_level_multi_profile_vllm.sh`，
  SHA-256 `39a10a468a52af2980a2355caca218b0196247e6c2ddebd82ddc59bc8d62074d`；
- engine runner：`temp/run_exe_g6_task_level_stage_c_engine_ablation_20260830.py`，
  SHA-256 `66147656f5a1bc4cd212516d9d32358e99a1e5c956b4211eb374fa8b7035c48b`；
- recovery72 evaluator：`temp/evaluate_executor_multi_profile_recovery72_20260830.py`，
  SHA-256 `f7c88bba16389d4cced71601c952cd0a09b6ec741b5a869c204e0fcd0c20f083`；
- frozen helper：`temp/run_exe_g9_stage_c_engine_ablation_20260830.py`，
  SHA-256 `739df0e1f9743e79da73e9f8a147c3cbf0893a6253cceefae2a27f4d30c2ae96`；
- G3 dedicated launcher SHA-256
  `4b9bc8493b44ee92f1d57e125103bacc5684fc8047a3ee1e3d95fbf0f207e38c`；
- G6 dedicated launcher SHA-256
  `3d6f0841959e4929e178c3cf42ecabb66ea38558f6919d4785999e3c3d13c69a`。

固定顺序：准备隔离引擎与 manifest；运行 fail-closed/task-level 单元测试；分别运行 G3、G6
dedicated recovery72；单次启动 multi-profile 引擎；按 G3→G6 与 G6→G3 两种顺序运行完整
recovery72；比较 raw text、token IDs、finish reason、canonical pass/fail 和 warm latency；停止
实验服务并复核产品 18070。不得根据中间结果修改脚本、门槛或顺序。
