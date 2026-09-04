# EXE-G6 task-level R6 greedy 顺序分叉诊断预登记

登记时间：2026-08-30；登记时 18075 空闲、18070 健康，本诊断尚未启动服务或推理。

有效的 R6 结果
`run_exe_g6_task_level_stage_c_deterministic_r6_engine_ablation/DETERMINISTIC_ENGINE_ABLATION_RESULT.json`
SHA-256 为 `22f6f1f642ffb8c8667e09cd40379aa58f47b614ce2edec7c22f6d3a90b1d495`。
R6 不能进入质量阶段：G3 raw/token/canonical 为 71/72，G6 为 72/72，其余门禁通过。

唯一分叉入口为冻结数据 source index 455、sample
`EXEG6-25d90fc447d18b7b1bc63d0356ab`。dedicated G3 与 multi G6→G3 产生 86 token；
multi G3→G6 在 token index 42 选择 EOS，产生 43 token。三者请求语义 SHA-256 均为
`1fffa8a98d6ce880c6ce6e4b8a363fdcb62f113937c17f695868bf80076bb57d`。

## 固定诊断设计

仍使用同一 base model、G3/G6 state、最小 multi engine、物理 GPU0、temperature=0.0 和 R6
其余全部 sampling 参数。所有请求 concurrency=1、attempt=1，无重试、修复或后处理，响应 body
与 raw token 在分析前 fsync 保存。

1. 新启 G3 dedicated 服务，连续请求目标 sample 32 次。
2. 新启同一 G3/G6 multi 服务，固定运行 16 个 cycle；每 cycle 顺序严格为：
   - G3 目标 sample（上一请求为前一 cycle 最后的 G3 目标；首 cycle 在服务 ready check 后）；
   - G6 source index 454，再 G3 目标；
   - G6 source index 455，再 G3 目标；
   - G3 source index 454，再 G3 目标。
3. multi 共 112 请求，其中目标 G3 为 64 次；dedicated 与 multi 合计 144 请求。

记录每个条件的全部 raw variant、token count、finish reason、首分叉位置、request/response digest、
前序 profile/source、cycle 与服务身份。固定比较：

- dedicated 32 次是否单一 raw variant；
- multi 中四种前序条件各 16 次是否单一且彼此相同；
- 每种条件与 R6 的 86-token/43-token 两个已知 variant 是否精确匹配；
- 全部请求体、响应体、OpenAI envelope 与 raw hash chain 是否有效。

该诊断不产生上线通过结论，也不改变 R6 门槛。如果分叉与某一前序条件关联，必须排查完整的
row 生命周期、同类 prompt shape 和相关引擎路径；如果同一条件内部也分叉，必须排查数值/内核
确定性。不得以该单样本特判作为最终修复。

## 启动前摘要勘误

首次执行在 `validate_inputs()` 阶段、启动任何服务或推理之前失败。原因是执行程序内手工抄录的
数据集摘要少了字符 `4`；文件本身未发生变化。R6 的四份 `RUN_PROTOCOL.json`、R6 汇总结果与
当前文件一致记录的真实 SHA-256 均为
`f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee`。
本勘误只纠正输入身份，不改变样本、顺序、参数、请求数、分析口径或通过门槛；修正后的执行程序
必须重新计算哈希并重新冻结后才可启动。

第二次启动也在输出目录创建和服务启动之前退出：诊断程序误把 R6 evaluator 的字节摘要、规范化
JSON、单次 HTTP 请求、原始追加写入和 envelope 提取函数当作 Stage-C 服务 helper 的属性。
执行程序现已内置与冻结 R6 evaluator 完全同构的最小记录函数，并经 AST 检查确认剩余的 helper
属性全部存在。此修正只使预登记的 raw-first 记录协议可执行；仍未发出任何推理请求，也未改变实验
设计或评价口径。修正后的程序必须再次计算哈希并重新冻结。
