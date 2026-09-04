# Agent 能力阶梯 V1 基线 R2 接线修正预注册

登记时间：2026-08-30（Asia/Shanghai），在 R2 任一模型请求前冻结。

R1 编排器在远端 13.3B 与本地 2.9B 完成加载后，把 Selector readiness 请求错误发送到
`/health`；冻结服务实际只公开 `/healthz`。R1 因此没有创建 benchmark output，没有启动 10
例执行，Executor completion POST=0、Selector inference=0、指标=0；随后按既有 finally 完整释放
18075/29621，产品 18070 仍健康。证据在
`run_current_s60_g3_g6_baseline_v1_orchestration/INVALID_PREFLIGHT.json`，SHA-256 为
`d76647eb50ae1bd1caf23ca7d5ab48f69a3ee7fdbce69060e006c7a36ae23ea6`；R1 runner SHA-256 为
`5e742fc56f55df875c8a7b5bf29ca542c6132ce620d221f351efb0464cd28a51`。

R2 唯一逻辑修正是 readiness URL `/health` → `/healthz`，并验证返回的
`runtime_identity` 至少逐字段匹配冻结 S60 identity。为保持不可覆盖审计，R2 使用新的本地
output/orchestration、remote evidence tag 和 server log。任务、acceptance、Planner、Selector、
Executor G3/G6、R7 引擎、GPU0、并发 3、max-transitions 300、顺序、评价算法和阈值全部不变。

R2 必须完整运行冻结 10 例；不得重用 R1 预检作为能力证据，不得修改或删除 RWKV 原始输出。
