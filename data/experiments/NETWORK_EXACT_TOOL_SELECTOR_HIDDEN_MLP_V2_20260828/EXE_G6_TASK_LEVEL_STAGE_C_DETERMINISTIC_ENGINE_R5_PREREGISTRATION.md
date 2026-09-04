# EXE-G6 task-level Stage C 确定性引擎复验 R5 预登记

登记时间：2026-08-30。登记时 18075 空闲、产品 18070 健康；R5 尚未启动服务或发起推理。

## 前置结论

R4 的 `ENGINE_ABLATION_RESULT.json` SHA-256 为
`eb72ab75b420d2fab4b794d23bc3e70490ddaa7dce33e9b226055d50f1495b69`，状态必须保持
`engine_gate_failed`，不得回写或解释为通过。只读诊断
`GATE_FAILURE_DIAGNOSIS.json` SHA-256 为
`916f2cdea971f6de12033129b89ce1af1ec681050b5660d841fb1898f9ba34f2`，确认：

1. v1 evaluator 将随 profile 改变的 `request_id` 与 `vllm_xargs` 纳入“基础请求相同”判断，
   因而两种顺序都必然为 false；删除 transport identity 后，两种顺序各 72/72 相同。
2. temperature=0.1、seed=1067 的 native sampler 本身不是 bit-exact：两次独立 G3 dedicated
   为 71/72，同一 multi 服务反向重复也为 71/72；G6 均为 72/72。差异只出现在长前缀后的
   最后一个 EOS/继续 token，但 v1 门禁仍必须失败。
3. G3 与 G6 的 canonical pass/fail 在 dedicated 和两个 multi 顺序中均为 72/72 相同。

## R5 唯一目的

R5 只验证引擎的 state 装载、隔离与请求级切换是否与 dedicated 进程严格等价。质量仍在之后用
生产 temperature=0.1 单独评估；R5 不以 greedy 输出替代生产质量指标。

## 固定协议

- 数据仍为
  `rwkv_lh_executor_network_recovery_g6_eval_v2/stage_sft.dev.eval.jsonl`，SHA-256
  `f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee`；只使用冻结的
  72 条 `protocol_rejection_recovery`。
- profile 固定为 G3 step2000
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12` 与 G6 step1500
  `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`。
- 固定四组：G3 dedicated 72、G6 dedicated 72、同一 multi 服务 G3→G6 144、同一服务
  G6→G3 144；并发为 1，每请求一次，无隐藏重试，无修复或后处理。
- 仅将 temperature 从生产值 0.1 固定为 0.0，以消除随机 sampler 对引擎身份比较的干扰。
  其余 top-p、top-k、penalty、stop、max_tokens、seed、prompt 和数据顺序保持 v1 不变。
- 请求语义 digest 使用 canonical JSON，并且只排除 transport identity 字段 `model`、
  `request_id`、`vllm_xargs`；其余字段任何差异均失败。该算法在 R5 推理前冻结，不得运行后修改。
- 仍使用物理 GPU0、远端 18075、原生 sampler、同一最小 overlay 与 manifest；不启用 rapid
  sampler，不修改 state、模型权重或 RWKV raw 输出。

冻结 evaluator：
`temp/evaluate_executor_multi_profile_recovery72_deterministic_v2_20260830.py`，SHA-256
`4b2ed1bfa6c4e693241ea36e1a48e06a39948cc76d77405af4d8f3dd2b281006`。

## 固定门禁

以下全部通过才允许进入生产温度质量消融：

1. 17 项 task/profile fail-closed 测试通过，显式 zero/G3/G6 profile 请求成功；
2. 两个 multi 顺序的请求语义 digest 均为 72/72 相同，任务内 profile switch 为 0；
3. 对每个 profile，dedicated、G3→G6、G6→G3 的 raw text、raw token IDs、finish reason、
   canonical pass/fail 必须逐条 72/72 全等；不接受 71/72；
4. 所有 raw/derived/request/response 哈希链有效，raw 在解析前保存且未修改或删除；
5. multi 相对 dedicated 的 warm p50 不超过 1.25 倍、p95 不超过 1.35 倍；
6. 物理 GPU0 身份不变，实验结束后 18075 空闲且产品 18070 健康。

任何一项失败即 `deterministic_engine_gate_failed`，不得降低门槛或激活本地配置。
