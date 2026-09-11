# Selector 数据管线完整对照与缺陷盘点

范围：只读核对历史代码、当前生产与训练入口、已完成准入重放的七组来源；不恢复旧协议或执行旧生成器，不改已有样本/评分/去重，不启动训练。分析快照截至 SELECTOR_BOUNDARY_EFFECTIVE_BATCH01_20260911；已登记的 boundary batch02 收尾数据不混入本次统计。以下数字不是无偏的全模型错误率。

## 1. Agent 级状态先行

最近完整评测两批分别为 Strict0/12、completed0/12、42动作/mutation1，以及 Strict0/12、completed0/12、58动作/mutation2。第二批11题重复成功动作预算耗尽，1题审计协议拒绝预算耗尽。后续完整评测队列已停止。

定向pilot与首个扩量批是采集，不是Agent验收：原机械记录分别Strict0/3、completed0/3、3动作/mutation0，以及Strict0/12、completed0/12、12动作/mutation0；按预注册Selector边界run_yielded，不视为任务成功。当前没有训练State，没有Agent能力提升结论，optimizer steps=0。

## 2. 旧流程确实存在，而且为什么快已查清

历史文件只能从Git读取，完整commit、路径、SHA见HISTORICAL_CODE_REFERENCES.json。

1. `generate_rwkv_action_state_tuning_round1_2k_v1.py`包含按缺陷构造候选的函数，包括协议错误、重复失败、无进展、观察等；调用已有seed实例化，记录failure_cluster、surface_variant、来源seed。并非每条样本都启动Planner和完整Agent。
2. `generate_rwkv_state_tuning_stage1_selector_v1.py`从已有Round1数据和评测残差读取Selector行，按缺陷配额选择100个semantic_family，每家族要求已有5个变体，精确产生500条train；固定79条dev，检查家族不交叉与prompt无完全重复。这个Stage1脚本本身主要做选样和打包，上游Round1脚本才负责变体构造。
3. 旧`build_exact_tool_selector_dataset_v1.py`是另一条历史trace候选构建器，不能与上述种子生成器混为一个入口。它以任务、阶段目标、阶段角色、进展的语义投影计算相似度；同标签近邻去重，不同标签近邻保留并登记为决策对照。
4. 旧G1J `dataset_contract.py`读取source registry，通过角色renderer和verifier构造输入/目标、校验token与来源家族，再打包。它支持counterfactual父来源与同split约束，但不是无条件从少量样本自动生成任意新场景的模型服务。

前两类Selector入口和旧exact-tool构建器在9abb43ec（2026-09-04）清理；G1J入口在aa8afe97（同日）清理。当前规则明确退役旧合成链。结论是：旧快速路径不是用户记错；新实现并未保留其等价功能。不能因此原样恢复旧JSON协议、旧renderer、旧State或旧来源。

## 3. 当前链每一步的责任和产物

| 环节 | 当前入口 | 输入 → 产物 | 是否产生新语义场景 |
|---|---|---|---|
| 生产采集 | 当前Controller、Planner、Selector；外部有界收集适配器 | 实际任务 → SQLite、事件、快照、model_trace、模型/源码身份 | 实际运行产生边界 |
| 来源登记 | role_trace_dataset_v1.register_case | 冻结工件 → source registration及SHA | 否 |
| 输入重建 | role_trace_inputs / role_trace_context / role_trace_generation | 当时快照、checkpoint、原请求返回 → 唯一builder输入与完整token证明 | 否 |
| 标签准入 | role_trace_dataset_v1.extract_source / _sample | 三菜单原输出、执行事实或review → candidates/review_queue | 否；仅能纠正既有边界答案 |
| 复核 | 独立AI决定及精确绑定附件 | 原输入、原输出、可见证据 → 接受/纠正/拒绝 | 否 |
| 筛选 | 预注册策略应用器、role_trace_selection | 全量候选 → 选中sample IDs、逐组来源重放 | 否 |
| 冻结 | statetune_data.freeze_dataset | 合格候选、密封selection、来源/waiver → train.jsonl、regression.json、manifest | 否 |
| 训练 | 当前StateTune trainer | 输入/目标token → 仅目标角色State | 否 |

当前不缺抽取、核验或训练入口，缺的是当前协议下“缺陷种子 → 受控派生场景 → 验证 → 打包”的正式入口。生成数据、重放来源、筛选成员、训练四件事不应再混称“已启动”。

同一真实边界的3种菜单是生产Selector原有3次求值；它们不是3个独立语义场景。当前外部截停适配器只减少后续角色调用，没有补上离线派生能力。

## 4. 当前可用的缺陷信号

