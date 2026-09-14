# 命令结果回答来源准入 R1

任务级：本工程轮新增Agent通过数0、训练步数0、数据集版本0。R4仍NO_KEEP；本修复不能当RWKV能力改善。

根因：direct_actor回答冻结只从observation.exact_spans收集文本SHA。生产命令投影把完整stdout/stderr放在result.command_streams，导致真实命令输出已在下一次输入中，冻结却把它当未观察到；旧逻辑还会将不存在exact_spans的完整结构投影拼成空文本SHA。

最小修复仅在direct_trace_data的数据准入层增加完整命令流绑定。要求已进入该生成祖先的实际观察、正确command_streams适配/权威、完整流、逐span内容SHA/字节连续性、stream整体SHA/字节/字符长度，拒绝混合combined与分流身份。文件文本与合法空文件行为保留。不会把未来验证结果、隐藏验收或强模型接管结果灌入原输入；不改模型协议、输入构造、工具参数、State、答案或运行调度。双独立审核、source-family隔离、原回归、sourceprofile限制C01与完整freeze身份门全部保留。

回归：旧逻辑在check_command/run_command的stdout成功和stderr失败4项公共freeze测试上均以“summary target uses unobserved source”失败，6个拒绝边界原本通过。补全测试夹具计数后再次4红6绿，原日志保留。最终新增15项覆盖合法两工具/两结果、未来观察、截断流、SHA错、span错、字节缺口、未知适配、混合流、Unicode以及原文件/空文件；完整1802 passed、0 skipped（325.49秒），Torch/State/浏览器按仓库完整tests运行，只GPU0。

额外真实证据：R4两条zero命令回答完整重放后，原规则无法绑定已见stdout，新规则绑定成功；这是只读工程诊断，不将开发评测输出准入训练。现存v3全部24回答源SHA仍通过，60条数据未改。输入转移覆盖缺口依然存在，必须实际采集和审核新边界才能补齐，不能只修freeze就宣称已有训练数据覆盖。

修复发生在R4两臂和创建迁移实验全部结束并记录SOURCE_AFTER之后；这些实验源码/原结果不变。Owner五处未提交修改保留，代码提交只包含本修复和新增测试；本地提交，不push。原型测试隔离了与本门无关的token/native回放等门，真实trace探针补充校验实际重放；不能把单元模拟当生产样本。
