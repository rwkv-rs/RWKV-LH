# EXE-G3 R6 Add+LayerNorm 指纹 R2 预登记

登记日期：2026-08-30（Asia/Shanghai）。R1 结果
`run_exe_g3_r6_prefill_addln_fingerprint_diagnostic/DIAGNOSTIC_RESULT.json` SHA-256 为
`acbea9c9adee3e8c26df1c5431e5c0114cf85abec7197fc0c53b02c3115728de`，因 8×121 个预期
Add+LayerNorm 事件实际为 0 而按原门槛正确标记 `diagnostic_failed`。请求、raw、layer trace、传输与
正式服务均完整；该无效结果保留且不用于根因结论。

R1 的观测缺陷发生在 wrapper 读取 `runpy.run_path` 返回字典，而被包装函数更新的是其
`__globals__` 活跃上下文。R2 只修正为从 `traced_forward.__globals__` 读取同一 live `active`；
不改数据、请求数、指纹字段、评价顺序或阈值。安装事件额外证明 `live_globals_shared=true`。

R2 仍固定同一 G3 state、物理 GPU0、1328-token 目标、temperature=0、logprobs=5、
concurrency=1、attempt=1、8 次请求；每次必须有 121 个 add_ln、61 个 TMix、61 个 CMix 和一个
complete 事件。按 ordinal 0..120、input x→input residual→output x→output normalized 查第一个
变化字段。wrapper SHA-256 固定为
`4bdf9bde009a3121498366873f93a17c66397793f1f6b689664a9389af3d62ed`，启动器 SHA-256 为
`f7067921e4e8444aec7a3e442cef75c1939093eb2e8cab7ff68a0d503a1febd4`，冻结 layer-wrapper
SHA-256 仍为 `74a1dbc0b6548b62087fac04032401ac552d39a3ebdac38fa496c5b4bc75ecb6`。

仍只做定位，不改变 R6/R7 门槛；所有原始 response/text/token/logprobs append-only fsync，
不得修改、删除、隐藏、重排或诱导 RWKV 输出。
