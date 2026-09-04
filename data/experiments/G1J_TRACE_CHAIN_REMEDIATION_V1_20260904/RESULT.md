# G1J trace 全链路工程整改结果

日期：2026-09-04（Asia/Shanghai）

## 判定

工程整改：通过。

模型能力恢复：未判定。旧 G1J Selector Head 已被协议身份拒绝；必须用新的在线同分布持久因果轨迹重训 Head v2，并重跑固定 Ladder 后才能判定选择准确率和任务完成率。

## 输入、用途与生成方式

- 来源/版本：`LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_g1j_zero_state_public_dev_canary_b01_b14_p01_p07_v1`。
- 用途：定位“只选两个工具、循环不结束、模型更强但系统更弱”的完整控制链路根因。
- 有效范围：B01-B14、P01-P06 共 20 个 case；P07 仅作为人工停止和无界续跑证据。
- 原始摘要 SHA-256：`23e462202640db1f12c01b5ad8b57d03e7a1dc87ab131a080fb752a2120215e9`。
- P07 停止记录 SHA-256：`938faab67372cce7f2e542725c450856844022a33127852d3f939d86f14be39d`。
- 聚合方式：使用 `temp/analyze_g1j_20260903_full_trace_chain.py` 静态读取每个 case 的 `event_log.json` 与 `model_trace.json`，不修改原始 trace。
- 聚合脚本 SHA-256：`728822aea2f7362006f582a91d1042f1ceb2ec6e66323c545c8119a75a7328f1`。
- 聚合文件 SHA-256：`4f50122c141d73ba85c9237c4070a05d4df92c2ed9626aaea3f7c3b25f258ceb`。

## 固定事实

- 20/20 case 未成功。
- 1124 次 Selector 选择：`list_directory=1044`、`move_file=80`，其余 23 个 label 为 0；20/20 首次选择均为 `list_directory`。
- 1104 个已执行 action：`list_directory=1025`、`move_file=79`。
- 协议拒绝 2813 次：action 2571、goal audit 242。
- 同一 selection 最多产生 167 次 action 拒绝。
- Step Auditor 运行 1104 次，接受 862、拒绝 242；Stage Checker 仅运行 1 次；Finalizer 0 次；`run_completed=0`。
- 因此 Selector 崩塌是工具单一化的入口，Executor 跨 action 状态污染和无界重试是退化放大器，Auditor 失配阻止阶段推进；Finalizer 不是不结束的根因。

## 已完成整改

1. G1J Head 身份升级为 v2；顶层和 portable identity 必须声明 `persistent-causal-sequences.v1`，旧 Head fail closed。
2. 旧 400 行 feature 提取器如实登记为独立 bootstrap rows；训练入口拒绝将其发布成持久轨迹 Head。
3. 每个新 Selector 决策对应一个干净 Executor action State；只投影有界 Harness 因果事实，不继承上一工具 WKV。
4. 同一 selection 只允许一次参数修复；连续 12 次 action 协议拒绝后持久写入 `run_blocked`，worker 不再自动续跑；显式人工恢复会记录预算重置边界。
5. Selector 拒绝进度改成相对 parent checkpoint 的 delta，checkpoint 元数据保存累计值。
6. 确定性的配置、身份、schema 和架构错误不再由 web worker 无限重试。
7. `blocked` 已贯通状态投影、worker、正式 Goal UI 与兼容 UI；正式 `goal_web_assets` 已加入 package data。
8. 环境示例、运行说明、架构文档、角色 State 配置和模型 SHA 已同步到当前协议。
9. 格式审计确认 normalization 已启用；旧日志 654 次“围栏未闭合”中 496 次是服务剥离 stop suffix 的误分类，158 次才是真实 length 截断。解析器现在只恢复 raw token IDs 可证明的 stop suffix，并单独识别空围栏。
10. Planner 的 read/write roots 只作为需求：Controller 在 Step Auditor 前以成功 Action 的精确参数做机械覆盖门。覆盖不全时不调用 Auditor、不完成步骤，确定性 gap 直接反馈 Selector。
11. Selector WKV 改为 `(step_id, step_revision)` 局部持续，跨步骤/revision/Final 重置；Executor clean start 只接收当前步骤及其明确依赖步骤的 Action 事实。

## 验证结果

- 定向链路测试：116 passed。
- `git diff --check`：通过。
- `/home/chase/GitHub/RWKV-LH/.venv/bin/python -m compileall -q rwkv_lh scripts tests`：通过。
- `/home/chase/GitHub/RWKV-LH/.venv/bin/python -m pytest -q`：821 passed，1 个既有 Python 3.13 `multiprocessing.fork` DeprecationWarning，耗时 106.73 秒。
- `uv build --wheel`：通过；wheel 已核验包含正式 `rwkv_lh/goal_web_assets/{app.js,index.html,styles.css}`。验证产物保存在 `temp/g1j_packaging_validation_20260904/`。
- 原始 trace 静态重放：完成，结果见 `TRACE_AGGREGATE.json` 和 `TRACE_CHAIN_AUDIT.md`。
- Executor token/stop 复核：完成，结果见 `EXECUTOR_TOKEN_PRESSURE.json`。
- Step Auditor 242 次拒绝已全量分类且无未分类项，结果见 `STEP_AUDIT_REJECTIONS.json`：缺读取覆盖 160、缺写入覆盖 14、输出合同 25、repair/complete 冲突 4、引用失败 Action 16、JSON 解析 23。

## 下一实验的硬门槛

当前 registry 实际为 25 个 label（23 operation + `final_answer` + `ABSTAIN`），不是 26。必须先确认第 26 个 label 或把实验协议固定为 25 类，再冻结四类映射。

新的 Selector 数据必须是逐步继承 `_next_state` 的真实/等价连续轨迹，覆盖 Planner frontier、Harness result、audit feedback、停止和协议恢复。之后按同一固定数据集比较：

- 单层 25 类 Head；
- 四类选择器 + 类内 StateTune/Head；
- 各角色 ExecutorArgs、AuditorStep、FinalizerAnswer、AuditorFinal 的零状态与 StateTune 消融。

在固定选择准确率、错误工具率、轨迹完成率、停止率和预登记相似度阈值全部满足前，不进入产品默认配置。
