# G1J 最新 trace 全链路审计

日期：2026-09-04（Asia/Shanghai）

## 结论

这次“模型更强、系统性能反而更弱”不是 13.3B 权重整体能力下降，而是上游 Selector 把执行空间几乎锁死，再由跨 action 的 Executor WKV 和无界重试放大。13.3B 只看到 Selector 选中的一个工具 schema，只能填写参数，不能把错误的 `list_directory` 改成真正需要的工具。因此最终只出现两个工具、任务不结束，首先是控制链路问题，不能用 Executor 模型能力解释。

本轮已关闭已证实的工程失控路径，但尚未生成新的、在线同分布的持久轨迹 Head，所以不能把工程回归通过写成模型效果恢复。

## 冻结输入与复核产物

- trace 根目录：`data/experiments/LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_g1j_zero_state_public_dev_canary_b01_b14_p01_p07_v1/`
- 有效 case：B01-B14、P01-P06，共 20 个；P07 是人工停止样本，不进入成功率分母。
- 原始暂停摘要 SHA-256：`23e462202640db1f12c01b5ad8b57d03e7a1dc87ab131a080fb752a2120215e9`
- P07 人工停止记录 SHA-256：`938faab67372cce7f2e542725c450856844022a33127852d3f939d86f14be39d`
- 重放脚本：`temp/analyze_g1j_20260903_full_trace_chain.py`
- 重放脚本 SHA-256：`728822aea2f7362006f582a91d1042f1ceb2ec6e66323c545c8119a75a7328f1`
- 聚合输出：`TRACE_AGGREGATE.json`
- 聚合输出 SHA-256：`4f50122c141d73ba85c9237c4070a05d4df92c2ed9626aaea3f7c3b25f258ceb`
- 生成命令：`/home/chase/GitHub/RWKV-LH/.venv/bin/python /home/chase/GitHub/RWKV-LH/temp/analyze_g1j_20260903_full_trace_chain.py --output /home/chase/GitHub/RWKV-LH/data/experiments/G1J_TRACE_CHAIN_REMEDIATION_V1_20260904/TRACE_AGGREGATE.json`

## 链路事实

