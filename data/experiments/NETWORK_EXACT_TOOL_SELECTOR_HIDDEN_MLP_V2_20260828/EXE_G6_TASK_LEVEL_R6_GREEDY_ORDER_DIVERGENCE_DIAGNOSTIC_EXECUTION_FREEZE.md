# EXE-G6 task-level R6 greedy 顺序分叉诊断执行冻结

冻结日期：2026-08-30（Asia/Shanghai）。本文件写入时尚未启动本轮服务或推理。

## 冻结输入

- 预登记：`EXE_G6_TASK_LEVEL_R6_GREEDY_ORDER_DIVERGENCE_DIAGNOSTIC_PREREGISTRATION.md`
  - SHA-256：`59c5ad63dfbf73f32f6982c4319380919b7bd266a1cc67f50e5cfedd9c9b4ed8`
- 执行程序：`temp/run_g6_r6_greedy_order_divergence_diagnostic_20260830.py`
  - SHA-256：`1a5f016c39f7b48856d9e5102261caf99387f1a7cf98badc17915ae28ff1e3ee`
- R6 结果：`run_exe_g6_task_level_stage_c_deterministic_r6_engine_ablation/DETERMINISTIC_ENGINE_ABLATION_RESULT.json`
  - SHA-256：`22f6f1f642ffb8c8667e09cd40379aa58f47b614ce2edec7c22f6d3a90b1d495`
- 固定数据集：`data/datasets/rwkv_lh_executor_network_recovery_g6_eval_v2/stage_sft.dev.eval.jsonl`
  - SHA-256：`f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee`
- Stage-C helper：`temp/run_exe_g9_stage_c_engine_ablation_20260830.py`
  - SHA-256：`739df0e1f9743e79da73e9f8a147c3cbf0893a6253cceefae2a27f4d30c2ae96`
- G3 dedicated launcher：`scripts/run_remote_exe_g3_multistage_candidate_vllm.sh`
  - SHA-256：`4b9bc8493b44ee92f1d57e125103bacc5684fc8047a3ee1e3d95fbf0f207e38c`
- G3/G6 multi launcher：`scripts/run_remote_exe_g6_task_level_multi_profile_vllm.sh`
  - SHA-256：`39a10a468a52af2980a2355caca218b0196247e6c2ddebd82ddc59bc8d62074d`

## 启动前状态

- 远端主机：`rwkv-8222`。
- 物理 GPU：GPU0，UUID `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`。
- 产品服务端口 18070 正在监听；实验端口 18075 空闲。
- 本地输出目录、两个远端证据目录和 multi server log 均不存在，执行程序拒绝覆盖。

## 不可变执行约束

- 严格执行预登记的 32 次 dedicated 与 16 cycle multi，共 144 请求。
- sampling 固定为 temperature 0.0、top_p 1.0、top_k 0、seed 1067，其余参数沿用 R6。
- concurrency=1、attempt=1；不重试、不修复、不后处理。
- response body、raw output 与 raw token 必须先 fsync 保存，再进行派生分析。
- 不修改、删除、隐藏、重排或诱导 RWKV 原始输出。
- 本诊断只定位根因，不产生上线通过结论，不调整任何门槛。

## 启动前重新冻结说明

初版执行程序在输入校验阶段因数据集 SHA-256 抄录错误退出；尚未创建输出目录、启动服务或发出
推理请求。真实摘要已由当前文件、R6 四份运行协议和 R6 汇总结果交叉确认。预登记已追加勘误，
执行程序只修正摘要常量及相应预登记摘要；实验设计和评价口径未改变。以上“冻结输入”列出的均为
勘误后的最终身份。

第二次预启动检查又发现执行程序引用了错误 helper 的记录接口，并同样在输出目录创建和服务启动
之前退出。最终程序内置了与 R6 evaluator 同构的最小 raw-first 记录函数；语法检查、冻结输入检查
和 Stage-C helper 属性检查均已通过。预登记保留两次 0-request 失败的完整说明；上方程序及预登记
摘要是第二次修正后的最终身份。
