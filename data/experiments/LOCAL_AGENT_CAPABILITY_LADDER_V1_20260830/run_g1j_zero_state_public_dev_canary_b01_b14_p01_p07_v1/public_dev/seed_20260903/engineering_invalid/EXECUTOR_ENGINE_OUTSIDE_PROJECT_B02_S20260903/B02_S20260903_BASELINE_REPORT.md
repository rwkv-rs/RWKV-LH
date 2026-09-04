# B02 全 zero State 基线结果

结论：**有效的 zero-State 能力失败**。基础设施、Strong Planner、Selector parent WKV、Goal frontier、唯一 prompt 格式和隔离 verifier 均正常；Agent 没有生成要求的 JSON，也没有合法 `final_answer`。

## 固定结果

- 240/240 Goal transitions，`status=running`，`agent_completed=false`。
- 238 次 RWKV 请求，52 次 Selector 决策，51 个真实工具动作，138 次协议拒绝。
- Selector：47 次 `list_directory`、5 次 `move_file`；51/51 个后续 parent digest 全部匹配前一 Selector State。
- Executor：46 次成功 `list_directory`；5 次 `move_file` 中 1 次成功、4 次因源文件已不存在而失败；136 次 action 协议拒绝。
- Step Auditor：51 次解析成功，49 次被控制器接受；1 次 `continue` 完成 S1，48 次 `repair`；2 次 audit 协议/语义拒绝。
- Plan 共 S1-S3，只完成 S1，停在 S2；Finalizer 和 Final Auditor 均未到达。
- 238/238 个 G1J 输入均以 `**Tool Call:**` 的 JSON 续写锚结束；`Assistant: ```json` 出现次数为 0。

## 首次语义偏离

第 4 个动作把 `scripts/verify_markers.py` 移动成 `reports/markers.json`。这不是结构化 JSON 生成：目标文件实际内容是 Python verifier 源码。后续 4 次又尝试相同 move，均因源文件已被移动而失败。Auditor 持续正确指出目标 JSON 未创建/未扫描源文件，但 Selector 最终又固定为 `list_directory`，Executor 在该已消费选择上进入长尾非法 JSON。

这说明 next-state 已真实传递并被审计，但当前 zero-State 组合仍不能把“创建 JSON 报告”的 Goal frontier 稳定映射到 `read_file`/`search_text`、`write_json` 和验证命令序列。

## 外部验收

- `reports/markers.json` JSON 等值检查：失败，文件不是 JSON。
- `python scripts/verify_markers.py`：失败，脚本被错误移动。
- `attempt_started`：失败，Agent 未执行项目验证命令。
- 无 scope violation：通过。
- Agent 进程树关闭：通过。

硬门禁中 schema validity 失败；role boundary、out-of-scope mutation、hidden retry 和 premature completion 均未违规。

量化记录：`B02_S20260903_BASELINE_METRICS.json`。  
运行后文件摘要：`B02_S20260903_WORKSPACE_SHA256.json`。
