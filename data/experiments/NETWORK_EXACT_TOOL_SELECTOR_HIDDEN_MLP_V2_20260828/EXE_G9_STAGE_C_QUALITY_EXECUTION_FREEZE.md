# EXE-G9 Stage C2：质量消融执行冻结

登记时间：2026-08-30；登记时 G9 仍在 GPU0 训练，尚未运行任何 G9 checkpoint、
Stage B/C 或本文件所述 Full90/live 推理。

## 输入身份

- Stage C 预登记：`EXE_G9_STAGE_C_MINIMAL_STATE_ENGINE_PREREGISTRATION.md`，SHA-256
  `5e5105dbfac93ec6277d3d881b19421215385cac7859137747d4969716f9d9b8`；
- 强 Planner 公开 readiness：`run_exe_g9_supervisor_readiness/SUPERVISOR_READINESS.json`，
  SHA-256 `180ed0da1f926bff7c8200771d38f90ccdb4a60ab646fe9d20a82d034a6cad27`；
- Full90 runner：`scripts/run_rwkv_e2e_benchmark.py`，SHA-256
  `d45ed6bb3aa08578b60661de662838cadb690c51cab6cdc36dd4ff4815009c80`；
- request-delivery integrity validator：
  `temp/validate_current_architecture_e2e_v8_multi_profile_request_20260830.py`，SHA-256
  `2a96c53cfe66ec27d6c43f985292e800a0350308f5cce032cc5fa5e112a46bb0`；
- multi-profile live evaluator：
  `temp/run_current_architecture_live_network_e2e_v5_multi_profile_20260830.py`，SHA-256
  `03a10423a2d70b601595a47a4f16f443c2e1e9fdc30ca563a9cc6390a3a29ee0`；
- Stage C2 runner：`temp/run_exe_g9_stage_c_quality_ablation_20260830.py`，SHA-256
  `82eeb04f072cbf3b2eaece8c41568cb90d7eeff0e0f1849694e71aaf05feb9a3`。

其余冻结身份由 runner 内常量固定：S60 factor/launcher、retrieval9 evaluator、live V1/V2
cases、multi-profile launcher 和 vllm-rwkv overlay。执行时 G9 ablation、checkpoint validation、
Stage B、preparation、Stage C1 五个结果必须分别用显式 SHA-256 传入。

## 固定执行顺序

1. 单次启动隔离 multi-profile Executor（18075、remote physical GPU0），同时保留产品 18070；
2. 单次启动本地 S60 Selector（local physical GPU0）；
3. `A_GENERAL_G3` Full90：G3 request profile、强 Planner/Reviewer
   `openai + contract_graph`、concurrency=4、max transitions=200；
4. `B_UNIVERSAL_G9` Full90：除 request profile 为胜出 G9 外完全同 A；
5. 对 A 的 90 个 immutable RunState 逐 case 执行生产 `retrieval-policy-v1` binding，证明
   `C_DUAL_G3_G9` 的 offline task 精确解析为同一 G3 model/profile/delivery，且已持久化
   main/atom action lane 没有 profile switch；
6. B、C 依次运行 live V1 2 cases、grounded V2 6 cases、retrieval hard gates 9 cases；
7. 对 B/C 每个 live case 的完整 raw Executor text、token IDs、finish reason 序列及结果逐项比较；
8. 停止实验服务、复制 server log，并再次检查 18070。

## C 离线等价说明

原预登记要求 C 的 offline Full90 逐 case 精确复现 A。C 对所有 offline task 的生产路由结果
与 A 完全相同：同一 base、G3 profile、request delivery、prompt、采样、S60、Planner、Harness
和 case 顺序。为避免把同一个 stochastic/provider 工作流重复调用一次再误把波动当 state 效应，
本冻结采用逐 case immutable RunState + production binding 的等价重放，不生成第二份 RWKV 输出。
每一例必须验证 retrieval mode=offline、role=general、G3 ID/SHA、delivery=request、main/atom
checkpoint identity 和 switch=0；C 的 strict/external/completion/首次偏离直接引用 A 的不可变证据。
这项规则在任何 A/B Full90 调用前冻结，不能根据结果改变。

## 固定门槛与选择

- A/B 都必须 90 cases、integrity valid、raw generation 数与 generation input 数相等、
  Planner tool authority/event=0、RWKV raw modification/deletion=0；
- B 的 strict、external、completion 均不得低于 A，且 A strict-pass case 在 B 中零回归，
  才允许选择单个 universal G9；
- 否则仅当 C 的 90/90 task-level 等价证明成立，才允许选择 G3 general + G9 network；
- B/C 都必须 live V1 2/2、grounded V2 6/6、retrieval9 9/9，B/C live 的逐 case outcome
  与完整 raw Executor sequence 必须完全一致；
- Stage C1 全门槛、request delivery、profile switch=0、physical GPU0、产品 18070 保留全部必须成立；
- 任一门槛失败都不激活，不降低门槛、不增加 operation/阶段 state 路由、不修改 RWKV 输出。
