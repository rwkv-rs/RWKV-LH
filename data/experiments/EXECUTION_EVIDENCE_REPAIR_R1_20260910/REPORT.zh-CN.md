# 执行证据与传输修复轮（R1–R4 合并工程修复，2026-09-10）

被审基线：`ca5b2edf`（生产代码 = `2e998537`，ENGINEERING_REMAINING_AUDIT_R1_20260910 确认 E1–E7 全部属实）。本轮为工程修复轮，非基准评分轮：不改角色协议、不改评分、不跑训练（optimizer steps 保持 0）。四个子轮各自单主题，全部通过离线门（compileall 语义由 pytest import 覆盖；全套 pytest 最终 **1447 passed、0 failed**，基线 1432 + 新增 15）。

## R1：trace 兼容准入 —— 双人复核等价豁免映射表

- `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py`：新 schema `rwkv-lh.role-trace-source-equivalence.v1`；`read_equivalence_waiver` 要求恰好两名不同 reviewer、decision=accept、每条目 (path, frozen_sha256, current_sha256) 精确匹配 + rationale + evidence_refs；vocab 与五个角色协议模块**不可豁免**；`_validate_frozen_scope` 仅在 waiver 精确命中时放行并记录 `waived_paths`；CLI `--equivalence-waiver` + `--waiver-sha256` 双 pin；provenance 记录 `equivalence_waiver_sha256` 与 `waived_paths`。
- 安全论证（测试固化）：豁免只放松整树 SHA 这一粗代理；逐角色协议 SHA、checkpoint 字节重建、timeline 重算、token 回放不受影响——篡改 prompt-builder 后即使有 waiver 仍在字节重建处拒绝（test_role_trace_dataset_integration.py 新增 5 测试）。
- 无 waiver 行为与修复前逐字节一致（旧源仍全拒，直至 waiver 双人复核生效）。

## R2：执行约束与失败证据（E1+E2+E3）

- **E1 修复**：`check_command` 合同改为"可写但不保留"——bwrap `--overlay-src <workspace> --tmp-overlay /workspace`（写入落 tmpfs 上层随进程消失），启动时功能探测 overlay 支持，无 overlay 主机走拷贝退路（副本执行后整体丢弃）。metadata 新增 `workspace_ephemeral`/`writes_discarded`。
- **E2 修复**：`_run_command_write_scope_gaps` 删除失败命令 early-return（失败命令的越界写同样污染工作区）；`workspace_changes` 缺失时 fail-closed 返回明确 gap；调用方遍历从 successful_actions 扩为全部 assigned actions。
- **E3 修复**：`subprocess.run` 超时改为捕获 `TimeoutExpired` 并读取其 `.stdout/.stderr`（CPython 在超时前已累积的字节），output 保留部分诊断，metadata 标 `timed_out=True`，`command_streams` 完整。
- 对照探针 `PROBES.json`（真实 bubblewrap 执行，contrast_baseline 指向修复前探针）：`check_command.unexpected_file_exists` **true→false**；失败 run_command 在有观测 delta 时 `scope_gaps` **空→非空**；timeout `partial_stdout_preserved` **false→true**。

## R3：Native 传输可靠性（E4 + 404 语义 + 连接层 + benchmark resume）

