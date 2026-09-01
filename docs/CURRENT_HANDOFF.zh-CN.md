# RWKV-LH 当前交接

更新时间：2026-09-01（Asia/Shanghai）

## 当前分支和产品链路

- 分支：`chase/rwkv-goal-loop-v2-cleanup`。
- 产品只接受 `stateful_goal`；旧 `none`、`contract_graph` 和 State Router shadow 不进入产品装配。
- Strong Planner 输出嵌套阶段 `GoalPlanPatch`；Strong Stage Checker 在阶段屏障只做只读 `advance/repair`。
- 2.9B RWKV 对当前步骤做唯一工具选择；13.3B RWKV 只填参数、执行推进和汇报。
- RWKV Auditor 每个边界使用 clean State；默认复用 13.3B 服务，但不继承 Executor State/WKV。
- Harness 与 Causal Ledger 是唯一事实权威。

## 不可破坏的约束

- 只在 WSL `UbuntuRecovered` 执行项目逻辑；临时脚本放 `temp/`，实验记录放 `data/experiments/`。
- 材料在前，唯一当前要求在语义尾；一个 RWKV 调用只有一个角色和一个任务。
- Selector 是工具选择唯一权威；Executor 不做 Top-K 二次选择。
- Planner 不选工具、不填参数、不执行、不审核；Stage Checker 不计划、不执行、不修改事实。
- Audit retry 不进入 Executor State；任何角色间 WKV 都不合并。
- 未完成步骤可 replace/discard；已完成步骤及其 evidence/revision 不可改写。
- 同阶段步骤不能互相依赖，读写根冲突必须拒绝；下一阶段必须等待整个当前阶段完成并通过 Checker。
- 当前运行时仍是一条持久 Executor State，阶段内顺序执行。隔离 State 并发未完成前不得接回旧 Atom Pool。
- 在修正输入、角色、证据投影和 Selector Head 前不做 State Tuning。

## 本轮已完成

- 原生 `GoalPlanPatch` 支持 add/replace/discard，并按 stage -> peer steps 嵌套解析。
- `RollingGoalPlan` 增加真实阶段屏障、跨阶段依赖约束和同阶段读写冲突检查。
- Strong Stage Checker 只输出三字段；review identity、stage、step/evidence 由 Controller 绑定。
- repair feedback 与 Planner patch 建立 durable source link；Planner 暂不可用后恢复时必须先补 repair patch，不能跳到 Final。
- Selector v8 只看当前 frontier；删除产品 Top-K 二次选择。
- Auditor clean State、证据事实投影和 prompt 禁止字段泄露已修复。
- 角色模型配置通过 `.env` 替换；Auditor role 不继承 Executor State profile。
- README 和当前架构文档只描述最新产品链路。

## 当前验证

- 当前 WSL 工作区全量：`771 passed, 1 warning`；核心链定向：`240 passed`。
- 干净提交快照核心链：`240 passed`。
- 干净提交快照全量：`615 passed, 147 failed, 1 warning`；失败来自未跟踪的冻结
  dataset/experiment artifacts，仓库尚非 clean-clone 自包含。
- G1J 13.3B 对当前 Auditor 模板：`2/2`；Executor write 参数例：`1/1`。
- G1J 7.2B 对同一 Auditor 模板：`0/2` 语义通过、`0` 格式错误；不推荐额外驻留。
- G1J 2.9B 旧 v7/S60 dev：S39 accuracy `0.9509918`、macro-F1 `0.9492751`，未过 `0.96` gate；最早错误是 `selected/raw_argmax` 工具分类。
- 同一 S60/V7 dev 配对：G1J 相对 G1I 修复 10、回归 29、共同错误 29，净多 19 个错误；
  这只比较各自匹配 Head 的旧 V7 系统。
- Selector v8 尚无匹配 G1J Head，不能宣称模型质量通过。

## GPU 使用边界

- 只使用服务器 GPU 0 和 3；GPU 1/2 是用户实验，不得触碰。
- 本轮测试时 GPU 0 运行 G1J 13.3B `18230`，GPU 3 运行 G1J 2.9B `18232`。
- 最终复核时 `18230/18232` 均未监听，GPU 0/3 没有本任务计算进程；继续实验前需按同一
  identity 在 0/3 重启。
- 当前唯一可见 VLLM 进程位于 GPU 2，约 17.9 GiB，属于用户实验，未操作。
- 7.2B 对照完成后已停止，不额外常驻。
- 端口和 PID 是临时实验事实，正式运行仍须每次检查 `/v1/models`、capability 和完整 identity。

## 下一实现边界

1. 为同阶段每步建立独立 Executor session/State 和独立 Audit boundary；
2. 通过冲突门的步骤并发，外部副作用和全局写串行；
3. 不合并 WKV，只确定性提交 Harness/Artifact/Evidence 事实；
4. 用 Selector v8 固定数据重抽 G1J 特征并训练匹配 Head；
5. 在上述工程门完成后，用原固定 Agent 数据跑真实 G1J E2E；只有重复模型能力缺口才进入 State Tuning。
6. 为历史 frozen dataset/artifact 建立明确的 Git LFS/DVC/NAS 恢复清单，使 clean clone 全量测试可复现；
   不把缺件测试静默 skip。

详细协议见 [RWKV Stateful Goal Loop v2](RWKV_STATEFUL_GOAL_LOOP_V2.zh-CN.md)，实验结论见 `data/experiments/RWKV_GOAL_LOOP_V2_CLEANUP_20260901/`。
