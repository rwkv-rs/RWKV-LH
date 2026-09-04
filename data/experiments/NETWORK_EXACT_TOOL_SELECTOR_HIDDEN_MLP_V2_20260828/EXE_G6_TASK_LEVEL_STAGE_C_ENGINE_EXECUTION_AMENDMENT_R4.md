# EXE-G6 task-level Stage C 引擎执行冻结补充 R4

登记时间：2026-08-30；R3 的 G3/G6 dedicated recovery72 已完成，multi-profile 服务在
ready 之前失败。失败服务没有接受任何模型请求，产品 18070 始终健康，RWKV raw 未被修改。

根因是 R2 使用了来自另一 vllm-rwkv revision 的完整 `rwkv.py` overlay。它除 state-profile
能力外还把固定引擎的 native sampler 改成了强制 rapid sampler，因而在
`VLLM_USE_RAPID_SAMPLER=0` 下启动失败。不能通过开启 rapid sampler 绕过，因为那会改变采样
路径，使 dedicated 与 multi 的 raw equality 失去意义。

失败准备与执行结果分别可恢复归档为：

- `invalid_generated_artifacts/run_exe_g6_task_level_stage_c_preparation_incompatible_full_overlay_20260830`；
- `invalid_generated_artifacts/run_exe_g6_task_level_stage_c_engine_full_overlay_rapid_sampler_startup_failure_20260830`。

归档中保留 G3/G6 dedicated 的全部 raw、derived、service evidence 和日志。multi 服务日志
SHA-256 为 `7826ba4ffe6a6c1773691387a6d9f56c768a78f61936220c4266d2090618a155`；
multi-profile inference call 为 0。

R4 从固定远端引擎原文件
`rwkv.py@24dc28626ee34b2e93231b67a72dce9c20ac765ede5194c053b39d743ac47c3a`
派生最小 overlay，只增加内容寻址 manifest、逐请求 profile 校验与 state row 初始化、隔离身份；
原 native `custom_sampler` 保持不变。未覆盖原 `envs.py` 和原 `test_rwkv7.py`。独立远端副本的
13 组失败关闭/隔离测试通过，证据为
`run_exe_g6_task_level_minimal_overlay_smoke/RESULT.json`，SHA-256
`fed7a2201fff1d652d4aabbeb63efe37bac5fbef0b6b6c97302a2cbd006c4c80`。

R4 冻结身份：

- minimal `rwkv.py`：`temp/vllm_rwkv_g6_task_level_minimal_overlay_20260830/rwkv.py`，
  SHA-256 `bef729ec3340f23c2370b503835fddb669f573804eb55ad2202303a31feef350`；
- standalone validator：`temp/validate_remote_vllm_rwkv_profiles_without_pytest_20260830.py`，
  SHA-256 `281a516659c11ad3b0cc1d2e93da6258f72e5a3ee7234f33b0ddce526476baa5`；
- preparation：`temp/prepare_exe_g6_task_level_stage_c_remote_20260830.py`，
  SHA-256 `10673e1a10b963b0df9ea09118a7375a53d0c26a3cbbd17c1773c5e9af20049b`；
- multi-profile launcher：`scripts/run_remote_exe_g6_task_level_multi_profile_vllm.sh`，
  SHA-256 `39a10a468a52af2980a2355caca218b0196247e6c2ddebd82ddc59bc8d62074d`；
- engine runner：`temp/run_exe_g6_task_level_stage_c_engine_ablation_20260830.py`，
  SHA-256 `b0c70d4f2372ae2561da043fd999098b119880675c9d60b5b32805486064bfa8`。

G3/G6 profile、数据、顺序、GPU0、18075、零 stage switch、raw equality、延迟测量和全部门槛
保持原预登记不变。R4 之后才允许重新准备引擎和发起下一次 multi-profile 推理。
