# Claude 交接：停止扩量和训练，数据质量审核未完成（2026-09-20）

## Owner 最新指令与当前状态

Owner要求停止当前工作，整理文档交由Claude接替。**不要自动续跑、不要按旧授权直接启动训练。** 当前1000条只能称候选数据，不能称已经验收的统一Code Agent StateTune数据集。本轮未启动新训练、optimizer steps=0、未运行新Agent评测。无新通过率、无训练收益、无成品交付结论。

最终产品目标是给RWKV做专属Harness和Code Agent；同质量下低成本、低延迟、高吞吐是目标属性。此次执行偏离在于大量时间用于单文件算法解答，真实项目读改测与反馈覆盖没有同步增加。达到数量和通过既有测试不能替代产品目标验收。

## 接手必须保留的工作区

先读AGENTS.md、docs/HANDOFF.zh-CN.md。WSL UbuntuRecovered执行项目逻辑。服务器禁止Git；仅本地Git，上传冻结源码及SHA清单。只用GPU0，不触碰其他账号进程。此次不push、无前端、无子代理/审核代理、无教师API。最终holdout未读取，不读acceptance_tests或Real Agent Holdout V2。

五处接手前已有修改保持原字节，**不得覆盖或擅自提交**：

- rwkv_lh/controller.py
- rwkv_lh/model.py
- rwkv_lh/supervisor_openai.py
- tests/test_hybrid_supervisor.py
- tests/test_supervisor_openai.py

R33 STOP_AND_HANDOFF.json保存逐文件SHA复核。此次没有修改生产代码/scripts/tests。源码相同的R31完整工程回归为1910 passed、0 skipped；此结果不是数据语义正确率或Agent成绩。最近已提交数据扩量检查点为cf1a8cc5a；本交接提交只含文档与实验记录。

## 已发生的训练与删除

R29曾过早用647条启动训练，owner随后要求先补足1000：已停止，真实87 optimizer steps、348样本、0完整epoch；未评测或保留候选。不能删除历史成本记录。

Owner本次要求删除此前中断State，已删除远端唯一FAILURE_STATE.pth：
`/home/chase/GitHub/RWKV-LH-unified-train-r29-647-20260920/training_runs/direct-unified-r29-647-20260920/FAILURE_STATE.pth`
既有SHA为64b2632876968076405e056ceb9bdcb39f279915c1296bae8b6737d6c20f0361。REGISTRATION/RESULT/events审计账本保留。删除证据在R32/R29_INTERRUPTED_STATE_DELETION.json；不得恢复此State。

R32准备了1000条fresh-zero、1epoch、accum4、250updates、LR1e-4、seed20260914、18000s/80GiB/GPU0方案，但**没有启动训练**。数值兼容检查通过，耗时558.49秒、0optimizer steps；远端compat unit已inactive/dead，训练unit未启动、inactive/dead。远端根为`/home/chase/GitHub/RWKV-LH-unified-train-r32-1000-20260920`，SSH alias `rwkv-8222`。启动helper增加R33 TRAINING_GATE检查，目前false。

## 1000候选的来源和分布

历史加载接受1003条，R31剔除3条关键信息仅在缺失图片/公式中的记录后，计1000个真实生成边界；888 source_id、851份不同来源内容。**不是1000独立项目、不是1000条RWKV正确答案。** R23原始失败与纠正候选均保留。

|类别|条数|占比|
|---|---:|---:|
|标准输入输出算法题写solution.py|750|75%|
|真实成功读取|122|12.2%|
|最终回答/总结|65|6.5%|
|执行命令|59|5.9%|
|项目代码编辑标签|4|0.4%|

动作：write_file751、read_file122、final_answer65、run_command52、check_command7、replace_text3。4个项目编码标签实际上是3处已有文件替换＋1次timebook.py局部创建，不应将4全部说成已有代码修复。

来源family：ULTRADATA_RL_CODE697、ULTRADATA_CODE240、MAINT30、RAG20、CLI6、FULL4、ANYIO2、LOGURU1。family是来源标记，不是能力验收。

更重要的覆盖缺口：

- 750算法代码中707条原工作区缺solution.py，43条已有代码未通过既定检查；不能将750统称bug修复。
- 只有6条算法纠正的真实输入祖先中含失败命令反馈；绝大部分不是测试失败后修复。
- 59条命令中52条为同一个`python public_checks.py`模板。9条实际非零退出是有价值的失败诊断，不是错误标签；50条为exit0。
- 65条final：43条无命令观察、22条实际执行结果报告；全部没有本次已执行修改的祖先事件。没有“本次改代码＋验证＋最终交付总结”的收尾训练覆盖。
- 无search/list等动作的正向目标。不能把有工具菜单等同于已训练工具选择覆盖。
- 750算法条目占目标token91.04%；按当前trainer四条一组token加权、固定shuffle模拟，其loss系数份额约89.29%；项目编码0.53%、命令1.29%、读取2.48%、回答6.41%。这是计划loss系数，不是实际梯度贡献或已证实退化。

## 哪些检查完成，哪些没完成

完成：

- 1000行格式、生产协议、token/BOS/stop、上下文长度和target-only mask审计通过；协议/模型/tokenizer身份各唯一。历史344条外层name/arguments→function/params修补发生在R28，当前已修补，旧错记录保留。它本应早期被阻止，不应到大规模才发现。
- 1000行源State祖先/事件统计和原验证证明SHA核对；输入、输入＋目标、request＋checkpoint完全重复均0。目标完全重复17组/额外145行，源正文重复108组/额外149行，不能因动作相同直接删掉不同上下文。
- 与原固定开发回归的注册相似度/文件隔离检查通过。
- 65条最终回答逐条核对源码/观察及执行声明，未新识别明确实质事实错；122读取来源有真实成功工具结果。4项目编码、59命令检查既有源请求和执行证明。750算法代码全部AST可解析、未发现非标准库依赖；历史750候选均有原baseline失败→candidate通过证据，共23802个验证case执行记录（case可含多个输入实例）。
- GPU0数值State兼容检查通过，未训练。

