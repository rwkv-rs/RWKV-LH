# G3/G6 fallback quality + Agent V1 R2 执行修正预注册

登记时间：2026-08-30（Asia/Shanghai），在 R2 任何模型请求前冻结。

R1 runner SHA-256
`8c141e0acfd5b0e907c041bb4a96ba9388b3e20e1f0a145b15eafa34ba3241ff` 在隔离 Executor 和 Selector
完成健康检查后、进入第一个 Full90 调用前，因为 `safe_phase(label, function, ...)` 的包装器形参
`label` 与下游 `run_full90(..., label=...)` 同名而抛出 TypeError。R1 invalid preflight 记录单独保留；
日志证明 Executor 只有 GET `/v1/models`，RWKV benchmark generation、Selector inference 和指标均为 0，
产品 18070 健康且 18075/29621 已释放。

R2 的唯一代码修正是把包装器第一个形参从 `label` 改名为 `phase_name`。数据、state、引擎、顺序、
采样、Planner、并发、阈值、输出解析和 R1 预注册全部不变。R2 使用新的本地输出目录、remote evidence
tag 和 server log，不覆盖 R1。原 R1 预注册 SHA-256：
`71144275fc65d544a8e3fd81798fa451d9c2b299b633fa364846282142506439`；R1 invalid preflight SHA-256
在 execution freeze 中固定。

R2 仍必须完整执行 Full90、offline routing 证明、live V1/V2、两次 WEB01 与 NET01，并按 R1 的全部
固定门槛判定；不得因为 R1 预检失败改变任何质量口径。
