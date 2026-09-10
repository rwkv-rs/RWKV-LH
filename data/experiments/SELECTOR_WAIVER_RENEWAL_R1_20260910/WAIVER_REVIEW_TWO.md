# 独立 AI reviewer two：Selector来源waiver续签复核

日期：2026-09-10。reviewer身份：`AI reviewer /root/waiver_review_two`。Owner已授权两名独立AI reviewer重新审阅f34e4964、21c0cf45；不是人工签名。没有读取另一reviewer结论、holdout或私有验收答案。

## Agent级与本次范围

本次未运行Agent或模型；不能据waiver续签声称Agent改善。旧来源15题的Strict 0/15、completed 0/15、mutation 3及原终止原因保持历史事实。本次仅审查原14来源、`selector_intent`、恢复既有60候选的源码身份代理；RP-WEB-02继续整源排除，126条标签待复核不由本waiver批准。

## 独立结论

**支持限定历史scope的续签，待具体proposal/registration/wrapper SHA核对后出具签署。** 不是认定所有变化在全程序中“纯观测”等价：observer异常隔离会改变异常传播；atom客户端隔离与close改变连接生命周期和资源行为。限定14来源的已保存Selector输入与标签权威重建路径没有执行这些新增操作；所有来源是stateful_goal v7，非parallel_atoms。完整SHA和当前字节/token复验仍是正式提取的硬门。

## 审阅覆盖

本地Git完整读取 `git diff b3e89de6 21c0cf45 -- rwkv_lh scripts`，包含五个生产文件及一个benchmark runner。逐文件工作树SHA均等于21c0cf45的Git内容；不是只审阅f34e4964或相信“观测层”摘要。

- `rwkv_lh/runtime/openai_compat.py`：新增订阅列表/add_audit_hook，保留原observer并去重，发事件时逐observer复制顶层dict、单独吞异常。POST payload、状态收据查询/重发、request id/digest和State转换代码未变。共享client仍会向全部订阅者广播，不能把“增加订阅”称任意调用方下的身份隔离；本次限定source是已有trace，不重新产生fan-out事件。
- `rwkv_lh/model_session.py`：构造及capabilities前duck-typed订阅；ModelSession._emit与transport fallback hook吞observer异常。失败observer曾可能中断模型调用，新版继续，因而全局控制流并非绝对等价。checkpoint构造、token序列、State append/commit/rollback、预算和transport选择判断未改；Selector历史重建不实例化session或调用capabilities。旧trace缺失的first-error不能凭新observer重建成已知。
- `rwkv_lh/exact_tool_selector/native_network_client.py`：增加可选audit hook、异常隔离_emit，在requests异常或非200分支发selector_transport_error后抛原有typed异常；成功200解析、network input builder、payload、模型State/解码均未改。新错误日志有run/trace/menu id但不补全旧unknown请求；没有改变已经保存的成功Selector lanes。
- `rwkv_lh/product_runtime.py`：仅把Selector hook接入并加model_role=selector_intent归属；不修改角色协议、计划、输入构造、终止和训练State传递。追加audit事件与模型输入是不同路径。
- `rwkv_lh/parallel_atoms.py`：抽出_run_atom_with_model，新增finally best-effort close；model_factory现在在建立store前调用而非之后。是生命周期与异常时资源痕迹变化，不应概括为完全无行为影响。原14来源明确是rwkv-stateful-goal-loop.v7，生产benchmark仅在not stateful_goal且策略parallel_atoms/contract_graph时构造此pool；本scope无此调用路径。
- `scripts/run_rwkv_e2e_benchmark.py`：Native Selector连接audit hook；atom factory为每个atom新建client，替代共享rwkv_client，避免事件重复归属。改变连接身份和池资源，不影响原14已封存stateful_goal输入。runner不在role源码waiver范围，但本报告仍审阅完整diff；不能把其SHA添加为生产scope豁免条目。

新增测试的代码已阅读：session first error、订阅去重/异常隔离、角色隔离、atom客户端独立与close、Selector传输错误。没有运行测试，没有借测试名称断言共享client本身隔离（对应测试正文明确断言其广播）。本任务不代替全套回归。

## 原来源与重建链核对

独立脚本 `temp/selector_waiver_renewal_review_two_identity_20260910.py` 只读原registration和登记工件并计算SHA；未传内部waiver mapping、未运行extract。原14源注册SHA为`0317d262960128fd43884ee7191c69bb15b5e54d645912446618b4c99366f6f7`。14来源全部登记工件（每源SQLite、model trace、event log、timeline、causal ledger、run protocol、source manifest）SHA与原registration一致，architecture全部为`rwkv-stateful-goal-loop.v7`。完整身份清单见 `WAIVER_REVIEW_TWO_IDENTITY.json`，SHA-256 `5ea378686a9a4eee019e3ee967b506f43fe506d4d1fea003c35d8db45f913a10`。

此前本reviewer对同一工件独立全量动作审阅：14源42动作全部成功（36观察、6write_file），run/check皆0，186个Selector lane中60候选与126待标签；唯一五次ELF误执行的check_command均在排除的RP-WEB-02。原工件本轮未变，故没有把新R1/R2评测来源混入或重写历史动作。本轮不重复宣称已经在新源码上完成正式提取。

读取role_trace_inputs.py确认重建从exact durable snapshot出发，Selector路径调用_frontier_facts、goal_frontier_selector_context、build_network_selector_input和角色唯一builder；不初始化模型、不调用观察hook。role_trace_dataset_v1.py的load_source_run/_validate_frozen_scope和extract_source未在此次提交区间改变。Selector分支仍对checkpoint transcript、protocol SHA、network/menu/eligible摘要、zero身份、原始suffix和server token证据核验；_action_authority仍依赖真实成功且推进root或唯一合同，否则待review。新增审计事件不会自动出现在不可改写的旧trace中，不能补救缺失事实。

## 续签边界

新waiver必须覆盖原冻结manifest至当前21c0cf45的**完整精确**文件对；原六文件中runtime/openai_compat当前SHA变化，并新增native_network_client/model_session/parallel_atoms/product_runtime四项，预期共十项。不能把b3e89de6当原frozen内容；须逐条对照原manifest验证。词表与五角色协议不可豁免。

批准文件须绑定同一14源注册SHA、role仅selector_intent、prospective waiver SHA和固定wrapper实际SHA。wrapper不得容许任意新增source/role，须在固定生产CLI前验证两个独立签署。60候选若重提取发生字节、token、目标或边界身份差异，须拒绝并报告，不为“恢复60”而改parser、评分或旧数据。coverage、相似度/切分及训练门保持原预注册要求；126条标签之后单独复核，不在本结论里预先批准。
