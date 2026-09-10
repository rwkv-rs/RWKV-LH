# AI reviewer one：固定 15 来源 Selector 因果影响复核

独立只读复核；不使用草案 waiver 绕过准入，不调用 extract_registration，不发布样本或训练。本文件补充原否决意见；原六文件全量统一 rationale 仍不接受。

Agent 级：无新增成绩，历史 Strict 0/15、completed 0/15、mutation 3。角色级：逐一检查固定 15 来源的 207 个已保存 Selector menu lane，**207/207 当前 builder 输入与历史 checkpoint transcript 逐字节相同**。这不是训练准入验收，也不证明 207 个标签均正确。

## 读取与校验

注册来源为 REALPROJECT_OFFICIAL_COLLECTION_R3_20260910/COMBINED_SOURCE_REGISTRATION.json。逐来源校验 SQLite SHA 等于该注册的 pin，以 mode=ro&immutable=1 打开；使用生产 RunState.from_dict/LongHorizonStore._deserialize 读取 final 和恰好停在 goal_role_input_boundary 的持久 checkpoint，调用生产 rebuild_role_input 重建 Selector，每个 menu 对照原 selector_checkpoint_id 的 transcript。

读取范围仅注册列出的 15 个 Agent SQLite 及两套历史 selector_candidates/candidates.jsonl、review_queue.jsonl；没有读取私有 acceptance 或 holdout。程序输出逐来源动作、边界、prior_actions、request_id、输入 SHA 和比对结果。未执行源码豁免或来源准入；完整 timeline、token、身份与标签权威校验仍留给合法范围内的生产抽取。

## 全部来源结果

| 来源 | lane 数 | run/check 实际动作 |
| --- | ---: | --- |
| ULTRA-Code_00001 | 12 | 0 |
| ULTRA-Code_00002 | 24 | 0 |
| ULTRA-Code_00003 | 3 | 0 |
| RP-API-01 | 12 | 0 |
| RP-API-02 | 15 | 0 |
| RP-MAINT-01 | 9 | 0 |
| RP-MAINT-02 | 24 | 0 |
| RP-CLI-01 | 9 | 0 |
| RP-CLI-02 | 9 | 0 |
| RP-DATA-01 | 15 | 0 |
| RP-DATA-02 | 12 | 0 |
| RP-FULL-01 | 15 | 0 |
| RP-FULL-02 | 6 | 0 |
| RP-WEB-01 | 21 | 0 |
| RP-WEB-02 | 21 | 5 check_command，0 run_command |

每行 lane 全部 byte_equal=true。其余 14 来源动作仅为 read/list/search/write_file；本轮改动的 command 执行、失败 command scope、command 超时路径没有在它们保存的动作中发生。RP-CLI-02 已知 Native 未确认属于未完成请求，本报告只计已持久化返回的 9 lane，不将未知后续模型工作补成样本。

## 唯一命中：RP-WEB-02

A00003–A00007 五次 check_command 全部 FAILED、exit_code=1；原 argv 为 python3 -c 打印版本，旧 resolved_argv 却把 venv/bin/python3 作为 Python 脚本，输出 ELF/SyntaxError: source code cannot contain null bytes。此次 native executable/shebang 修复直接改变该错误的成因。因此它们之后的重复 check_command 是宿主执行错误诱发的失败恢复上下文，不能仅靠 byte_equal 认定与修复后普通工具失败分布等价。

- CE-000005、CE-000024：各 3 lane，共 6 行，先于第一条 check，历史标签为 executed_fixture，分别 list_directory/search_text；可在后续细粒度方案保留。
- CE-000046：3 lane，选择首条 check 前，历史标签 planner_contract。未受过去错误污染，但目标操作的执行语义已有变更，暂不纳入最简范围。
- CE-000059、CE-000072、CE-000085、CE-000098：各 3 lane，共 12 行，prior_actions 已包含 A00003 及后续错误；当前源码作用下不能声称原宿主故障反馈应继续出现。均为 planner_contract 标签，原唯一 eligible 标签不证明反馈分布未改变。

精确 request_id 与 prior_actions 列于同名 JSON，避免用路径/题号作为生产特判。

## 可审阅的收窄方案

现有 v1 waiver 不编码样本白名单。最简安全范围是创建**仅用于14个无command来源、仅selector_intent**的明确新登记（原注册条目原样引用，完整 SHA 固定），将 RP-WEB-02 整源排除在本次来源兼容实验之外。这是训练来源等价审计范围，不改变 15 题 Agent 评测分母，不回写历史评分或采集。规则依据“是否命中修改的执行证据路径”，不是为某道题写生产特判。

按现有候选文件计算，此范围保留 **60 自动候选 + 126 待标签复核 = 186 lane**；原 WEB-02 的 21 自动候选暂不移入本次兼容候选。原复核材料及 207 lane 原始事实不删除，不宣称其全为无效；后续可建立通用边界范围准入后细分复核。

**技术判断：存在可批准的 14 来源 Selector 源码身份兼容范围。** 可接受理由是这些固定来源未经过被修改的 Harness command 行为、Selector 当前输入逐字节可重建、已返回 transport identity 继续执行完整原校验。前提是新材料准确列出注册 SHA、角色、不可扩展到 WEB-02/其他角色的用途，并将 original rationale 改为承认工具执行语义变化、明确范围外不等价。尚未见具体收窄 waiver 和注册 SHA，故本报告不是新 waiver 的签名批准；提交具体材料可完成复审。

跨切分相似度、coverage、标签语义双审、固定回归等后续门不因来源兼容获准而解除。未知 Native 请求不得混入。不得把首个 review 的字节防线局限误写成现已自动解决。

## 产物

- 诊断脚本：temp/waiver_review_one_selector_scope_20260910.py，绝对路径执行。
- 逐来源证据：WAIVER_REVIEW_ONE_SELECTOR_SCOPE.json，包含脚本 SHA、输入注册 SHA 与全部来源 SQLite SHA。
- 历史候选计数脚本：temp/waiver_review_one_candidates_summary_20260910.py。
- 无新测试运行，无模型调用，无旧 trace 写入。

## 对保持 v1 schema 的落地方案意见

接受“新 waiver 的 rationale/evidence_refs 明确限定 14 来源注册 SHA 和 selector_intent，配独立 wrapper 在调用原 CLI 前硬校验 scope+role+SHA”的设计，**无需为此次审计修改生产协议**。但不能仅靠注释限制范围：wrapper 必须 fail-closed 校验精确注册内容 SHA、仅此 14 条原来源身份/工件 SHA、唯一角色 selector_intent、waiver 自身 SHA 与六文件当前 SHA，并固定传递给原 CLI 的实参，禁止额外透传参数覆盖 registration/roles/waiver。输出应为本轮 experiments 诊断目录，保留原始候选与复核劳动。wrapper 和限定 waiver 作为同一冻结审阅单元，不能将文件独立复用于更广范围。

该方案的可批准性限于实际检查上述 wrapper/新 waiver/新注册后；本文是设计层同意而非尚不存在文件的签名。207/207 字节匹配**不代表 token 验证、完整来源准入、标签语义、覆盖/切分或训练验收通过**。
