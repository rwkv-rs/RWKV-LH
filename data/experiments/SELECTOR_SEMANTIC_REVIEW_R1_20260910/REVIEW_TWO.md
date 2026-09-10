# 独立 AI reviewer two：全部126条Selector语义标签

身份：`AI reviewer /root/waiver_review_two`。Owner明确授权两个独立AI reviewer进行本次语义复核。未阅读另一reviewer决定，未使用私有答案、holdout、后续执行或最终成绩作为标签依据。不是人工签名。

## Agent级与结论

本次没有新Agent评测、mutation、训练或能力改善成绩；历史Strict/completed/终止原因保持原样。本轮只是固定旧来源的语义操作标签审阅。

全部44个前置边界、126个菜单lane均已给出独立决定：**accept_original 46、accept_correction 68、reject 12**。reject保留，不为清空队列制造纠错。此结果还需与另一独立reviewer按精确输入/原输出身份求交；单份意见不构成双review批准，更不构成数据集valid或训练准入。

## 输入身份及覆盖

- MANIFEST.json SHA-256 `8a98d5585045d5acc5abca01f7e2b16fd8c8f25394b4d2cfdc9114c0361443f4`。
- 原126行review_queue.jsonl SHA-256 `e6944b08906ac450ff375a3780bfe6f5188e09b304fbcc25f6076637e8fc8fb5`。
- 逐44包SHA与manifest匹配，逐126行sample/request/input SHA/original output SHA与原JSONL核对，protocol_source逐字段相同；无重复或遗漏sample。
- DECISIONS_TWO.json SHA-256 `7ffbd1c21687f2e75301aa65b6021076fcc3a59122052818f9739dd2801764f2`。

每条决定绑定sample_id、request_id、input_sha256、original_output_record_sha256、packet SHA，并提供操作建议和独立理由。所有行的available_evidence_refs原本为空，因此结果evidence_refs统一为空；不会把feedback中的A000xx或包文件路径冒填成被授权的证据ref。可见依据写在rationale并由原protocol_source/input哈希绑定。

## 判断口径

以当前子任务、明确成功标准、当前可用target类型、已发生参数/结果、feedback与recent_rejections共同判断操作，而非只看eligible或任务成败。机械completed前提不自动证明语义达成；Auditor反馈也不自动是真实缺口。只审Selector操作，不批准Executor参数、Python算法或错误JSON。

- B001/B002/B004/B005共12条reject：server.py宽泛检查目标下，旧文件名/函数pattern搜索0匹配说明策略缺陷，但Selector只返回search_text，没有绑定下一pattern。read_file更直接不等于已证明必须换操作；不能把Executor参数错误硬转成唯一操作纠错，也缺乏足够明确的正例搜索策略。保留此不确定性。
- B003以及B011/B012允许原search_text：目标是功能/API端点或接口/报告规则的内容提取，定向搜索相关词可以合理完成；旧pattern“README”或整句零匹配不是search_text本身必错。原read_file同样直接适用。审批不批准再次使用旧错误pattern。
- B006–B009、B018对全文/全部规格目标选择read_file；B015–B017、B022–B029在发现完成、目录已列且缺正文时纠正list_directory到read_file。不是按文件后缀特判；依据是文本目标、完整内容要求及前置发现/内容差别。
- B013/B014/B019/B020保留原read_file：读取操作与合同相符。last_action成功未截断与Auditor泛化/截断反馈存在冲突，不能依赖有争议反馈给合法读取操作贴负例；也不据此认定重复读取已推进或Auditor正确。
- B030–B035保留write_file：index.html仍缺失且目标要创建HTML，Executor字符串/JSON失败不说明工具选错。
- B036–B044的delete_file行纠正为write_file，原write_file行保留：目标明确生成/覆盖main.py，不要求先删除；write_file支持覆盖。前置未展示execute_shell/write_file的拒绝保留为事实，不把shell作为新的合法替代，也不认定任何现有算法正确。

同一边界的三菜单源上下文相同但lane身份不同；逐行保留input/hash，输出不同的行分别判断。B003/B007/B011/B012/B037/B038等混合输出没有按多数票统一原标签。

## 执行边界

审阅B001–B044完整protocol_source；长重复recent_rejections只按完全相同内容分组显示以便阅读，没有删改原包。具体判断由本reviewer逐边界书写，落盘脚本只是按已写判断展开并核验126行身份及eligible建议，未调用模型/测试/正式extract、未改源码/旧trace/候选或评分。

输出文件只记录本reviewer意见；最终合并必须保留分歧和reject，批准纠错仍须当前生产render_target、token/协议、全量覆盖、既定相似度/固定切分及数据质量门。训练未经这些门通过不得从本报告推导可启动。
