# R3 启动前中止记录

R3 状态为 **`INVALID_PRE_GENERATION_STARTUP`**：Agent 题目运行数 **0**，Strict / completed / mutation **未测量**，不能写作能力成绩 0/12。模型生成调用数 **0**，没有角色评分、双零噪声带或训练样本。本轮在 A 臂开始前由冻结身份检查中止；B 未启动。

2026-09-07 06:45:38 UTC，`ARM_A_RUN.log` 记录 `execute_arm → verify_frozen → immutable_files` 的 `AssertionError: source, grading, dataset or registration changed`。这发生在 `current_config`、`ARM_A_START_R3.json` 和 `benchmark.main` 之前。A 进程退出码为 1；顺序执行器因缺少 A 完成证据停止，没有拼接或补跑 B。检查时 A/B 的 START、COMPLETION 记录及实际运行目录均不存在；目录中的 `*_SELFTEST*` 是此前作者工具自验，不能计作 Agent 题目运行。

共享工作树中另一项并行开发改变了冻结源码集合。[PRE_GENERATION_ABORT.json](PRE_GENERATION_ABORT.json) 保存发现时的逐文件原 SHA 与观察 SHA：

| 变化 | 文件 |
| --- | --- |
| 内容变化 | `rwkv_lh/role_trace_inputs.py` |
| 内容变化 | `rwkv_lh/stateful_goal_loop.py` |
| 内容变化 | `tests/test_role_trace_inputs.py` |
| 新增 | `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py` |

这是共享执行目录的身份不一致，启动守卫按预注册拒绝执行；没有证据将其归因于模型能力、Planner 协议或推理服务故障。本次只记录变化及其影响，未撤销其他任务的文件，也未审查或验证其未提交代码。R3 原 freeze SHA-256 保持为 `e962c894fbe3e8e50db697b0a90548161d6f117343813513ac370ae8c5284853`；本次收尾核验所有 20 个既有顶层 R3 文件保持原字节。

后续执行已独立登记为 R4：本地隔离工作树 `/home/chase/GitHub/RWKV-LH-zero-baseline-r4`，分支 `chase/zero-baseline-r4`，固定提交 `eb861256c8edf2e3f0361027a68ed0fc35cddcf5`。R4 freeze SHA-256 为 `c2317b13cbc8483a42f1cb1a9b40ef2134cb290f2b93b9c28ff70b0e70d3307b`，A 臂于 **2026-09-07 06:55:08.276669 UTC** 启动，日志已记录 `[1/12] RP-API-01 starting`。上述为只读核对到的启动时证据。执行负责人随后确认：首题收尾时运行器导入全部登记题集，因缺少封存题集模块失败，R4 已停止并标 INVALID；A 仅有 2 条 `runner_error` 记录，Strict / completed / mutation 未知，不能采用占位 0，B 未开始。当前在隔离目录修复通用运行器依赖并准备 R5，重新冻结后两臂从头运行。本次未写入该工作树或其冻结文件。

后续观察运行仍按 owner 授权使用本地 g1j-13.3B 与当前预算，保留已知模型合同、截断与上下文失败的原始结果；强模型恢复后再议。没有为本次收尾重新执行测试、调用模型、重启服务、读取隐藏验收或启动训练。

可复核文件为本目录的 [ARM_A_RUN.log](ARM_A_RUN.log)、[SEQUENCE_RUN.log](SEQUENCE_RUN.log)、[SEQUENCE_STATUS.json](SEQUENCE_STATUS.json)、[CLOSEOUT_INPUT_ATTESTATION.json](CLOSEOUT_INPUT_ATTESTATION.json) 和 [CLOSEOUT_VERIFICATION.json](CLOSEOUT_VERIFICATION.json)。`script_snapshots/*.py.txt` 保存与 R3 freeze 一致的临时运行脚本，以及中止登记和本次收尾脚本的原字节；这些文件不会被生产代码导入。[SHA256SUMS](SHA256SUMS) 覆盖顶层 R3 文件、脚本快照和本次更新的三份原目录文档，排除清单自身；从 `/home/chase/GitHub/RWKV-LH` 运行 `sha256sum -c data/experiments/ZERO_STATE_AGENT_BASELINE_R3_20260907/SHA256SUMS` 可复核。