- **首错保留**：`_native_request` 在进入恢复前 emit `native_request_transport_error`（含首错类型与消息）；最终异常消息拼接首错，`raise ... from first_error`——收据 404 不再覆盖第一原因（修复 E4）。
- **404 语义化**：服务端 journal 在执行任何工作前 claim（`native_request_recovery.py` `_claim`，新增回归锚测试固化该顺序）⇒ 收据 404 证明请求从未执行。客户端 `state_request_result` 把 404 返回为 `not_recorded`；`recover_native_request` 四态（completed/pending/not_recorded/unknown），not_recorded 经 backoff 二次确认后抛类型化 `RWKVRequestNotRecorded`；`_native_request` 有界重发（新 setting `native_resubmit_attempts`，默认 2，emit `native_request_resubmitted`）。安全性：request_id 内容寻址，迟到首发被 journal 按 id 去重。真 unknown 仍绝不重发 POST。
- **连接层**：`_new_session` 挂 `HTTPAdapter(Retry(connect=2))`（只重试连接建立——请求未发出，永远安全）；Native mutation POST 加 `Connection: close`，消除死 keep-alive 穿端口转发隧道这一 404 实证根因（NATIVE_CREATE_UNKNOWN_AUDIT.json，RP-CLI-02）。
- **benchmark**：`--native-transport-resume-attempts`（默认 1）对 `model_transport_unavailable` 的可恢复中断做有界重入；原中断事件在同一因果库中保持耐久，观测记 `infra_retry`，**不改评分**。

## R4：Planner Supervisor 生成健壮性

- SSE 容忍 finish 后的 usage-only 尾帧（常见网关收尾形态）；finish 后出现文本或改变 finish_reason 仍拒绝。
- `finish_reason==length`（SupervisorGenerationInterrupted）从"从不重试"改为 retry_attempts 内有界同预算重试——资源结果，非协议缺陷；其他非 stop 完成仍不重试。
- thinking 下输出预算提升（预注册变量，非评分阈值）：`max_review_tokens` 1400→2800、`max_directive_tokens` 1200→2400（reasoning token 计入 max_tokens，旧值使 length 成为常态）。

## 死代码清理（本轮触碰文件内）

AST 全仓扫描（`DEAD_CODE_CANDIDATES.json`，1558 个定义中 8 个候选）；删除本轮触碰文件中人工确认无引用的三个：`harness.missing_required_postconditions`、`supervisor_openai._float_env`、`supervisor_openai._bool_env`。其余 5 个候选（atom_execution/controller/vllm_rwkv/statetune_native_runtime）不在本轮触碰文件，留待单独 CLEANUP 轮（vulture 未安装，候选清单由名字出现次数扫描产生，动态调用未证死）。

## E5 持续进程会话（并行设计线，未实施）

设计文档 `PERSISTENT_SESSION_DESIGN.zh-CN.md`；可行性探针 `persistent_session_probe/PROBE.json` 证明 Harness 持有的单个长驻 bwrap 跨交互存活并保留会话内状态。实施另立轮次，不作为 Selector 训练门槛。

## 架构评估（初步，重跑 15 题后需以 ARCHITECTURE_FIT_REVIEW 复核）

无证据要求推翻五角色分工；分工边界清晰正是本审计能把失败精确归因到 Selector/Executor/Auditor/基础设施的原因，且小而固定的角色上下文与 RWKV 定长 State 的 adjacency 原则相容。三个已暴露的流程弱点（不在本轮修改）：① Step Auditor 把"找到一行/成功写入"升级为完成——单点放大器，方向是证据合同收紧；② 无进展缺升级路径（RP-API-01 初始计划后从未再调 Planner）——方向是重复无效动作触发强制重规划/菜单收缩；③ 反馈送达≠生效——方向是反馈改变 State/菜单结构而非仅追加文本。各自应单变量立轮。

## KEEP 状态与遗留门

- 已过门：全套 pytest 1447 绿；R2 三探针对照全部达预期；R3/R4 行为由假服务器单测覆盖（死 socket+404→重发成功、pending→等待、真 unknown→不重发、usage 尾帧容忍、length 有界重试）。
- **未过门（需 owner 执行）**：① 重跑 15 题 Agent 评测（R3/R4 的 KEEP 判据：无首错丢失死链、SupervisorGenerationInterrupted 下降、Strict 不劣化）——需要模型服务器与端口转发在位；② `EQUIVALENCE_WAIVER_DRAFT.json` 双人复核（6 个文件的 frozen/current SHA 已 pin，decision=draft 在复核改为 accept 前会被准入器拒绝）；③ waiver 生效后用 `--equivalence-waiver` 重提取旧 trace 验证 15/15 恢复准入。
