# Hybrid v1 / R126 初步改造记录

日期：2026-08-21

性质：结构改造验证；不是能力提升实验，不替代真实 RWKV E2E。

基线源码：`baseline/round126-v19p1` / `50754a2cc1d4b4fcf44d2a93f3888cd070a9c962`

## 预先固定的范围与通过阈值

本轮只验证在没有强模型 API 的条件下，是否建立可审计、可恢复、有调用上限的接入边界。
不修改 R126 的模型采样、工具 schema、Harness 语义、completion 文本或 E2E 评分算法。

固定验证集：恢复后的 R126 全部 107 项测试，加本轮新增 Hybrid 专项测试。通过阈值：

1. R126 原 107 项全部通过；任何失败即回归。
2. Hybrid 专项覆盖计划+PASS、REVISE 后执行、返修上限、规划失败 fail-closed、PASS 边界恢复，
   全部通过。
3. 默认未注入 Supervisor 的现有测试路径不产生 `supervisor_*` 事件。
4. Hybrid 完成文本与 RWKV `final_answer(text)` 字节一致，`controller_rewritten=false`。
5. `max_review_repairs=1` 时最多两次检查、一次返修，第二次 REVISE 必须 interrupted。
6. 全包语法编译通过。

相似度指标：本轮没有生成候选业务输出，因而不伪造文本相似度。结构等价使用既有 R126 测试
逐项通过率，阈值为 107/107；后续能力实验继续使用已登记的 E2E Strict/External 指标与固定
评测脚本，不在运行后改口径。

## 实现摘要

- 从 R132 工作源码建立可恢复 stash，恢复 R126 的 `README.md/benchmarks/rwkv_lh/scripts/tests`
  精确快照；源 manifest 48/48 匹配，恢复后 107/107 测试通过。
- 新增 `rwkv_lh/supervisor.py`：强类型计划、检查、请求与策略契约。
- Controller 仅在显式注入 Supervisor 后启用混合路径；RWKV 保留唯一 Harness 执行权。
- 新增 `supervisor_plan_committed`、`supervisor_review_recorded`、
  `supervisor_call_failed` 因果事件。
- 计划一次提交；检查只能 PASS/REVISE；默认一次返修，硬上限三次；API/协议错误 fail-closed。
- 已落盘计划和检查支持 resume，避免重复模型调用。

## 验证结果

- R126 恢复点：`107 passed in 26.65s`。
- Hybrid 专项最终：`7 passed in 2.19s`。
- 改造后全量最终：`114 passed in 10.53s`（本地固定 TMPDIR，避免 Windows TEMP 捕获文件干扰）。
- `py_compile`：通过。

## 全局影响与风险

上游新增的是可选 SupervisorClient；下游仍是同一 LongHorizonController、ModelSession、
ActionHarness、CausalEvent store。默认路径不实例化 Supervisor。Hybrid 路径会增加一次规划调用
和每个 Final 候选一次检查调用；真实延迟、费用、限流与模型质量尚无 API 数据，不能在本轮
下结论。

下一阶段必须先登记具体 API/provider/model/超时/重试/费用上限，再固定同一 E2E 数据、参数和
评分算法做 R126 vs Hybrid 配对对照。不得用强模型直接执行工具或改写答案来掩盖 RWKV 执行能力。
