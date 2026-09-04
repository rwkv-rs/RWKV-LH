# 全 zero State Agent 基线执行状态

更新时间：2026-09-03（Asia/Shanghai）

## 固定协议

- Selector、Executor、Step Auditor、Finalizer、Final Auditor 均使用 zero/unset State；未执行 Head 训练或 StateTune。
- G1J 生成角色只使用 `PromptV1` + `**Tool Call:**` + ` ```json` 续写格式。
- Strong Planner 使用 GPT-5.6；Stage Checker 使用 Claude；请求不发送 temperature、seed 或 reasoning 参数。
- 固定测试母路径为本目录；公开题位于 `public_dev/seed_<run-label>/cases/<task-id>/workspace`，不把路径强调写入用户任务。
- 只有经过 Final Auditor 接受的合法 `final_answer` 才终止 Goal；transition budget 耗尽不伪装完成。

## Next-state 整改与验证

- Goal frontier 已向 Selector 投影当前阶段、已完成阶段、最近动作参数/结果、最近 Auditor gap，以及当前候选工具名称和描述。
- Selector 使用自身独立的持久 parent WKV；不跨角色传递 WKV。
- Executor 协议拒绝后在同一已消费选择上继续，不重新调用 Selector。
- 本地完整回归：812 passed。
- 远端 Selector 服务已同步到项目当前推理引擎并验证 parent continuation：54/54 个后续边界的 parent digest 与前一 Selector state digest 一致。

## 已失效运行

- 原 B01、B02 与未完成的 B04（run label `20260903`）实际连接到工程外旧 Executor vLLM，不能进入能力分母。
- 三者的工作区、数据库、轨迹和汇总均已无损移动到 `public_dev/seed_20260903/engineering_invalid/EXECUTOR_ENGINE_OUTSIDE_PROJECT_*`。
- B03 首次规划请求遇到上游 HTTP 500，已归入 `infrastructure_invalid/B03_ATTEMPT1_UPSTREAM_500_GOAL_PLAN`，也不进入能力分母。
- 此前关于“B01 是有效 zero-State 能力失败”的判断撤销；它只能作为工程诊断材料保留。

详细根因、迁移和归档证据见 `ENGINE_RUNTIME_REBIND_AND_INVALIDATION_20260903.md`。

## 当前有效运行时

- Executor vLLM：`data/runtime/engines/vllm-rwkv-67f0c5996c50`，版本 `0.23.1rc1.dev1942+g67f0c5996`。
- Executor 制品：`data/models/rwkv7-g1j-13.3b-vllm-v1`，manifest SHA-256 `4eff9f7054e52d702c43132855e943a8fce3269e578a0160752363775b3d6647`。
- 加载日志确认模型根目录只识别一个 safetensors 分片（`1/1`）。
- `runtime_acceptance/PROJECT_ENGINE_ZERO_STATE_NATIVE_CHAIN_20260903.json` 已通过 create、append、generate、rollback、commit、export/import、fork 全链路；所有生成非空，未发送 seed。
- 2026-09-03 本地电脑重启后，远端 Executor/Selector transient service 均仍为 `active (running)`；本地 29613/29621 转发已恢复为独立、禁用 SSH multiplex、由 systemd 自动重连的 `rwkv-lh-g1j-zero-public-canary-forward-20260903.service`。重启后 `/v1/capabilities`、`/v1/models` 与 Selector `/healthz` 身份复核通过。

## 当前执行

- B01 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、53 次选择全部为 `list_directory`、52 次成功动作、136 次协议拒绝、无 `final_answer`。
- B01 的 53/53 个 Selector 输入有完整工具描述，52/52 个后续 parent State 连续匹配，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点。
- B02 本轮在第 0 个 RWKV 请求前遇到中转站错误地拒绝已经包含小写 `json` 的 Responses 输入，已归档为 `infrastructure_invalid/B02_ATTEMPT2_RELAY_INCONSISTENT_JSON_GUARD`；不计入能力分母，稍后以同一身份重试。
- B03 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、57 次选择全部为 `list_directory`、56 次成功动作、144 次协议拒绝、无 `final_answer`。
- B03 的 57/57 个 Selector 输入有完整工具描述，56/56 个后续 parent State 连续匹配，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；其 Step Auditor 已明确要求读取 JSON 和验证脚本，但 Selector 仍未从目录枚举转移到读取或修改。
- B04 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、66 次选择全部为 `list_directory`、65 次成功动作、131 次协议拒绝、无 `final_answer`。
- B04 的 66/66 个 Selector 输入有完整工具描述，65/65 个后续 parent State 连续匹配，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；计划四个步骤均未完成，目标 JSON 与校验结果均未改变。
- B05 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、63 次选择全部为 `list_directory`、62 次动作（2 成功、60 失败）、117 次协议拒绝、无 `final_answer`。
- B05 的 63/63 个 Selector 输入有完整工具描述，62/62 个后续 parent State 连续匹配，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；目标代码与测试均未修复。
- B06 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、238 次 RWKV 请求、47 次选择（27 `list_directory`、20 `move_file`）、46 次成功动作、170 次协议拒绝、无 `final_answer`。
- B06 的 47/47 个 Selector 输入有完整工具描述，46/46 个后续 parent State 连续匹配，238/238 个 G1J 输入只使用冻结的 Tool Call JSON 锚点。它完成了 S1 并由 Claude Stage Checker 接受，frontier 推进到 S2；但 20 次移动均为源目标相同的 no-op，未完成实际兼容迁移。
- B07 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、57 次选择全部为 `list_directory`、56 次成功动作、133 次协议拒绝（Executor 127、Step Auditor 6）、无 `final_answer`。
- B07 的 57/57 个 Selector 输入有完整工具描述，56/56 个后续 parent State 连续匹配，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；Auditor 已明确要求读取脚本和订单数据，但 Selector 始终未从目录枚举转移到文件读取，目标输出未创建。
- B08 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、66 次选择全部为 `list_directory`、65 次动作（12 成功、53 失败）、143 次协议拒绝（Executor 109、Step Auditor 34）、无 `final_answer`。
- B08 的 66/66 个 Selector 输入有完整工具描述，65/65 个后续 parent State 连续匹配，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；活动配置未修改，示例与归档配置保持不变，外部验收 8 项通过 5 项。
- B09 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、50 次选择（28 `list_directory`、22 `move_file`）、49 次成功动作、141 次 Executor 协议拒绝、无 `final_answer`。
- B09 的 50/50 个 Selector 输入有完整工具描述，49/49 个后续 parent State 连续匹配，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；22 次移动均为源目标相同的 no-op，构建脚本未修复，外部验收 4 项通过 2 项。
- B10 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、56 次选择全部为 `list_directory`、55 次成功动作、142 次协议拒绝（Executor 129、Step Auditor 13）、无 `final_answer`。
- B10 的 56/56 个 Selector 输入有完整工具描述，55/55 个后续 parent State 连续匹配，55/55 个后续输入包含最近动作结果和 Auditor 反馈，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；Agent 未创建版本审计报告，外部验收 8 项通过 6 项。
- B11、B12 的本轮尝试在第 0 个 RWKV 请求前遇到 Strong Planner HTTP 500，B13 在第 0 个 RWKV 请求前遇到 HTTP 502；三者均归入 `infrastructure_invalid/`，不进入能力分母，并将使用完全相同的冻结身份重试。
- B14 seed label 20260903 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、66 次选择全部为 `list_directory`、65 次成功动作、151 次协议拒绝（Executor 109、Step Auditor 42）、无 `final_answer`。
- B14 的 66/66 个 Selector 输入有完整工具描述，65/65 个后续 parent State 连续匹配，65/65 个后续输入包含最近动作结果和 Auditor 反馈，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；配置、实现、文档均未修改，外部验收 5 项通过 2 项。
- run label 20260902 的 B01 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、51 次选择全部为 `list_directory`、50 次成功动作、143 次协议拒绝（Executor 139、Step Auditor 4）、无 `final_answer`。
- B01 run label 20260902 的 51/51 个 Selector 输入有完整工具描述，50/50 个后续 parent State 连续匹配，50/50 个后续输入包含最近动作结果和 Auditor 反馈，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；工作区保持只读，外部验收 10 项通过 9 项，但最终调查回答不存在。
- run label 20260902 的 B02 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、58 次选择全部为 `list_directory`、57 次动作（29 成功、28 失败）、134 次协议拒绝（Executor 125、Step Auditor 9）、无 `final_answer`。
- B02 run label 20260902 的 58/58 个 Selector 输入有完整工具描述，57/57 个后续 parent State 连续匹配，57/57 个后续输入包含最近动作结果和 Auditor 反馈，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；基线报告已生成，外部验收 5 项通过 2 项。
- run label 20260902 的 B03 已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、51 次选择全部为 `list_directory`、50 次动作（49 成功、1 失败）、182 次协议拒绝（Executor 139、Step Auditor 43）、无 `final_answer`。
- B03 run label 20260902 的 51/51 个 Selector 输入有完整工具描述，50/50 个后续 parent State 连续匹配，50/50 个后续输入包含最近动作结果和 Auditor 反馈，239/239 个 G1J 输入只使用冻结的 Tool Call JSON 锚点；Agent 未修改运行配置，外部验收 6 项通过 3 项。
- run label 20260902 的 B04 首次尝试在本地电脑重启时停于 237/239 个计费 RWKV 请求，尚未生成 `RESULT.json`；完整 case 目录已原样归档为 `seed_20260902/infrastructure_invalid/B04_ATTEMPT1_HOST_REBOOT_AT_237_OF_239`，不进入能力分母，并登记 `CLASSIFICATION.json` 与 SQLite SHA-256。
- B02 seed label 20260903 的有效重试已完成并归类为 `valid_zero_state_capability_failure`：240/240 transitions、239 次 RWKV 请求、51 次选择全部为 `list_directory`、50 次动作（45 成功、5 失败）、152 次协议拒绝（Executor 139、Step Auditor 13）、无 `final_answer`；外部验收 5 项通过 2 项。
- 用户在主基线完成前将三轮重复明确修订为一轮；`BASELINE_REPETITION_AMENDMENT_20260903.md` 固定 seed label 20260903 为唯一正式 B 组轮次。已完成的 seed label 20260902 结果只作补充观察，20260904 不再运行，模型输入、参数、阈值和评价器均不变。
- 单轮 B 组当前已完成并独立评分 11/14，缺失项只有 B11–B13；当前正在运行 B11 seed label 20260903。
- 完整主基线的新正式分母为 21：B01–B14 单轮 14 项，加 P01–P07 各一次 7 项；label 不作为模型请求参数发送。
- P01–P07 在 B 组之后运行，每题使用固定、彼此隔离的空工程目录和独立黑盒验收；不会把工程绝对路径写进 Agent 输入。

## 暂停状态（2026-09-03 23:01，取代上方“当前执行”中的旧进度描述）

- 用户已明确要求停止测试；当前没有基线执行进程。
- 单轮 B01-B14 已全部完成并独立评分，成功 0/14。
- P01-P06 已全部完成并独立评分，成功 0/6；每题均耗尽 240 次转换且没有合法 `final_answer`。
- P07 在 222/240 个转换调用后由操作员中止，未生成正式结果或指标，不能进入能力分母。
- 当前正式完成度为 20/21；本基线尚未达到最终完成条件。
- P 组另有 19 次 Strong Planner `goal_plan` HTTP 500，全部发生在首个 RWKV 请求之前并隔离在 `infrastructure_invalid/`，不计入能力分母。
- 完整阶段性汇总见 `PAUSED_BASELINE_SUMMARY_20260903.md`；P07 中止快照见 `P07_OPERATOR_STOP_RECORD.json`。
