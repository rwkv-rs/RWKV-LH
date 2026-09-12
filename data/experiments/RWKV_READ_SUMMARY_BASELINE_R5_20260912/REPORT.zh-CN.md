# R5：明确路径读取 → 理解 → 总结，固定组基线

任务级 **0/8 合格**，两遍各0/4；模型以final_answer声明完成8/8，按预注册定义均为未达质量门的完成8/8，mutation=0。终止原因全部final_answer，没有预算中断、无总结终止或错误工具选择。这不是项目级Strict，也不是项目任务完成率。这里“错误完成”包含遗漏导致的不合格，不等于8次都编造或明说“已经测试通过”。固定组稳定门未通过，不升级到搜索或更复杂任务。

组件级：读取调用合法且路径正确8/8；一次返回完整文件8/8；完整观察、exactly-once及正确State延续8/8；总结全部登记要点覆盖0/8。重复读取0、非法参数0，未发现明确曲解；1份回答有一处缺少文件直接支持的模块断言。17组必需事实×2遍中，完整覆盖10/34组，其余含部分覆盖；这不是按字面匹配得到的分数。

| 既有文件/来源 | 字节 | 读取/交接 | 总结合格 | 主要遗漏或风险 |
|---|---:|---|---|---|
| RP-API-01 README.md | 1823 | 2/2 | 0/2 | Python标准库约束、取消释放时段；第二遍还缺时间区间/验证边界 |
| RP-API-02 README.md | 2020 | 2/2 | 0/2 | 首遍省略事务/并发/重启；第二遍改善但仍缺同key异请求冲突、quantity限制、更正重试 |
| RP-API-01 server.py | 935 | 2/2 | 0/2 | 合同未完成、响应头、db仅解析；第二遍额外称使用threading模块 |
| RP-API-01 verify_public.py | 497 | 2/2 | 0/2 | 健康检查范围正确；超时、关闭连接等登记细节未全覆盖 |

## 冻结与运行边界

登记SHA `80dc672e19e1473c707b010e4bd2c70bd69b870b4494b3f7f18b93b1622001ea`，在第一条真实generation之前写入。四个文件均直接复用R4已通过的R5实际workspace；全文分别为619/713/259/130 token，未新建datasets版本、角色训练集或新场景。原文件和workspace全清单保存在REGISTRATION，每个运行使用隔离副本；外部评分事实与source_result没有传入模型workspace或输入。

任务统一为“阅读指定文件 PATH，总结其主要内容。只依据文件中的信息回答，不补充未经文件支持的事实。”唯一生产R4简短read_file说明保留。输入由LongHorizonModel._assignment和model_io生产renderer构建，工具结果由Controller._action_observation_event构建，不另造协议。提供生产完整工具菜单，不使用eligible_operations，不预选参数、不强制read→final顺序。非read工具选择将终止失败而不执行/替换，本次没有触发。

RWKV 13.3B zero，模型SHA `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65`；native_required，每题每遍独立zero根，temperature=0.1、top_p=1、top_k=0，其余采样见登记，未额外设置随机seed，重复运行不承诺逐token一致；每次输出1800，每题最多4次generation，主组最多32次，原读取回归24次，总上限56次，主组墙钟预算3600秒。未增加补救调用或重采样。服务132个project文件及6393个engine文件与已冻结清单一致，无远端Git，实际server/tokenizer build见SERVER_IDENTITY。

主组实际16次generation，完整输入累计67156 token（每次3170–5516），输出3198 token。完整输入计数是各调用full-context之和，不能冒充增量prefill消耗。原始输出token包含服务结束标记，精确保存；没有用估算替代。对应token数组在model_trace.jsonl，输入文本在input_N_token_decoded.txt，输出原文在RESULT和raw_generation。总预算未打满，不能把遗漏归因于输出截断。

## 信息流证据与诊断

执行路线是next_command→真实Harness→append_action_observation→同一next_command→RWKV原样final_answer。没有调用会强制回答的terminal_answer，无Coordinator/Planner/Selector/Final reviewer额外模型。正式completed字段只表示模型提交了final，外部评分另行决定合格；程序不改写回答。

MECHANICAL_AUDIT保存每次generation的父checkpoint、摘要、完整token重建、每个观察的父子关系和唯一注入次数。16/16完整输入token及解码文本匹配，8/8真实file chunk与exact_spans完整一致，8/8下一代直接从观察child生成。四题的两遍根输入相同、zero预填充State摘要相同；后续真实观察的时间戳/证据ID自然变化，未伪称后续上下文逐字一致。State核验是协议身份、父子摘要和实际输入的可复核证据，不是对服务内部数值张量计算的独立证明。