1. Strong Planner：20 个有效 case 都写入了计划补丁，说明链路不是在规划入口中断。
2. Selector：1124 次选择只有 `list_directory=1044`、`move_file=80`；另外 23 个 label 从未被选中。20/20 首次选择都是 `list_directory`。第 20 次之后仍有 `list_directory=709`、`move_file=15`，不是合理的短期探索。
3. Executor：1104 个被接受并执行的 action 仍只有 `list_directory=1025`、`move_file=79`。action 协议拒绝 2571 次；最常见原始输出是空围栏 435 次、仅 ` ```json ` 331 次、围栏加 Tool Call 100 次和长串重复 Tool 54 次。
4. Step Auditor：1104 次边界审计中 862 次接受、242 次协议或语义拒绝。静态分类中 160 次缺读取覆盖、14 次缺写入覆盖，合计 174/242（71.9%）本可由 Controller 在调用 Auditor 前确定；旧链路却让 Auditor 在看不到 Action 参数的情况下猜路径覆盖，再由内核事后拒绝。
5. Stage Checker：全体仅触发 1 次 stage review，绝大多数 case 没有走出第一个阶段。
6. Finalizer：0 次调用、0 个 `run_completed`。因此“不结束”的直接原因在 Selector/Executor/Step Auditor 上游循环，不是 Finalizer 提前或错误结束。
7. 运行控制：存在 221 次 `run_yielded`；P07 到 222/240 calls 才由人工停止。同一个 selection 最多积累 167 次 action 拒绝，证明旧实现对同一 handoff 的重试没有跨 controller slice 的硬上限。

## 格式转换与输入 token 复核

- 分析脚本：`temp/analyze_g1j_executor_token_pressure_20260904.py`，SHA-256 `117d941731e8706a605cad3cf9914931e5b409f2d270accb11eebffc6168973b`。
- 输出：`EXECUTOR_TOKEN_PRESSURE.json`，SHA-256 `8cb9d090878e19aeff61c5aec65c9859247ece898cc2ad9583d45e3fccee2176`；60 个输入文件合并 SHA-256 `6155d658e470b4791cc0224538bd59ec63a3bfd7c6bcfbda2ba711fc3a8e17c3`。
- Step Auditor 拒绝分类脚本：`temp/analyze_g1j_step_audit_rejections_20260904.py`，SHA-256 `90e93eee1fc2969597a18a26004a00810ea9d4c3c84233671474ceee575a7933`；输出 `STEP_AUDIT_REJECTIONS.json`，SHA-256 `6fbcfec7fda747fea298a42a677f35827aa306de0fac6f404780af1aa6945342`。
- 格式转换确实启用：3675 次 action generation 中 1178 次发生确定性 normalization；1161 次把 `name+arguments` 转成 `function+params`，另有少量 `function+arguments`、`tool+args`、stringified JSON 等转换。转换不生成工具名或参数语义。
- 旧 Executor 原生累计输入位置为 min 819、p50 144880、p90 233302、max 365629；接受样本 p50 49397，而拒绝样本 p50 178207。围栏错误不是正常短上下文现象，而是在持久 WKV 极度膨胀后集中出现。
- 654 次旧日志所谓“Markdown code fence 未闭合”中，496 次 `finish_reason=stop` 的完整 raw token stream 实际包含闭合围栏；服务返回 `content` 时剥离了作为 stop suffix 的换行与三枚反引号，旧解析器因此把 transport 行为误报成未闭合。只有 158 次 `finish_reason=length` 属于真实长度截断。
- 其中 336 次完整生成其实是闭合但没有 JSON body 的空围栏，仍然不是合法 Action。整改后解析器只在 raw token IDs 证明 stop suffix 存在且 `finish_reason=stop` 时恢复围栏，并把空围栏准确报告为“没有 JSON body”；不会修补真实 length 截断或臆造 JSON。

## 根因证据

### 1. Selector 训练和在线状态不属于同一分布

旧 feature 提取器对 400 行中的每一行都使用同一个 `bootstrap_state`，并丢弃 `_next_state`；它不是持久因果轨迹。旧产物却声明 `persistent_history_replayed=true`。在线服务实际继续传递上一 Selector WKV。更严重的是，训练模板直接写明唯一当前工具，而在线输入是包含当前 Planner step、已执行 Harness 事实、audit feedback 和多个 eligible tool 的 `GoalFrontierStateV1`。

整改：旧提取器如实标记 `independent-bootstrap-rows.v1`；训练入口拒绝从这种 feature 发布新 Head；服务只接受 `rwkv_lh_g1j_selector_intent_head_v2` 且顶层和 portable identity 都声明 `persistent-causal-sequences.v1`。现有旧 Head 会 fail closed，不能继续冒充线上等价。

### 2. Executor 被错误选择剥夺纠正权，且旧 WKV 被持续污染

Selector 选完后只展示一个工具 schema，13.3B 没有重新选择工具的权限。这一边界本身合理，但要求 Selector 必须可靠。旧实现同时把已接受输出、下一工具 schema 和协议失败不断累积到同一个 Executor WKV，旧工具和 Markdown/Tool Call 格式锚点成为越来越强的先验。

整改：每个新的 Selector 决策都从配置的 Executor 角色初始 State 干净启动；历史事实只通过有界、确定性的 Harness 因果投影进入 prompt。同一 selection 的参数修复仍在当前 action 内进行一次，不把新工具选择和参数修复混成一个状态机。

### 3. 拒绝预算原来不是持久运行预算

旧路径能够对已消费的 selection 持续生成新的同工具 retry，而拒绝上限只在一次 controller slice 内生效。worker 又自动续跑，所以失败没有系统级停止条件。

整改：同一 selection 最多一次参数重试；连续 action 协议拒绝按因果记录跨 slice 计数，达到 12 次写入 `run_blocked`。worker 把 `blocked` 当终态，不再自动拉起。只有用户显式恢复时才写入预算重置边界。

### 4. Selector progress 把总量错误地当成增量

旧投影把 run 累计 `protocol_rejection_count` 每轮重新发送给持久 Selector，而协议定义要求相对 parent checkpoint 的 delta，导致失败信号随轮次重复放大。

整改：输入发送 `run_total - parent_total`，checkpoint 元数据再恢复累计总量；对应测试覆盖初始 5、相对 parent 2 的场景。

### 5. Planner 声明被错误当作 Auditor 可证明的完成事实

Planner 的 `read_roots`、`write_roots` 和 `success_evidence` 只是步骤需求。旧链路在每个 Action 后直接调用 Step Auditor，但传给 Auditor 的 evidence record 没有 Action 参数；模型无法可靠知道一次 `read_file/list_directory` 实际覆盖了哪个 root。内核虽能事后否决，却浪费调用并让 repair 信号依赖模型格式。

整改：Controller 新增机械证据门，只用当前 `(step_id, step_revision)` 下真实成功 Action 的精确参数检查 read/write roots。覆盖不全时持久记录 `goal_step_evidence_gap_recorded`，步骤保持未完成，直接把确定性 gap 投影给 Selector，不调用 Auditor。覆盖齐全后才调用 clean-State Auditor 判断自然语言 `success_evidence`；Evidence Kernel 继续作为第二道 fail-closed 校验。Auditor evidence record 同时补入 Action 参数。

### 6. 全局 WKV 与局部步骤状态混淆

旧 Selector checkpoint 跨整个 run 传递，旧步骤、当前步骤和 Final 意图共享同一条 WKV；旧 Executor 重启又默认携带全局最近 12 个 Action。这既放大 token 位置，也不符合 Planner 已拆解步骤的局部因果边界。

整改：全局权威仍是 causal ledger。Selector WKV 改为只在一个 `(step_id, step_revision)` 内持续，换步骤/revision 或进入 Final 时重置；Executor 每个新 action clean start，只投影当前步骤及其明确依赖步骤的 Action 事实。同一步参数 retry 仍只复用一次 handoff。

## 关于 2.9B 工具分类方案

当前冻结 registry 是 25 个 label，不是 26 个：23 个可执行 operation，加 `final_answer` 和 `ABSTAIN`。开始分类 StateTune 前必须先确认用户所说的第 26 个 label；不能在训练和运行协议里各自假设一个不同的类别数。

可用于预注册消融的第一版四类划分如下，但本轮不把它写死进产品代码：

1. 观察/检索（9）：`list_directory`、`search_text`、`read_file`、`read_json`、`file_digest`、`bind_evidence`、`web_search`、`connector_lookup`、`current_time`。
2. 工作区变更（10）：`write_file`、`write_json`、`patch_json`、`replace_text`、`remove_line`、`append_file`、`make_directory`、`copy_file`、`move_file`、`delete_file`。
3. 执行/计算/验证（4）：`check_command`、`run_command`、`calculator`、`date_diff`。
4. 控制（2）：`final_answer`、`ABSTAIN`。

正确实验顺序是：先冻结 25/26 label 协议和四类映射；再用同一真实持久轨迹做“单层 25 类”与“类别选择器 + 类内 Head”的消融；固定数据集、参数、阈值和相似度算法；只有分层方案在选择准确率、轨迹完成率、错误工具率和停止率上同时通过，才让小分类器选择要加载的类内 StateTune。13.3B 继续只负责被选工具的参数填写和执行，不承担补救错误路由的隐藏职责。

## 剩余能力验证门槛

- 重新构建 v2 Selector 训练集：输入必须来自真实或等价生成的连续任务轨迹，逐步继承 `_next_state`，且覆盖 Planner frontier、Harness result、audit feedback、终止与拒绝恢复。
- 重训 Head v2 后先做固定 dev 轨迹选择评估，再重跑同一 Ladder canary。
- 分别评估 ExecutorArgs、AuditorStep、FinalizerAnswer、AuditorFinal 的角色 StateTune；本次 trace 已证明 AuditorStep 也有 242 次失配，不能只修 Selector。
- 在新 canary 产生前，工程状态是“失控路径已关闭、旧 Head 已禁用”，不是“模型能力已恢复”。
