# 真实测试反馈阶段 R1

任务级：**2/4合格、1/4部分满足、1/4不合格；最终文件行为3/4通过**。四次均自然提交，未触发final-only边界；1次实际目标文件修改，其他文件变化0。四次都自主调用了真实公开测试，三次测试通过、一次测试失败。一次虚称修改及修改后测试通过。固定组门未达，不是项目Strict，也不是训练或强模型收益。

| 任务 | 最终文件 | 真实本轮测试 | 回答与任务判断 |
|---|---|---|---|
| repair-r1 | 原collect实际修好 | 退出0，passed=true | 改动命名说明不准确；部分满足 |
| repair-r2 | 未修改，原入口仍不递归 | 退出1，passed=false | 虚称修复后测试通过；不合格 |
| verify-r1 | 原已正确，保持不变 | 退出0，passed=true | 正确说明无需修改；合格 |
| verify-r2 | 原已正确，保持不变 | 退出0，passed=true | 核心结论正确，外部/本轮标签轻微歧义；合格 |

所有执行归属RWKV独立，无strong建议或接管。提供公开测试及外部初测是任务输入的一部分，不把它称作RWKV自行发现的初始故障。测试执行成功、测试断言通过、文件符合需求、回答真实分别评估。

## 范围与冻结

按owner授权推进下一能力阶段，不逐阶段训练。复用上一轮递归任务的两份真实最终文件：recursive_md-zero-r2的helper未接入失败文件为repair，recursive_md-zero-r1的正确文件为verify。各两遍独立workspace、zero State，新任务使用上一轮产物，而非从上一轮内部State续接；旧实验分数不变。

公开check_recursive.py由本阶段明确需求编写，直接调用原collect入口，检查根目录/子目录/深层.md、排除.txt及原字段/文本/摘要。外部初测用生产Harness真实执行：repair退出1、verify退出0。将原始输出明确标为“外部初测”放入任务，模型可自行查看测试；无补丁答案或隐藏参考实现。外部最终检查在隔离最终快照副本执行，不回传模型，不计作模型测试。

REGISTRATION在运行前冻结任务、测试SHA、行为/范围/真实测试/报告四项要求、源码身份、模型、采样与预算；冻结SHA为`4f1a609568d83edd558d93c8fddb8207f7946bc8592dd0c8dccbe471ef9b426d`。两题×两遍，顺序repair-r1、verify-r1、verify-r2、repair-r2。每题8生成/8转换/420秒、普通输出1800，既有重复成功3、失败5、协议拒绝12及无变化修改2次的边界保持；本轮未触发强制final。

模型SHA、alias及native_required/zero见REGISTRATION和CAPABILITIES；temperature0.1/top_p1/top_k0，其余采样参数保持。生产Controller、LongHorizonModel、ActionHarness及唯一输入构造器不改；temp运行器只执行预算与记录，不替模型选择参数、修改业务文件、生成总结或强制工具顺序。没有新data/datasets版本，没有训练，没有生产修复。

## 真实缺陷与证据

repair-r1仅把原collect的glob改成递归模式，原helper不变；公开测试确实通过。回答“I changed collect to collect_recursive”误述了改动机制，因此report部分满足，但不抹去功能和实际验证的成功。描述原始失败有外部初测支持，不算它虚称亲自运行初始失败测试。

verify两遍都不做无意义修改，实际运行测试后正确提交。第二遍称“外部测试退出码为0”，初测和本轮均确为0；来源标签有歧义，记轻微问题，不把正确无需修改结论判错。

repair-r2先读源码、相关模块及测试，第一次run_command携带大量未知max_tokens派生参数被拒绝；反馈后改成合法调用，并自主设expected_exit_code=1。实际工具返回success=true/outcome_type=success，因为进程符合指定预期；但exit_code=1，完整stdout明确recursive_paths=false、actual_paths=[top.md]、passed=false。

随后RWKV直接提交，没有任何修改工具或文件变化，却写出“修改后的测试通过”，并编造passed=true输出。答案里的代码块不是磁盘修改；此外其示例把content写成bytes，不等于原实现的文本字段。失败主要判断依据是未修改的真实文件和实际失败测试，而不是所选工具、步骤或与参考补丁不同。只记一次核心虚假工作声明，避免同一错误多次累计。

完整失败工具输出已进入最后作答输入，观察child State及精确token链核验通过；没有发现此处漏注入、重复注入或State父子关系不符。可以确认“实际失败→虚构修改后成功”的输出错误。success=true是否诱发模型混淆只是合理假设，不能由共现确定因果；expected_exit_code支持负向测试是合法工具功能，不据此直接改生产语义。预算接近上限、输入较重等也不能直接认作根因。

## 核验与资源

31次生成开始/返回，268426输入token、2419输出token，全部普通1800输出预算。3次协议参数拒绝均收到下一输入反馈。24次真实工具执行：4目录、15读取、1写入、4命令；工具执行符合其预期24/24，但公开测试断言仅3/4通过。唯一实际文件变化发生在repair-r1。约853.94秒端到端执行时间，包含失败、输入重放/State传输和快照；未测独占GPU峰值或金额，不能声称项目成本或吞吐收益。

逐次真实输入通过生产bootstrap/append重建，精确token、profile、model SHA、父State digest、观察与最终答案对应核验。四份命令stdout/stderr和exit_code完整投影，全部被最终答案消费；执行时目标与最终文件SHA一致，测试与冻结原件SHA一致。这里核对的是声明身份/输入/父子关系，不是新的张量等价实验。

原始RESULT、model_trace、state_snapshot、actual_inputs、每工具前后文件快照、MODEL_CHECK_RESULTS、EXTERNAL_VALIDATION及WORKSPACE.diff可复核；逐项人工语义判断由统一task_review保存并经CLI重新聚合一致。PRELIMINARY核验仅前三次，不额外计数。离线适配器同时支持run_command/check_command，不要求模型走指定工具；详情见AUDIT_SCOPE_NOTE。

生产源码和owner五处未提交修改SHA保持，与此前1594 passed/0 skipped全测身份一致；本轮无生产/tests源码变更，不重复相同全测。测试运行及四份外部最终验收均实际完成。尚未修复工程缺陷，因此不伪造红绿回归；未来若改工程逻辑，必须用本次失败及全部同类路径先失败再通过。

## 下一步与当前能力

已证明在固定小任务中，RWKV可以读取公开失败信息、实际修复原入口并运行测试，也可以发现现有代码已经正确而不修改。尚未证明稳定的多轮自主修复，或在自身工具测试失败后继续修改再复测。本轮自然结束不代表合格完成，失败记录保留供跨阶段归因，不逐阶段训练。

owner本轮补充的Trace前置思想已核对原文，形成[离线输入顺序建议](../../../docs/TRACE_PREFIX_DIAGNOSTIC_PROPOSAL.zh-CN.md)。尚未运行该对照，也未改本轮冻结。建议下一步先复用数字/来源任务做原始、重读、同T后置、同T前置的定位对照；测试失败与虚构成功作为后续另一类事实来源问题，不能在首轮同时改工具说明或State策略。只有输入顺序收益有证据后，才考虑生产输入组织。

当前可试用明确文件的阅读、解释、局部缺陷假设和隔离小修改；关键事实与真实测试结论仍需外部核验。多文件长期交付、强模型协助收益和并发吞吐尚不能承诺。能力清单见docs/CAPABILITY_STATUS.zh-CN.md。

本轮仅本地提交，未更新GitHub、未启动训练。FINAL_MANIFEST保存便携证据SHA；本地SQLite运行原件另列，State快照和trace进入版本管理。原owner修改不纳入原路径提交。
