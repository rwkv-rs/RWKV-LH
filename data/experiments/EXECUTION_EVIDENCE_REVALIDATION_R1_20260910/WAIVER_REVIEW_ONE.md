# 独立 AI reviewer one 技术复核

日期：2026-09-10。身份：AI reviewer one（/root/waiver_review_one），依据 owner 本轮明确授权，不代表人工签名。独立完成，未与另一 reviewer 交流。未修改生产代码、waiver 或旧 trace，未读取 holdout/acceptance。

Agent 级：本复核没有新增 Agent 运行；历史 12+3 题 Strict 0/15、completed 0/15、mutation 3，终止包含无进展、工具/参数拒绝、协议错误及 Native 未确认。角色级：本复核未新增角色样本或训练，optimizer steps 未发生。

## 决定

**当前 DRAFT 原文不予 accept（证据不足且 rationale 有事实错误）。** 六文件 SHA pin 均正确；这证明版本身份，不证明执行证据或训练标签等价。允许继续做范围收窄后的等价审计，不能把本报告当 accept 签名。

尤其，统一 rationale 声称“无 prompt builder contract 变化”，但 harness 的 check_command description 已修改；生产重建在 `rwkv_lh/role_trace_inputs.py:288` 取当前工具定义，紧接着核对 definition_digest。旧 check_command Executor disclosure 在这里应拒绝，即使 waiver 放行粗粒度源码 SHA。此防线有效，但也说明“全部旧 trace 恢复准入”不能由六个 SHA 对和代码单测推出。

## 逐文件判断

| 文件 | 冻结/当前 pin | 结论与依据 |
| --- | --- | --- |
| rwkv_lh/harness.py | 两端通过 | 不接受无条件等价。除命令入口的 Python shebang、native executable 与 PATH 修复外，check_command 描述和执行持久性均变化；check 的写入从保留变为丢弃，超时从丢失部分输出变为保留 output/command_streams。旧成功检查不自动证明当前检查语义下的观察或后续 workspace 等价。 |
| rwkv_lh/stateful_goal_loop.py | 两端通过 | 不接受无条件等价。_step_execution_evidence 从 successful_actions 改 assigned_actions，_run_command_write_scope_gaps 删除失败早退；旧失败命令越界现在会产生 scope gap，影响缺口/完成证据及后续角色输入。需逐实际动作核对影响范围。 |
| rwkv_lh/supervisor_openai.py | 两端通过 | 对已有完整成功角色边界的历史输入可有条件兼容；并非未来运行行为等价。review/directive 预算 1400/1200→2800/2400、length 重试和 SSE 尾帧接受范围变化，会改变产生哪些 Planner 结果；不能把新代码性能与旧臂直接比较。删去的两个辅助函数不影响可见调用路径。 |
| rwkv_lh/runtime/openai_compat.py | 两端通过 | 对身份完整、已返回的旧 generation 有条件兼容：原 token、request digest 和 State checkpoint 仍须验证。新重试/404恢复不补全旧未确认请求，不可从当前恢复逻辑倒推旧请求从未执行；未知请求不得当训练样本。 |
| rwkv_lh/runtime/protocol.py | 两端通过 | 接受作为粗粒度源码身份豁免候选：只增加 RWKVRequestNotRecorded 异常类型，无角色 schema 或 token 变更。但异常文档中的“永未执行”不能代替旧请求事实核验。 |
| rwkv_lh/runtime/settings.py | 两端通过 | 对历史已完成 generation 的原设置记录有条件兼容；新增重发预算不修改旧模型输出。对新运行则是传输预算变更，必须登记。 |

## 证据与全局影响

本地 `git diff e7c455b6 -- <六文件>` 审阅各变更；使用 `git show e7c455b6:<path>` 的原始字节计算 SHA，与草案六 frozen SHA 全匹配；当前磁盘六 current SHA 全匹配。SHA 核验脚本位于 `temp/waiver_review_one_sha_20260910.py`，仅为分析，不是生产依赖。

`data/experiments/EXECUTION_EVIDENCE_REPAIR_R1_20260910/PROBES.json` 自己提供语义非等价反例：check 写入后 unexpected_file_exists=false；旧基线为 true。失败 run_command 旧 scope gap 空、现在非空；超时恢复 PARTIAL_DIAGNOSTIC_READY。这些是正确修复，也正是无法用“角色协议未改”替代标签语义复核的原因。

`rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py:453` 的 _successful_progress 使用旧 action.status/result 和观察/修改根判定；_action_authority 使用它生成 executed_fixture 权威。当前 byte rebuild 能证明“当前 builder 对旧冻结事实渲染相同”，但不重新运行历史 shell、不恢复旧丢失输出、不证明旧 check 没有污染后续 workspace。因此即使 Selector 样本 byte rebuild 通过，仍需证据确认其标签权威和所依赖历史动作未受三种语义变化影响。上游 Harness→Controller evidence→Selector/Executor→Auditor 的影响不能只检查目标角色协议 SHA。

waiver schema 仅绑定文件 SHA 对和 reviewer 字符串，未绑定 source_run_id、role 或样本白名单。当前共享统一 rationale 不足以表达有条件准入范围。粗 SHA 豁免本身不取消其余防线，但不能把其余防线夸大为对所有执行语义的证明。

## 可继续路径与局限

维持 draft；对固定 15 来源逐动作列出 check_command 写入、run_command 失败及越界、超时、未确认 Native 请求，沿 causal boundary 标出受影响角色样本。限定 Selector 的首次数据审计可保留独立复核劳动，但要把通过边界重建、标签依据和语义影响审计同时登记，排除受影响样本并如实报告数量，不改旧成绩或旧 trace。取得上述事实后可另发范围明确的新审阅材料。

本复核为六文件代码/防线/现有对照探针审计；尚未逐一重建 15 来源的全部 checkpoint，未声称具体多少样本不可用。没有发现证据足以证明“全部旧标签失效”，也没有证据足以批准当前全量统一等价声明。

验证：`.venv/bin/python -m pytest -q tests/test_role_trace_dataset_integration.py -k waiver` → **4 passed, 42 deselected，8.84s**。这是 waiver 约束专项测试，不是完整回归或旧 15 来源再抽取。
