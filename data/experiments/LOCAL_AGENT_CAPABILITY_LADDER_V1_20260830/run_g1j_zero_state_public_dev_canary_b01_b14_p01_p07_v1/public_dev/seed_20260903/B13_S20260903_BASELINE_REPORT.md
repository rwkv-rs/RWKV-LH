# B13 run label 20260903 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 终态为 `running`；消耗 240 transitions；`final_answer` 未通过终止链路。
- 正式轨迹包含 239 次 RWKV 请求和 1 次 Strong 请求。
- 外部黑盒验收 4 项通过 2 项；完整任务未成功。

## State 与工具上下文核验

- Selector 决策 56 次；首轮 parent 为空，后续 55/55 个 parent State 边界连续匹配。
- 56/56 个输入含 `GoalFrontierStateV1`；56/56 个输入含完整候选工具名称和描述。
- 最近动作上下文出现 55 次，最近 Auditor 反馈出现 55 次。

## 行为轨迹

- Selector 操作分布：`{"list_directory":56}`。
- Executor 执行动作 55 次，操作分布 `{"list_directory":55}`，状态分布 `{"failed":4,"succeeded":51}`。
- Executor 协议拒绝 129 次；Step Auditor 协议拒绝 32 次，接受 23/55 条审计记录。
- 计划步骤 `["S1","S2","S3","S4"]`；已完成 `[]`；最终 frontier `["S1"]`。
- 239/239 个 G1J 输入使用冻结的 Tool Call JSON 锚点；`Assistant: ```json` 混合标记 0 次。

## 独立黑盒失败项

- `command_exit`：`{"actual_exit_code":1,"argv":["/opt/verifier-python/bin/python3.13","scripts/verify_integration.py"],"output":"Traceback (most recent call last):\n  File \"/workspace/scripts/verify_integration.py\", line 4, in <module>\n    backend = subprocess.run([\"python\", \"-m\", \"unittest\", \"tests.test_backend\", \"-v\"], capture_output=True, text=True)\n  File \"/opt/verifier-python/lib/python3.13/subprocess.py\", line 554, in run\n    with Popen(*popenargs, **kwargs) as process:\n         ~~~~~^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/verifier-python/lib/python3.13/subprocess.py\", line 1039, in __init__\n    self._execute_child(args, executable, preexec_fn, close_fds,\n    ~~~~~~~~~~~~~~~~~~~^^^...`
- `event_min_count`：`{"actual":0,"event_type":"attempt_started","minimum":1}`

## 归因边界

本例的 next-state 连续性、阶段投影和候选工具描述均按上述计数直接从落盘轨迹复核。若完整任务失败，而这些链路计数完整，则失败记录为冻结的全 zero State Agent 在工具选择、参数生成、反馈利用或协议稳定性上的观测能力边界；不会改写为训练结果，也不会用基础设施无效尝试填入能力分母。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B13_S20260903_RESULT.json`
- `B13_S20260903_BASELINE_METRICS.json`
- `B13_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B13-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B13-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B13-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B13-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B13-S20260903/state_timeline.json.gz`

生成方式：

```bash
/home/chase/GitHub/RWKV-LH/.venv/bin/python /home/chase/GitHub/RWKV-LH/temp/write_g1j_zero_public_case_report_v1.py --case B13 --run-label 20260903
```
