# EXE-G3 R6 prefill 终态指纹诊断预登记

登记日期：2026-08-30（Asia/Shanghai）。登记时远端 18070 健康、18075 空闲；本轮尚未启动服务或推理。

## 冻结依据与修正后的问题边界

上一轮三臂结果 `run_exe_g3_r6_prefill_state_cublas_diagnostic/DIAGNOSTIC_RESULT.json`
SHA-256 为 `e3948997f9d6e9ece83618f45b7f55e8b522fa37faf173bd8815875dc68871aa`，72/72
请求、传输、环境和 attestation 均有效，且正式服务保持健康。`sync`、`cublas`、`sync-cublas`
均保留 43/86 token 两种原始输出，故排除 state row 异步初始化和已测试的
`CUBLAS_WORKSPACE_CONFIG=:4096:8`。

对冻结 raw 的只读精确比较又表明：三臂第 0 个生成 token 均固定为 token id 2364；`cublas` 臂该
位置 selected logprob 24/24 完全相等，而从 token index 1 开始 24 次 selected logprob 全部不同。
因此当前不能只归因于 prompt hidden；边界必须在“prefill 写出的 recurrent state”与“首轮 decode”
之间进一步判定。

## 固定诊断

- base model、G3 state `EXE-G3-MULTISTAGE-STEP2000`（SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`）、物理 GPU0、
  `fp32io16`、原 state adapter、native sampler、`--enforce-eager` 全部保持不变；不设置
  `CUBLAS_WORKSPACE_CONFIG`。
- 固定同一 source index 455、sample `EXEG6-25d90fc447d18b7b1bc63d0356ab`、prompt SHA-256
  `006194134f225089cbad9242065c1e3f4f05ca8387c9cd2bff54027b27eae1a2`；服务端实测 prompt
  长度固定为 1328 token。
- temperature=0.0、top_p=1.0、top_k=0、seed=1067、logprobs=5、concurrency=1、attempt=1；
  连续请求 16 次。
- 诊断 wrapper 只在 1328×4096、单请求的 packed-varlen prefill 结束时读取并 SHA-256 指纹：
  prefill 输入 hidden、输出 hidden、v_first、该请求行的全部 shift state、全部 FP32 WKV state、
  elapsed。读取使用精确原始字节，不改写任一 tensor。
- wrapper SHA-256 固定为
  `14ead6e26e8cc8741ce35bc430259e7123022f4c8b05c6cdca8296de40ec823c`；启动器 SHA-256 固定为
  `773c3d616ab5ce939a650b43199639e9bf55873c7a17e6e3abf24d83f83087e1`。

## 固定解释

1. 16 次 input 指纹一致，prefill output/shift/WKV/elapsed 也全部一致，但 token index 1 仍漂移：
   prefill 终态被排除，进入首轮 decode 的逐层指纹。
2. input 一致而 output 或 state 指纹不一致：根因位于 packed-varlen prefill；按第一个不一致类别进入
   layer/substage 指纹，不先修改 decode。
3. prefill 终态一致且本轮 raw/token/logprobs 全部稳定，而此前 eager 仍漂移：终态读取带来的同步改变了
   行为，进入最小 prefill→decode event/synchronize 修复验证。
4. input 本身不一致或指纹事件不足 16：本轮无效，只检查数据/调度/观测链，不作根因结论。

“稳定”仍要求单一 raw、token 和完整 token_logprobs 序列。本轮只定位，不改变 R6/R7 质量门槛，
不产生上线通过。完整 response body、raw text、raw token 与 logprobs 必须 append-only fsync 后再分析；
不得重试、修复、后处理、修改、删除、隐藏、重排或通过提示词诱导 RWKV 原始输出。