未完成：

- **全量fresh重放/执行复验被owner停止**。进程802641已TERM，最后观察到0起始row index900；没有DATA_RESULT.json。不要把所有原证明通过写成这次1000全量fresh复验完成。
- 没有对750算法做一轮全新的、独立于作者的逐题数学正确性证明。既有作者审查与固定测试不提供普遍正确保证，53条stdio甚至没有algorithm_assessment专门字段（不能仅凭字段缺失断定答案错）。
- 新公开样例审计及来源质量归因未完全收尾，下面记录真实范围；不能称R33完整语义验收完成。

## 新发现：源题损坏与验收不足

已记录隔离4条（SOURCE_CONTRADICTIONS.json）：

- index468，CODING-84bc96c3b04a83976df7592a：迷宫样例空格与重复规则冲突。
- index675，CODING-8482a27224f4ea0e2b690f18：CRC样例输入缺空消息，输出多一个00 00。
- index775，CODING-797547459773d293d378e39c：要求n行，n=5样例只剩17一行；正文公开枚举17/16/13/9/5。
- index792，CODING-cb1726cd951b92c22221dc86：按正文覆盖规则公开实例枚举73矩形，样例21。不得自行改样例或认定私有测试优先。

后续发现但尚未合入隔离清单：index773源网格多组样例宽度与W矛盾，疑似#字符丢失；index669/894有数字被翻译成英文单词的损坏版本，同时又附正确版本；index784/944有残缺重复样例，同时有完整另一份。应继续区分正文可唯一解答、仅示例损坏与实质歧义，不能机械全部删，也不能无视冲突直接放行。

全源扫描另有字面\n样例25条、HTML实体9条、外部样例附件占位5条、空样例输出4条，类别可重叠，仅是风险标记。

公开样例复验（不改变原评分）：

- 围栏提取覆盖359/750条，322全部匹配、37需归因。16条仅对诊断样例解码HTML/字面换行后通过；21条包含正文冲突、附件占位、空输出、输出中夹说明或提取问题。源输入与训练target没改。
- 余391条尝试纯文本提取，309有候选样例、82未可靠解析。第一版regex的\s错误吞掉首行数字，结果明确INVALID_PARSER并留红绿证据；V2修复后300匹配、9需归因，不能把修parser称RWKV收益。
- V2九项：62空输出被说明文字误提取，390/891输出空行导致截断；527是表格/残缺尾部示例，669/773/784/894/944为上述来源损坏或重复样例问题。不要将其未经归因直接计为模型错误。
- 所有这些只是补充诊断，不能替代原精确输出验证，也不等于所有算法泛化正确。

额外审计失误已记AUDIT_INDEPENDENCE_INCIDENT.json：一次想只看测试元数据的临时命令误输出4条私有验证数组（303/468/775/792）；不是最终holdout。没有据此改任何候选或模型输入；不能将这4条此次审计再称盲审，未来改题需另设未暴露验证。已知4条公开矛盾在此之前即由公开样例发现。

## 数据处置与后续建议，尚未执行

整批降级为候选库，TRAINING_GATE=false。4条已隔离不意味着其他996条已通过全部语义审核。不要静默修改原模型输入、原输出或评分，也不要用隐藏测试答案纠正训练标签。

应先补可靠自动准入：唯一生产构造/target渲染、全行mask/token检查、来源完整性、公开样例与正文一致性、真实执行、去重/隔离、任务/动作/反馈覆盖统计。规则能做的检查放在首批准入，不反复消耗模型做机械工作。语义矛盾必须显式隔离，不用accepted=true自我签字代替证据。

重新定义数据目标：算法代码可作为辅助池；主池优先真实项目定位、已有代码修改、失败测试反馈后修复、诚实交付总结。继续一个统一State方向，不按每个错误堆独立State。是否调整采样和补数据由下一任先报告证据与具体方案；未经owner重新确认不要自动照R32旧计划训练。

原冻结12题开发评测和72次zero-a/zero-b/candidate对照准备仍在R32/evaluation，未运行。即使以后训练loss下降，也必须独立任务检验，不用训练题或已纠正答案证明能力。

## 文件索引

- R23：`data/experiments/RWKV_UNIFIED_DATA_EXPANSION_R23_20260919/`，原纠正批次与失败样本。
- R31：`data/experiments/RWKV_UNIFIED_DATA_CHECKPOINT_R31_20260920/`，库存、图片完整性、1000名单、工程回归。
- R32：`data/experiments/RWKV_UNIFIED_TRAIN_R32_1000_20260920/`，1000聚合REVIEWED_ROWS、格式mask、隔离、源码、compat、未完成refreeze与训练准备。没有训练完成记录。
- R33：`data/experiments/RWKV_FULL_1000_AUDIT_R33_20260920/`，本次逐行审计、分布、公开样例原始结果、隔离、训练阻断与停止记录。
- 大体积输入/源码快照保留本机原路径，不应假设本交接Git提交包含所有可迁移运行工件。运行前逐文件检查SHA与路径，不恢复旧schema或远端Git。

本轮责任：把数量、既定测试通过与Code Agent训练就绪混同；分布和源题一致性检查太晚；手工大量算法纠正未形成目标所需的工程闭环覆盖。不能靠训练或继续凑数把这轮投入解释成已经取得的成果。
