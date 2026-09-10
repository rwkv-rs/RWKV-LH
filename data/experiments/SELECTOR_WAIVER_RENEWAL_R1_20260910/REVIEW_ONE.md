# 独立 AI reviewer one：f34e4964 与 21c0cf45 源码兼容续审

身份：AI reviewer /root/waiver_review_one，owner 明确授权；独立完成，未与另一 reviewer 交流。审阅范围 b3e89de6..21c0cf45 的全部 rwkv_lh/ 和 scripts/ diff；本地 HEAD=21c0cf45d519ee090742c08156cd2935d112b87b。

Agent 级：本次未运行 Agent，不能据代码测试宣布 Strict/completed/mutation 改善或 KEEP；最新既有交接为 Strict 0/15、completed 0/15、mutation 6，终止无进展/角色协议拒绝。角色级：本次只读重建旧限定14来源186个已保存Selector lane，186/186与原checkpoint transcript逐字节相等；不等于token校验、来源准入、标签语义、覆盖或训练通过。

## 判断

**支持对原14来源、仅 selector_intent 续签精确源码身份豁免；不支持“整个补丁仅观测且全程序语义等价”的笼统结论。** 尚待具体新waiver/注册/wrapper的最终SHA复核，本文不是预先签名。旧RP-WEB-02仍整源排除，旧广域草案否决与历史证据不改。

两个冻结RUN_PROTOCOL均已校验原注册SHA，stateful_goal.enabled=true。runner仅在 `not stateful_goal and supervisor_strategy in {parallel_atoms, contract_graph}` 建立atom pool，所以本范围未走改变client生命周期的atom路径。14来源动作再次查明无run_command/check_command；先前命令证据修复的范围理由继续成立。186 lane包含60历史自动候选和126待标签复核，后者不是自动正确标签。

## 逐文件diff意见

| 路径 | 改动和范围内判断 |
| --- | --- |
| rwkv_lh/runtime/openai_compat.py | 增订阅表、去重订阅与逐观察者异常隔离；没有修改请求构造、重试、Native State引用/commit/rollback/token处理。共享client会对全部hook扇出，不能视作每会话隔离；当前14来源stateful_goal按角色独立client，续签不认可共享atom旧错误归属。 |
| rwkv_lh/model_session.py | create_model_session能力发现前与构造时绑定hook，鸭子调用add_audit_hook；_emit和fallback回调异常现在被吞掉。属于可观察行为改变：此前回调抛异常可能中断模型调用，现在继续。实际旧成功Selector边界不依赖该异常，输入与状态处理代码未改；不从新观察日志反推旧未知请求已成功。 |
| rwkv_lh/exact_tool_selector/native_network_client.py | 请求异常/非200在原异常抛出前emit selector_transport_error；payload、成功response校验、fresh State选择未改。新增hook自身异常隔离；已保存成功lane的生成证据可按原门验证。 |
| rwkv_lh/product_runtime.py | Selector hook接入model_audit_hook并加model_role标签；不改四角色session创建和State隔离。不把后加的审计消息当旧因果事实补写。 |
| rwkv_lh/parallel_atoms.py | 新_run_atom wrapper在finally调用model.session.client.close，body移入_run_atom_with_model；这是真实资源生命周期变化，不是纯日志。当前close只关闭requests HTTP sessions，不调用Native delete/rollback，不直接改RWKV State；但对共享或自定义factory client可能有生命周期影响，不能作通用无风险证明。该策略不在本14来源执行范围。 |
| scripts/run_rwkv_e2e_benchmark.py | _build_atom_model_factory不再注入共享rwkv_client，每atom创建新client，消除跨atom订阅扇出。也改变连接池/能力发现次数/cleanup归属；新factory与pool finally必须联合考虑。主Selector加审计hook；stateful_goal角色client隔离方式未改。没有评分/阈值/role input改动。 |

模型factory返回前抛异常的资源清理、自定义共享client所有权、Selector HTTP session关闭不在新增finally保证范围；本审阅不将这些局限写成已完成的全局生命周期证明。它们不构成本14个不走atom路径的来源兼容否决条件。

## 证据与验证

- REVIEW_ONE_VERIFICATION.json：六个生产/runner文件在b3e89de6和当前的SHA、两个冻结协议身份/模式、186lane计数。
- REVIEW_ONE_SCOPE.json：旧14来源SQLite pin核验、全动作、逐边界prior_actions/request_id/input SHA/byte_equal。SQLite仅mode=ro&immutable=1，使用生产RunState与rebuild_role_input，不执行load_source_run豁免准入或extract。
- temp/waiver_renewal_one_scope_20260910.py 与 temp/waiver_renewal_one_evidence_20260910.py 为绝对路径执行的分析脚本。
- 独立专项：pytest tests/test_native_request_recovery.py 中factory首错、每atom独立client、失败cleanup、四角色审计隔离5项通过，65 deselected，0.92s；独立basetemp=data/test_runs/pytest_waiver_renewal_one_20260910，没有使用默认测试目录。

续签仍需：新waiver每条从原e7c455b6冻结SHA映射到当前，而不是将b3中间版本误当原来源；新增所有SOURCE_CODE_PATHS内变化文件，保留不可豁免role协议/vocab和完整token、timeline、字节重建防线；独立wrapper精确固定同一14来源注册、角色、waiver、两份approval及自身SHA，显式fail-closed校验。输出写新experiments目录，不覆盖旧60候选或126复核劳动。没有训练、模型调用或读取hidden acceptance/holdout。

## 具体材料最终决定

**accept，仅绑定本轮 SCOPED_APPROVAL_ONE.json 的三项SHA及 selector_intent。** 已进一步审阅当前wrapper、完整proposal与限定注册：注册字节等于上次批准的14来源注册；10个累计豁免路径逐个与原e7c455b6及当前字节SHA匹配，均属于SOURCE_CODE_PATHS且不是NON_WAIVABLE_PATHS，精确覆盖全部变更的准入源码路径。runner另行审diff，不误称其在源码豁免表中。

wrapper明确require/SystemExit校验，不依赖可被-O删除的assert，强制固定源/角色/输出并验证双AI审批、waiver与wrapper实际SHA。新rationale承认观察者异常与atom生命周期变化、限定14个stateful_goal来源，不声称全局等价；原草案的范围外理由继续有效。独立计算prospective waiver SHA=f53186ecfca2f97126b132f41b1bc37bdef46e77ce91b3cde4a68385ef0a3aaa，wrapper SHA=58aedb07b622959b516b53280314efaacd95c2ee1f493d5221adbcd0ca1d668f。具体核验明细见 REVIEW_ONE_FINAL_MATERIAL_CHECK.json。

本决定仅授权该冻结单元放松粗粒度源码身份代理，原token/State/输入/来源及数据质量门不变；尚未重新extract，不保证恢复数量，未批准126行的语义标签或训练。
