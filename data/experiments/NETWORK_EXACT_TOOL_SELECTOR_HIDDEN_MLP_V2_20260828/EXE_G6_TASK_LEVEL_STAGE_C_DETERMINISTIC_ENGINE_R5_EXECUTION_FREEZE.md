# EXE-G6 task-level Stage C 确定性引擎复验 R5 执行冻结

登记时间：2026-08-30。登记时 R5 的本地输出、三个远端 evidence tag 与远端 multi log 均不
存在，18075 空闲，18070 健康，R5 inference call 为 0。

协议由
`EXE_G6_TASK_LEVEL_STAGE_C_DETERMINISTIC_ENGINE_R5_PREREGISTRATION.md` 固定，SHA-256
`1cb78b610c6ff5ee3f5802c0d327db096e1abd0067de906165ea0bd903bae9e4`。

冻结执行身份：

- runner：`temp/run_exe_g6_task_level_stage_c_deterministic_ablation_20260830.py`，
  SHA-256 `ed82499b277bc6e66b6bfc816c5b387f7dcd802d930073946c3b0b653bd7c0a4`；
- deterministic evaluator：
  `temp/evaluate_executor_multi_profile_recovery72_deterministic_v2_20260830.py`，
  SHA-256 `4b2ed1bfa6c4e693241ea36e1a48e06a39948cc76d77405af4d8f3dd2b281006`；
- preparation result：SHA-256
  `88fb9c7e3754b5807dcae35f6255e5011007629b128e3a6ee36a31e0e4711d0b`；
- R4 failed engine result：SHA-256
  `eb72ab75b420d2fab4b794d23bc3e70490ddaa7dce33e9b226055d50f1495b69`；
- diagnosis result：SHA-256
  `916f2cdea971f6de12033129b89ce1af1ec681050b5660d841fb1898f9ba34f2`；
- minimal engine overlay：SHA-256
  `bef729ec3340f23c2370b503835fddb669f573804eb55ad2202303a31feef350`；
- manifest：SHA-256
  `32c461d8488ae0f3b91f9ff123bb4c18fe61020ef190ac8da89b6086b0e1f715`；
- multi launcher：SHA-256
  `39a10a468a52af2980a2355caca218b0196247e6c2ddebd82ddc59bc8d62074d`；
- frozen helper：SHA-256
  `739df0e1f9743e79da73e9f8a147c3cbf0893a6253cceefae2a27f4d30c2ae96`。

执行顺序、数据、profile、GPU、端口、门槛与 R5 预登记完全一致。运行中不得修改上述文件；
不根据中间输出停止、调参或挑选结果。
