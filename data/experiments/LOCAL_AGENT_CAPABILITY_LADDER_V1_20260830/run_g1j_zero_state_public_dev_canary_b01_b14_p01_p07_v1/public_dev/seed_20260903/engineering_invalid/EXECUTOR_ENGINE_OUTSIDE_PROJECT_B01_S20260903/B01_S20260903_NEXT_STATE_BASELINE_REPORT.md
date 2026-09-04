# B01 全 zero State next-state 整改后基线结果

结论：**有效的 zero-State 能力失败基线**。本次没有基础设施故障，Selector parent State、Planner frontier、Harness observation、Auditor gap 和当次工具描述均已进入真实运行；模型仍未从 `list_directory` 转向 `read_file`，随后 Executor 在长 State 上进入重复非法 JSON，最终用尽 240 transitions 且没有生成 `final_answer`。

## 固定结果

- `full_task_success=false`，`status=running`，`agent_completed=false`。
- RWKV 请求 239；Selector 55；真实动作 54；协议拒绝 138。
- Selector operation：`{'list_directory': 55}`；动作 operation：`{'list_directory': 54}`。
- 首次 Selector parent 为空；后续 parent digest 绑定 54/54，绑定率 1.000。
- `GoalFrontierStateV1` 55/55；带 latest action 54；带 audit feedback 54；eligible 工具描述全非空：True。
- completed stage 计数始终为 [0]；最终 completed steps/stages 均为空。
- 54 个动作全部成功执行 `list_directory`，唯一 observation fingerprint 数 4，最大相同 observation 次数 30。
- Step Auditor parse 成功 53，其中内核接受 47、语义拒绝 6；格式无效 1；合法 verdict 全为 repair：`{'repair': 47}`。
- action-scope 协议拒绝 131，全部绑定同一个已消费 selection；没有重新调用 Selector。
- Finalizer 未到达，Final Auditor 未到达，最终输出为空。
- 239 次真实 generation input 的唯一后缀检查：Tool Call JSON 239/239，`Assistant: ```json` 出现 0 次。
- 7/7 workspace file-content 检查通过，未修改文件且无 scope violation；总外部检查 9/10，通过失败项只是没有 Agent `attempt_started`/最终完成。

## 能力边界

当前全 zero State 系统可以：让 Strong Planner 产生合法 S1；让 Selector、Executor、Step Auditor 和 Harness 真实闭环；稳定执行合法目录观察；在多数边界生成合法 repair 审核；跨 55 个 Selector 边界维持可验证 parent WKV。

当前不能：根据清晰的文件列表、四个明确 `read_roots`、Auditor 三个明确缺口以及 `read_file` 描述，把工具意图从目录枚举切换到文件读取；也不能在 54 个动作后的 Executor State 中持续输出合法参数 JSON。因此它尚不具备完成最基础只读调查任务的 Agent 能力，不能进入 7 个 Strong Planner 全流程题的能力比较分母。

## 可复核证据

- 主结果：`public_dev/seed_20260903/B01_S20260903_RESULT.json`
- 完整审计：`public_dev/seed_20260903/cases/PUBLIC-CANARY-B01-S20260903/audit.json`
- 因果账本：`public_dev/seed_20260903/cases/PUBLIC-CANARY-B01-S20260903/causal_ledger.json`
- 本量化：`public_dev/seed_20260903/B01_S20260903_NEXT_STATE_BASELINE_METRICS.json`

本次没有训练、Head 更新或 StateTune；没有改变预注册任务、参数、阈值或外部评价口径。