代码审查与实际轨迹没有支持观察遗漏、重复追加、错误父State或读参数缺陷。生成侧已具备本固定组的读后作答闭环，但保留主要约束和摘要覆盖不足；无法从这8条将原因唯一归结为提示词、模型知识或训练。第二遍库存摘要已完整写出事务、并发、持久化，说明这些内容到达且能够被利用；同样输入的root并不保证覆盖率稳定。

`server.py`第二遍说“它使用 Python 标准库的 http.server 和 threading 模块”。文件提供ThreadingHTTPServer，却没有threading模块导入或实现细节，按“仅依据指定文件”记一处无直接依据陈述，不把线程HTTP处理本身误判为错误。其他路径501在GET处理器语境下理解；示例命令不等于宣称实际运行过。逐断言解释、完整事实清单和原句见SEMANTIC_REVIEW。

## 评分限制及下一步

预注册要求所有事实组全部覆盖，其中含Python标准库、5秒超时、close等细节。短摘要可以准确概括主旨而漏掉这些细节；本轮仍按原门记失败，不能临时放宽或把10/34组解释为知识正确率。评审是Codex在模型运行外依据原文件逐项复核，接受不同措辞，并非双人盲审或已验证的自动语义评分器。所有原回答及判断可供owner逐条复核。

因此本轮**不修改生产提示词、State、parser或Harness**。最小下一步是先明确“主要信息”与可省略细节的口径：如果调整，必须另轮预注册并保留本轮0/8，不能重评分冒充收益。若沿用现有严格门，最小候选仅为通用任务说明增加摘要覆盖要求（用途、关键规则/限制、输入输出、未实现/未验证边界），不含外部事实、参考答案或路径特判；在相同四文件、模型、State、预算上新冻结基线和候选再验证，并先建立真实失败样本回归。当前证据不支持修State或扩架构，更不授权自动进入搜索。

## 原读取回归与工程验证

沿用原R1运行器和评分器，R4相同有效7题×3及独立R2缺失补充×3：主组 **21/21**，独立缺失补充 **3/3**。主组工具success 18/21（缺失题正确返回错误亦为诊断通过），补充工具success 0/3。协议错误0、提前final 0。与历史R1 18/21、独立R2 3/3分开报告，保留原无效夹具及失败候选，不把它们合并为收益。是否保持R4读取边界见SUMMARY.gate；即便原读取全通过也不能补偿摘要门失败。

WSL UbuntuRecovered，uv frozen及Chromium环境检查完成，完整 **1514 passed、0 skipped、243.65秒**。原5个未提交文件SHA保持；本轮生产文件零改动。仅在临时离线审计中修正了两项布局假设：短文本在typed exact_spans，不在旧output；原始生成token含已被文本展示剥离的stop围栏。该诊断代码按真实首例完成1 failed→1 passed，初次误标、修前代码、RED/GREEN保留；未改变预注册条件、生产协议/parser/stop或任何模型结果，也没有运行后重采样改善成绩。

## 复核索引

- REGISTRATION.json、SOURCE_MANIFEST.json、SERVER_IDENTITY.json：运行前口径、模型和逐文件源码身份。
- FROZEN_SOURCE.tar.gz：全部运行生产源码、词表及冻结运行器；源码身份SHA `fe1019d529de1ea8324c23c5140c6a257f8198a4cb8b985b21725414f700014c`。
- RESULTS.json、runs/*/RESULT.json、state_snapshot.json、model_trace.jsonl、observation_N.json：原始轨迹和持久化State关系。
- MECHANICAL_AUDIT.json、ROOT_STATE_IDENTITY.json：精确token/观察/根State核验。
- SEMANTIC_REVIEW.json：外部逐要点评分及无依据陈述；不进入模型输入。
- read_regression/RESULTS.json、READ_REGRESSION_CALL_AUDIT.json：原读取独立复测。
- CHAIN_INSPECTION.json、AUDIT_BEFORE.py.txt、PRELIMINARY_AUDIT_LAYOUT_MISMATCH.json、AUDIT_RED.log/AUDIT_GREEN.log、PYTEST_FULL.log：工程分析与测试。
- RAW_EVIDENCE.tar.gz及SHA256SUMS.json：完整原始证据和哈希封存。只做本地提交，由owner负责push。
