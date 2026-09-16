# R17：Qwen3.8-27B 教师纠错部署

Owner明确要求直接替换教师模型，重新组织提示与材料，并运行全部。Owner进一步确认累计1024条RL全部进入纠错队列。20题消费者已在waiting_for_model阶段停止，0模型调用；统一1024队列保留这20题的原始边界并优先执行，不重复计数。RWKV仍是产品默认执行模型，本轮替换的是离线纠错教师。

## 输入设计

唯一构造函数 `rwkv_lh.teacher_input.build_teacher_input`。System明确实际交付、工具自主选择、测试失败后继续修复、stdin测试需真实输入、只报告已发生事实。User包含原用户目标、当前工具schema、源失败候选（不可信）、源工作区文件入口，以及教师本轮实际动作/参数/原始工具输出。教师自行读取所需任务和代码；不自动给实现方案，不替它选参数。

不传全部RWKV历史，不传未来源轨迹、私有测试/答案、重复State/SHA/chunk审计字段。保持文件正文、数字、命令输出和完整性/截断/游标元数据。教师本轮已发生动作全量保留，不静默裁剪；完整原始生产输入及所有审计字段在trace/来源材料保留。此变化不是“把所有内容重新概括一遍”，不通过摘要模型创造新的事实。

教师从所选真实生成前的工作区快照重新执行，使用新会话；不把RWKV张量State移给Qwen，不宣称输入与原RWKV边界完全相同。教师成果归strong_takeover。纠正只是候选，须经产物/语义/边界适用性审核；不得直接把教师整段接管轨迹当RWKV独立完成或同输入训练标签。

## 模型、预算与隔离

官方 Qwen/Qwen3.8-27B BF16，固定revision见REGISTRATION/MODEL_SOURCE。复用已冻结vLLM0.29.0引擎，GPU0+3 TP2，语言模式、原生262144上下文、reasoning parser qwen3；temperature1/top_p0.95/top_k20、thinking enabled、reasoning_effort medium。24调用/1800秒/每次16384输出token（含思考）。这轮同时改模型、输入和预算，不据此宣称某个单项的因果收益。

整条链路在服务器运行，模型18244回环端口。原20题及其私有stdio验收不变，其余1004题按各自封存manifest恢复最后真实生成前快照与原私有验收，原R15/R16结果不重算。实际工具仍由现有Controller/Harness执行，JSON解析及参数验证沿用生产协议。源代码完整manifest在本地生成并上传，服务器核对实际文件，不运行Git。

## 新增工程保护

每次HTTP生成前向同一引擎/tokenize发送实际聊天消息及模板参数，按教师tokenizer核对输入+请求输出<=服务上下文上限，避免RWKV计数代替教师计数。超限保留证据，终止该题为context_budget_exhausted，不截断、不谎称完成，后续题继续。只有思考、输出预算耗尽而没有动作内容时，分类为output_budget_exhausted，不作为服务宕机停止全队列。网络/身份/沙箱等基础设施错误仍停发并记录。

新构造、上下文越界和思考耗尽均有红→绿回归。首次输入服务器probe只构造上下文并故意停止，不算真实模型调用或任务通过。完整回归结果见FULL_TESTS_FINAL.txt。

## 上轮真实结束情况

R16已停止：13/20尝试、11提交、8题修改、1调用预算中断、1HTTP400中断、7未运行；全部产物通过0/13。75次生成尝试/74返回。HTTP400原文为输入至少24577+8192输出超过32768，不是Qwen原生上下文限制。R16采样候选与验收原样保留。

## 原20题准备位置（已停止，零真实生成）

模型目录：`/home/chase/GitHub/RWKV-LH-teacher-r17-20260916/`
执行目录：`/home/chase/GitHub/RWKV-LH-server-teacher-r17-20260916/`
模型unit：`rwkv-lh-teacher-r17.service`
纠错unit：`rwkv-lh-server-teacher-r17.service`
进度：执行目录 `outputs/STATUS.json`
逐题：`outputs/runs/<ID>/DELIVERY.json`及`execution/`。

waiting_for_model只表示等待模型，不代表开始纠错。最终报告需以实际API调用/工具结果/DELIVERY为准。

全量执行目录 `/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916/`，unit `rwkv-lh-teacher-1024-r17.service`；双进程、SQLite事务认领与持久收据，1024唯一来源。工作区/输入隔离，当前任务中断不自动重试；进程重启发现未决running时要求核对trace，避免重复生成。产物已通过的快照重验后保留、语义审核单列；不自动当作教师纠正或训练数据。64GiB磁盘保留门在派发前检查；基础设施错误停止新派发，其他正在执行的任务保留至有界终止。每题24调用/1800秒，1024题总量与双进程为本轮资源上界，未宣称固定时间内全跑完。

全量准备49240文件/约5.19GB（传输压缩），manifest SHA `c0975b59f4da3d73a69773276fe55d5eb0a1c1aae45e6224229dda24467f0773`。R10封存证据来源R12 sealed索引，R13来源逐任务retirement；均核对源文件SHA，未恢复已删除原生State张量。首次准备因R10/R13索引布局不同中止，原日志保留后按各自已冻结索引读取，未改原数据。

完整回归1894 passed、0 skipped，330.78秒。没有启动StateTune训练，没有新增datasets版本，没有push。
