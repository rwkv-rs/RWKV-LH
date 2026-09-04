# RWKV-LH 单一产品链路清理预注册

日期：2026-09-04（Asia/Shanghai）

## 冻结起点

- 源提交：`3f23a6a6`（已推送到 `chase/rwkv-goal-loop-v2-cleanup`）。
- 固定备份分支：`chase/pre-cleanup-20260904`，同样指向 `3f23a6a6`。
- 起点验证：`821 passed`；Python 3.13 下 1 个既有 `multiprocessing.fork` 警告。
- 本轮不训练、不生成、不加载、不选择任何 StateTune，也不修改模型、Head、冻结数据集或评价阈值。

## 第一阶段固定范围

唯一保留的产品链路为：Strong Planner → G1J Selector-Intent → clean-state Executor-Args → Harness → 机械证据门 → Step Auditor → Stage Checker → Finalizer / Final Auditor。

本阶段只删除已经退出该链路、且已有 GitHub 快照可恢复的表面和旁路：

1. 0.4B State Router/Shadow 的 HTTP、训练、评估、投影、Web API、CLI、测试与历史说明；
2. 旧 `web_assets` 副本，只保留正式 `goal_web_assets`；
3. Hybrid Supervisor、Contract Graph、ECRA 候选、State Router 和旧论文快照等历史文档；
4. PyPI 控制台中已退役的 control/state-router 入口。

为当前 Selector 服务保留其仍在使用的本地 vllm-rwkv 加载后端；该后端只提供模型身份、tokenizer 和隐藏状态提取，不提供 State Router 决策。

## 固定验证与判定

- 静态引用检查不得再出现 `state_router.shadow`、旧 Shadow API、旧 `web_assets` 或被删除入口；
- 当前 Goal UI、运行栈、G1J Selector 服务、Executor、机械证据门与恢复路径的相关测试全部通过；
- 完整 `pytest -q`、`compileall`、`git diff --check` 和 wheel 构建全部通过；
- 清理前后当前产品测试的通过率保持 100%，不以删除失败用例的方式掩盖当前链路回归；
- 结果和删除行数写入同目录 `RESULT.md`。
