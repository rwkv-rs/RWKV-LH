# Execute 覆盖采集：预注册方案（2026-09-11，方案文档，未执行）

目标：取得 Selector 训练候选缺失的 **execute 覆盖**（当前 0，候选 INVALID 的唯一实质原因）——即"计划 execute 阶段步骤上，模型选择并成功执行 check_command/run_command"的真实边界。两个单变量轮次，A 先行，A 不达标再启 B；C 方向（改 Step Auditor 协议）**本方案排除**。

## 已核实的事实前提（证据均已封存）

1. Selector 菜单不缺命令工具：COMMAND_PATH_COLLECTION_R1 的 43 行菜单全部解码验证含 check_command/run_command（三种轮换顺序）。失败是模型选择行为，不是菜单/门控。
2. 既有任务文本已隐含要求测试（如 RP-CLI-01 "Deliver … tests"），模型仍 13 动作零命令——**单纯重复既有措辞不够**，任务设计必须让"跑命令"成为最短进展路径。
3. 标签权威机制（代码核实）：
   - `executed_fixture`：动作真实 SUCCEEDED 且推进 missing root（role_trace_dataset_v1.py `_successful_progress`）——依赖模型自发选对。
   - `planner_contract`：`rebuilt["eligible_operations"] == [operation]`（:785-786）；eligible 来自计划步骤 `step.allowed_operations` 经 phase/roots 投影（role_trace_inputs.py:195-203）——**Planner 把某 execute 步骤的 allowed_operations 收窄到单一命令操作时，标签不依赖 Selector 自发选择**。
4. Planner 是强模型（deepseek-v4-pro），其计划行为由 supervisor 提示词模板引导；模板在 supervisor_openai.py（SOURCE_CODE_PATHS 内、**可 waiver**，非角色协议）。
5. 红线：不按题特判、不合成角色场景、不改评分；角色协议模块 NON_WAIVABLE（这就是排除 C 的原因：改 auditor_step 协议会使全部历史 trace 永久报废且无豁免通道）。

## 轮次 A：EXECUTE_COVERAGE_COLLECTION_R2（任务集设计，零源码改动）

**单变量**：采集任务集。不改 rwkv_lh/ 任何文件（零 waiver 影响、零 SHA 报废）。

**任务设计原则**（新增 2 个开发任务 + 复用 RP-CLI-01、RP-WEB-02）：
- 新任务是真实开发需求，不是为凑样本合成的角色场景：例如"修复这个小项目中一个已知失败的测试"——工作区预置完整可运行的小项目（含 `tests/` 与一个真实失败的断言），README 验收物明确包含"`python -m pytest` 的实际运行输出（退出码 0）写入 `TEST_REPORT.md`"。
- 关键机制：**让命令成为最短进展路径**。预置项目已可运行（无需先写大量代码），第一个有信息量的动作就是跑测试看哪个失败；写文件类操作反而无法推进"失败测试定位"这一 read root。
- 与既有失败对照：旧任务先要求实现（写文件是最短路径，模型写完就重复写）；新任务反转顺序——先诊断（必须跑命令）后修复。
- 任务与 acceptance 由 owner 定稿并走既有 register 流程；禁止在 acceptance 里读取隐藏验收实现。

**预注册参数**（沿用 COMMAND_PATH_COLLECTION_R1 格式）：production_commit=162e60ee（或届时 HEAD）、executor_max_output_tokens=1800（不与预算变量混合）、no_forced_commands=true、no_budget_treatment=true、max_transitions=200、native_transport_resume_attempts=1、per_case_wall 1800s、optimizer_steps=0。

**KEEP 判据**（采集轮不做能力宣告）：
- 主判据：`check_command_count + run_command_count ≥ 1` 且至少 1 个成功命令动作绑定到 phase==execute 的步骤；提取后 `coverage.execute ≥ 1`（fresh extraction，无 waiver）。
- 副判据：全部交接核验通过；命令路径的 tmp-overlay / 超时保留输出首次获得真实 Agent 运行验证（`tmp_overlay_live_agent_verified` / `timeout_output_live_agent_verified` 翻 true）。
- NO_KEEP 处置：封存证据，启动轮次 B；不重跑挑好分。

## 轮次 B：PLANNER_EXECUTE_CONTRACT_R1（Planner 模板变量，A 不达标时启动）

**单变量**：supervisor 计划协议提示词模板（supervisor_openai.py 内 plan/patch 模板文本）——要求 Planner 对 execute/验证阶段步骤：
1. 步骤指令显式写明要运行的命令（如 "run `python -m pytest` via check_command and record its output"）；
2. **将该步骤 `allowed_operations` 收窄至 `["check_command"]`（或 `["run_command"]`）**。

**作用机制**（这是 B 的核心价值）：allowed_operations 收窄 → 投影后 `eligible_operations == ["check_command"]` → Selector 边界自动获得 `planner_contract` 权威的 execute 标签——即使 2.9B Selector 从不自发选命令，训练数据也能干净产生。同时菜单收窄本身也直接提高 Executor 实际执行命令的概率（Selector 无其他可选项）。

**约束与代价**：
- 改动仅限提示词模板字符串与（若需要）计划 schema 的 allowed_operations 传递路径；不碰五个角色协议模块。
- supervisor_openai.py 在 SOURCE_CODE_PATHS 内：本轮 KEEP 后需一次等价复核重签（与 statetune_data.py 的待签新 SHA 合并为一次）。
- 风险预注册：Planner 过度收窄导致非命令步骤也被限死 → 判据含"非 execute 步骤的 eligible 多样性不降"（对照历史计划的 allowed_operations 分布）；Planner 补丁语义拒绝率不升。

**KEEP 判据**：coverage.execute ≥ 预注册下限（建议 ≥3 个独立边界）；`planner_contract` 或 `executed_fixture` 权威的 execute 行 ≥1；Strict 不劣化；补丁拒绝率不升。

## 判据之外的既定后续链（两轮任一 KEEP 后）

execute 边界入库 → waiver 重签（一次覆盖：statetune_data.py 新 SHA + 若 B 启动则 supervisor_openai.py 新 SHA）→ 统一重提取 → 新行复核（双 AI 授权流程照用）→ 相似度政策复用（0.95 门槛与聚类规则不变，不重调）→ 密封 `rwkv-lh.statetune-row-selection.v1` 文档 → `freeze_dataset`（已接通 waiver 重放与筛选再现，162e60ee）→ zero-state smoke（optimizer steps > 0）→ 登记首轮 Selector StateTune。

## 明确不做

- 不改 auditor_step / selector_intent 等角色协议（NON_WAIVABLE，全量 trace 报废）。
- 不在采集轮混入预算变量（1800 维持；预算轮已 NO_KEEP 封存，重启需现象复现证据）。
- 不为凑 execute 样本降低 similarity 门槛、修改家族切分或手工构造行（seal_selector_data_gates 的禁令继续有效）。
- 不把采集轮结果表述为能力通过；Strict 仍按原评分。
