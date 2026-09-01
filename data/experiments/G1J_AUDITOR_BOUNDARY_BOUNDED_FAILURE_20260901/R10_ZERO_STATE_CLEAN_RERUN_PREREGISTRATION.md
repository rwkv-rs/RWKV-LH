# R10 zero-State 干净重跑预登记

日期：2026-09-01。代码、数据、参数、三路 zero profile 和评价口径与 R9 完全相同。启动前额外执行
只读进程 gate：R8/R9 benchmark PID 均不存在，当前仅允许一个 R10 runner；远端仅保留 GPU 0 的
13.3B Executor/Auditor 服务与 GPU 3 的 2.9B Selector 服务。R10 使用新目录，不读取 R8/R9 输出。

R10 的结果按 Planner、Selector、Executor、Auditor、Stage Checker、Evidence Kernel、基础设施和最终
验收分别归因；只有无并发污染的 trace 可以进入后续各角色独立 State Tune 数据候选。