七组已重放来源合计621条准入候选、209个真实边界；272条自动标签、349条双审标签。231条菜单样本的原预测经双审纠正，涉及82个边界；另外87条review拒绝保留。统计涵盖已有split，不意味着这些全部可以用作训练种子。

| 双审确认的原预测 → 纠正目标 | 菜单行数 | 数据方向 |
|---|---:|---|
| search_text → read_file | 142 | 查找匹配行与阅读完整内容的区别 |
| list_directory → read_file | 51 | 目录已经发现以后，应获取文件内容而非继续列目录 |
| delete_file → write_file | 23 | 重写/替换完整文件不等于删除文件 |
| search_text → file_digest | 11 | 要求哈希身份时，文本搜索不提供哈希证据 |
| file_digest → read_file | 4 | 要理解文件内容时，哈希不提供内容证据 |

231条纠正中，216条发生在已有动作之后，180条带语义反馈；其中151条/52边界带反馈且原预测仍等于上一动作的操作。这支持“反馈后的操作切换”作为重点，但不是仅凭feedback存在就断言全部反馈被忽略。该统计的last_action失败计数均0，不能把它包装成覆盖了工具失败、超时、传输错误恢复。

可复核实例：

- RP-CLI-01 / CE-000027：目标理解README约定；已有搜索动作且带缺口反馈，search_text被纠正为read_file。
- RP-MAINT-01 / CE-000025：需要读取迁移合同和实现，目录已经观察过；list_directory被纠正为read_file。
- ULTRA-Code_00001 / CE-000041：目标重写main.py，delete_file被纠正为write_file。
- AGENT-V1-WEB01 / CE-000030：目标包含记录验证器SHA，search_text被纠正为file_digest。
- NEW-DIAG-01 / CE-000004：目标理解README、实现和测试，file_digest被纠正为read_file。

每个实例的精确输入SHA、原输出SHA、角色边界、完整目标、反馈、来源manifest均在DEFECT_INVENTORY.json中。不是按题目名称添加生产特判。

## 5. 筛选正在丢掉主要缺陷信号

当前有效57行（52train/3dev/2confirmation），只有2条纠正样本被保留。训练目标分布：search_text18、list_directory15、write_file15、check_command3、read_file1，file_digest0。621行中的231条纠正最终只保留2条，不能把“候选valid”解读为“已经覆盖主要缺陷、适合首训”。

当前策略对完整input_text做byte5gram cosine0.95并按边界形成传递连通分量；训练分量只留字典序代表，碰到固定评测anchor的分量会排除其训练成员。固定工具菜单、角色描述、JSON键都参与相似度。一个样本与另一个接近，会通过中间样本把更多状态连在一起。

只读诊断：1802条相似关系中901条两端目标不同。一个同任务实例，初次观察目标list_directory与已有进展后的read_file被算为0.9798相似；菜单和角色前缀各2721字节，占该两条输入约48%与56%。这足以证明应审查决策状态差异和类条件处理，但不能仅凭标签不同就断言所有样本都应保留——也可能是标签矛盾或任务本身有多个合理操作。

旧构建器采用语义投影、同标签去重和跨标签对照保留；当前做法与它有实质差异。这里没有修改0.95阈值、重算冻结评分或把被排除样本重新计入有效数。具体关系与SHA见同级SIMILARITY_DIAGNOSIS.json。

## 6. 不能全部归为Selector的问题

- 选择的工具合理，但参数、路径、搜索词、代码错误：归Executor/工程，不把错误参数反推成必须换工具。
- 工具返回success且观察了root，只能证明机械动作；当前_successful_progress的这种证据不保证该操作满足“完整阅读/完整理解”等语义要求。自动标签值得单独审查，但本次不撤销或重写旧批准。
- Auditor没有让工作进入下一阶段，或反馈没有新信息：需区分Selector是否仍有明确更优动作。多种工具都合理时，不能为了单标签强行纠正；双审不一致保留拒绝。
- Planner初始计划错误、Native中断、State/token错位：工程或上游问题，不作为Selector正负标签。
- execute目前仅3个保留菜单行，失败状态覆盖0；不是已掌握命令工具，也不是足够的失败恢复证据。

## 7. 整理结论

优先顺序应改为：盘点缺陷种子和标签 → 修订数据选择/派生设计 → 小规模验证保住决策对照 → 批量生成并验证 → 冻结/训练。继续盲目补到500行不是当前第一优先级。

建议方案见PROPOSAL.zh-CN.md。现有候选、固定5评测anchor、历史规则和成绩保持原样。方案涉及新的派生来源和新选择策略，尚未实现或批准；不把它冒称为当前准入器已有能力。
