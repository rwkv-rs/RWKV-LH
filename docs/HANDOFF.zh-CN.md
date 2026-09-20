# 最新：Owner要求停止，交接Claude（2026-09-20）

以[本次交接](CLAUDE_HANDOFF_20260920.zh-CN.md)为准。1000条降级待审候选；新训练0步，训练门false。全量fresh复验已按owner停止，未完成；旧R29中断State已删除、账本保留。原五处代码修改不动，不push。下方“训练就绪/有效1000”为此前阶段记录，不能覆盖本次质量审核结论。

# 当前 R31 已补足：有效1000条，正在完整冻结后训练（2026-09-20）

最新owner要求不中断完成“真实格式1000→StateTune→独立测试→缺陷总结”。当前正式有效1000条，888个source_id、851份不同来源内容；尚未启动新训练，不恢复R29中断State。R28 corrected647为基座，仅累加35以后已通过加载器批次。公开验证候选不计数。1910工程回归全绿、0跳过；无子代理、教师API、未push，接手时已有五处修改保持。准确库存与SHA见 `data/experiments/RWKV_UNIFIED_DATA_CHECKPOINT_R31_20260920/INVENTORY.json`；R23 STATUS已同步。此为工作中检查点，任务尚未完成；下方旧数量为历史。

文本可用性复核：历史1003条中排除3条关键图片/公式缺失，当前1000为过滤后数；见R31 TEXT_SUFFICIENCY_REVIEW、TEXT_ELIGIBILITY_INVENTORY和ELIGIBLE_SAMPLE_IDS。保留历史结果，训练不得绕过有效名单。

# Owner最新顺序：先满1000，再训练（2026-09-20）

Owner明确修正：先完成格式修补，再补足至少1000条合格数据，之后训练与测试。647条R29训练已停止，服务inactive/dead；实际87 optimizer steps、348样本、0完整epoch。中断State仅诊断，不保留生产、不继续R30评测。真实ledger与停止原因见R29 training/interrupted和OWNER_ORDER_CORRECTION_20260920.json。当前已冻结647条，仍差353；batch35四条仅公开交叉验证通过，尚未计数。以下647提前训练授权已被最新指令替代。

# 最新R28格式修复完成（2026-09-20）

647条已全部重新冻结；344条外层格式修复（R22 30＋R23 314），v6 300与R20 3原本一致。647条真实输入、token/mask/长度/参数/执行证据复验通过，1907工程回归全绿、0跳过。新包为`data/experiments/RWKV_TRAINING_TARGET_FORMAT_R28_20260920/frozen_corrected/`，SHA与逐行映射见该轮RESULT和REPORT。旧样本保留，不计新增。后续扩量从新647包开始，使用`temp/freeze_expansion_batch_r23_wire_r28_20260920.py`，下一新批次35；不要再调用旧内部name/arguments生产器。

Owner已授权先用修复后647条训练一轮、继续补到1000。R29冻结当前源码，GPU0、zero初始化、target-only mask、1epoch/162预计更新；已补当前依赖身份并重新做Native数值兼容。训练实际状态以R29远端ledger为准，不能由准备记录推断已训练。R27固定开发基线31/48（zero-a15/24，zero-b16/24），213生成/State核验通过；新建文件产物4/4但忠实交付3/4，已有代码修复0/16。R29须同源码重新对比zero/candidate，不拼接R27成绩。无子代理、无教师API、未push；owner五处修改保持。

# 最新交付优先级（2026-09-19）

Owner 要求尽快成品且不降质量。当前 R27 已在服务器 GPU 0 运行冻结的 48 次 zero 开发基线，外部验收尚未完成，不改两臂执行源码。R23 冻结包合计647条，但新全量格式审计确认344条目标使用name/arguments，而输入要求function/params；这些条目需保留原件后重新导出和验证，不能直接宣称本轮训练就绪。另303条使用要求的键。训练未启动，未push，无子代理。具体交付范围、证据和下一步见 `data/experiments/RWKV_UNIFIED_DATA_EXPANSION_R23_20260919/PRODUCT_DELIVERY_PRIORITY.zh-CN.md`；全量逐行证据见同目录 `TARGET_ENVELOPE_AUDIT.json`。下方645等数量为旧检查点。

# 当前工程检查点 R26（2026-09-19）

R23正式645条，距1000差355，尚未训练。R24命令入口已修复；R25真实基线在第二次相同任务发生退休State回执复用而停止，首题原评分通过但整组比较INVALID，服务已停。R26已将create分配身份绑定到持久化checkpoint，保留同一请求恢复，1905完整回归通过/0跳过。1024原采集初始handles互异，无本类transport终止。必须新冻结源码后完整重跑基线；不把R25拼接为收益，不宣称成品完成。详见R26 REPORT与RESULT。Owner五处修改保持，未push，无子代理。

# 当前进行中 R23（2026-09-19）

Owner目标正式统一数据至少1000条、约1500条，并明确禁止独立审核子代理。当前正式645条（起点333＋本轮312），距1000还差355；只有已冻结且加载接受的批次计数。STATUS.json与批次manifest是数量依据。由当前Codex亲自纠错，子代理0、训练0、推理API0、未push。没有后台Codex自动创作；仅验证脚本可异步执行。旧R21未验收计数不能直接加上新训练行，任务/边界分开。原始失败与有歧义来源隔离，不靠重复读取或重写同一答案凑数。

当前路径：data/experiments/RWKV_UNIFIED_DATA_EXPANSION_R23_20260919/。R23尚未完成到1000，不把本检查点当任务完成；下方R22为已完成历史。
<!-- END R23 LIVE -->

R24产品入口工程修复已本地提交587af6491：rwkv-lh改接现有CodingJob，实际help红→绿，1900完整回归通过/0跳过；模型协议与执行循环未改。R23最新645条见CHECKPOINT_EXTENSION_AFTER_R24.json，仍差355，尚未训练。R25已冻结原有12个隔离开发任务与当前源码，在服务器GPU0准备新zero基线；模型/engine/源码校验通过，服务启动中，是否已开始任务以R25 STATUS.json为准。尚不能宣称完整成品验收。

# 最新交接检查点 R22（2026-09-19）

**30条R21真实编码纠正已正式冻结并由训练加载器接受。现有可用库存333条调用边界（v6 300＋R20 3＋R22 30），仍为三个包、未创建新dataset版本；333条target-only mask全通过，最长24455/24576。新增30条生产输入/State重放、两遍本地fresh红→绿、来源去重/固定回归隔离通过；原始远端证明及错答保留。不训练、不push、生产代码未改。1024任务仍是80独立产物通过、83已验收、941未验收；本轮新增Agent运行0，非Strict或RWKV训练收益。下一步补剩余真实纠正，尤其测试反馈、有效修改与忠实收尾，不只堆算法题写入。见[R22报告](../data/experiments/RWKV_CODEX_FREEZE_R22_20260919/REPORT.zh-CN.md)及TRAINABLE_INVENTORY.json。**

# 最新交接检查点（2026-09-19）

**R21 进行中：Owner 要求 Codex 直接完成 1024 题纠错，尚未全部完成。76 题已写、73 题通过固定 exact；原8通过产物本次最终文件复验7通过、1超时，超时题已由 Codex 修复。合计80个独立产物通过、83个已验收、941个尚未验收；不是项目Strict。30个任务完成真实原边界绑定与隔离红→绿，尚未冻结/训练；一条长输入已改用真实早期边界复验通过，30来源最长24213/24576，无截断。76/76原输入和State重建通过。初始10条不可见误报来自临时审计的CRLF转换，已留痕修正，生产逻辑未改。哈希构造旧exact0/34保留，新语义全域999/999单列。教师与旧模型权重已清理约126.66GiB，保留共享venv/trace/私有验收；无后台教师或Codex自动纠错。1894回归全绿、owner五处修改不变；不训练、不push。详见 [R21报告](../data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917/REPORT.zh-CN.md) 和 PROGRESS.json。下方“运行中”为历史。**

R19 2048/4096 各两题均已结束，4次均未通过、重复成功调用耗尽预算；4096不再运行。不要恢复旧1024教师队列。下一步是继续手工纠正与源边界/训练准入，不把正确独立脚本自动当成已入训样本，不为清理或续跑在服务器调用Git。

# 当前交接（2026-09-16）

**最新 R20（2026-09-17）：已正式冻结3条真实仓库诊断动作纠正，Loguru栈深度复现、AnyIO stdin签名缺口、AnyIO临时文件公开API缺口；3任务/2仓库，项目修复完成0，训练0。双隔离Qwen审核＋实际Harness复验＋生产重放/16K/target-only mask＋既有固定回归隔离门通过，442目标token；增量包位于 `RWKV_REAL_CODING_DATA_R20_20260917/frozen_increment/`，不新增datasets版本。1894回归全绿、0跳过。1024队列已暂停，19留痕/0产物通过，2未决中断需核对；不要误读为仍运行。R19首次seed预检失败0模型调用，修正后2048两题仍重复调用中断；4096限定对照后台继续，未推广。未训练、未push。见[R20报告](../data/experiments/RWKV_REAL_CODING_DATA_R20_20260917/REPORT.zh-CN.md)。**

**最新 R18：已移除教师 --enforce-eager，CUDA Graph/编译实测启用；固定双请求短输出预热后27.2→82.7 token/s（3.04倍），不是任务通过率。首2题输出预算耗尽原件保留，切换中断2题封存后显式重试；1024队列已用新服务恢复。模型unit `rwkv-lh-teacher-graph-r18.service`，端口/队列目录不变。仍未改思考预算，未训练、未push。见[R18报告](../data/experiments/RWKV_TEACHER_CUDAGRAPH_R18_20260916/REPORT.zh-CN.md)。**

**最新 R17：已部署 Qwen3.8-27B BF16（官方固定 revision、262144 上下文）到服务器 GPU 0＋3，API 18244。Owner 明确授权全部 1024 条 RL 入纠错队列；来源已全部校验并冻结，双进程后台服务 `rwkv-lh-teacher-1024-r17.service` 已真实调用模型，首两题自主读取 TASK.md 后继续生成。8 个历史原产物通过任务先重验，教师产物通过与语义审核、训练准入分开。1024 不是纠错成功数，训练准入仍 0。教师输入改为目标＋工具＋不可信原候选＋本轮真实观察，保留完整审计；每题 24 调用/1800 秒、每次 16384 输出 token，服务原生 256K，实际 tokenizer 预检。全回归 1894 passed、0 skipped。R16 已结束于 13/20 尝试、11 提交、8 修改、0/13 产物通过；旧 20 题 R17 等待消费者已停且零生成，避免重复。未训练、未 push。详见 [R17 报告](../data/experiments/RWKV_QWEN38_TEACHER_R17_20260916/REPORT.zh-CN.md)。下方运行中描述均为历史，实时以服务器全量执行目录 outputs/STATUS.json 为准。**

**最新R16：R15实际已在第3题240秒HTTP超时后停止（前2题产物0通过、17题未运行），下方“20题后台进行中”仅是历史。已修复教师请求与任务剩余预算不一致、服务器AppArmor沙箱配置、系统Python虚拟环境链接在沙箱内不可见的问题；真实服务器stdin/写入/私有文件隔离和stdio正确/错误/超时检查通过，1890完整回归通过、0跳过。同20题已重新冻结，在服务器`rwkv-lh-server-teacher-r16.service`运行，调度/工具/测试/记录全在rwkv-82，直接18243端口，不依赖本地模型转发。首快照2提交/0修改/0产物通过，第3题生成中；前两题仍只给计划，完整任务/语义审核待完成。模型暂保持Coder-Next FP8，Qwen3.8作为后续独立候选；输入封装影响尚未证实。训练0，未push，owner五处修改不变。见[R16记录](../data/experiments/RWKV_SERVER_TEACHER_R16_20260916/REPORT.zh-CN.md)，实时状态以服务器outputs/STATUS.json为准。**

**R13采集已完成：累计1024条RL任务（另5条SFT）；本轮512条、15提交/5产物验收通过、56条修改、4078生成，512条trace完整且State全部released，两个blobs目录0文件。R10＋R13共24提交/8产物通过，非项目Strict。已停止两张卡的采集服务。owner授权开始本地纠错试验R15：固定20真实失败（8协议/8重复读取/4失败提交），原失败20/20复现；Coder-Next FP8权重已完整校验，独立vLLM0.29.0在GPU0＋3已启动。默认custom all-reduce启动卡顿，关闭后API及实际生成成功，首题已真实写入solution.py；20题后台纠错进行中，任务验收待完成、训练0；看`RWKV_LOCAL_TEACHER_PILOT_R15_20260916/STATUS.json`，不能把等待服务当模型已运行。**

**R13已启动：新增512条RL Code已全部准备并冻结，GPU0＋2、并发4后台采集，目标累计1024条；14:30快照新增13/累计525留痕，4执行中，0提交/0产物通过、1条修改。13条79生成完整封存并自动退休State。5条SFT另计，不纠错不训练。36小时总预算；服务`rwkv-lh-continuous-collection-r13.service`。初始admitted156将在批次边界更新，ready已512。详见[R13报告](../data/experiments/RWKV_COLLECTION_R13_20260916/REPORT.zh-CN.md)。**

**R12已完成：512 RL全部留痕，9提交、3原代码验收通过；512/4024生成边界及5 SFT封存后回收，State目录净减少401.80 GiB，撤回R11副本另清理约1.09 GiB。1887回归全绿；GPU0/2新服务实际各3生成后自动退休，两个新blobs目录均0文件。服务端新增64 GiB磁盘保留门。旧R10消费者已停止，不是3万条完成；后续新批使用当前代码重新冻结，默认逐任务退休。强模型/训练0，owner五处修改不变。详情见[R12报告](../data/experiments/RWKV_STATE_LIFECYCLE_R12_20260916/REPORT.zh-CN.md)。**

**R11清理已按owner新指令停止：旧 full-trace runtime 与原 State 保留；eval-results 和 chase/rwkv-skills 在停止指令前已删除。GPU0/2恢复原启动路径及冻结身份，R10采集已续跑（暂停前284条RL留痕，非通过数）；预算/任务不变。详见[R11记录](../data/experiments/RWKV_STORAGE_CLEANUP_R11_20260916/REPORT.zh-CN.md)。**

**R10：owner 明确双卡采集、结束后纠错，并允许 RL Code 补充且与 SFT 分开统计。GPU 0＋2 已运行同权重/同源码身份的独立 Native 副本，GPU 1、3 不动；连续批次消费者已部署，已实证第一批32题结束后自动进入第二批。冻结供给为5个SFT来源AnyIO公开版本功能任务＋512个新RL Code补充题（21批），不是3万题就绪。SFT试采5题均未修改/未提交，61生成重建核验通过；两卡各抽查1条RL轨迹共10边界也通过。模型失败保留原件，不纠错、不训练、不push。最终1876工程回归全绿、0跳过。长跑使用独立冻结源码，状态见 `data/experiments/RWKV_DUAL_COLLECTION_R10_20260916/campaign/STATUS.json`，详细证据见[R10报告](../data/experiments/RWKV_DUAL_COLLECTION_R10_20260916/REPORT.zh-CN.md)。补足SFT可复建来源和剩余3万目标仍未完成；空供给须明确 waiting_for_bound_tasks，不把常驻进程当作采集。**

**R9交付纠正：昨晚仅运行1个Loguru任务，约30.6秒后重复读取中断、0修改/0提交，随后没有后续任务；没有持续采集七小时。69,895条仅是SFT下载/结构审计数量，不是新执行或新训练数据。以下R9的“后台启动”描述保留为历史，不能视为大批部署完成。GPU2遗留Selector已停止；GPU1属rwkv账号的Lightning CUDA 7B服务，chase无停止权限，owner最新要求暂不处理。**

**R9：全7分片完成完整SHA验证和结构审计，共69,895条源记录；curl18两轮失败及Range恢复原始证据保留。全量来源索引完成，仍不能算69,895个可运行环境。新增Loguru Code_Agent_000009公开0.7.0重实例化，真实atexit崩溃复现、普通日志对照通过、57公开测试通过、正式转换准入1题。WSL后台unit `rwkv-lh-coding-collection-r9.service`已实际调用RWKV，24calls/1200s，配置并发4但有效1；会自动封存trace并做隔离代码检查，最终语义验收另列。不是3万题全量采集，未训练/教师/push。Owner最新要求部署验证后停止监测、会后自行检查；不要自动新建监控。状态与用法见[R9报告](../data/experiments/RWKV_COLLECTION_DEPLOY_R9_20260915/REPORT.zh-CN.md)。**

**Owner要求完成测试后后台运行、自行检查：R8已在本地WSL用户systemd启动4路SFT Code完整分片下载与结构审计（固定7分片14.89GB），真实下载已核验；独立冻结审计源码、完整大小/SHA后才审计，最长36小时，不配置Codex监控。当前是来源准备，RWKV执行/训练仍0，不是3万有效任务已经开始；环境复建与任务冻结仍待完成。服务`rwkv-lh-sft-source-r8.service`，状态位于`data/experiments/RWKV_SFT_BACKGROUND_R8_20260915/STATUS.json`，WSL和本机10808代理须保持运行。R7远端GPU0快速推理服务已独立常驻。[后台运行与检查](../data/experiments/RWKV_SFT_BACKGROUND_R8_20260915/REPORT.zh-CN.md)。**

**并发R7已完成：旧服务8/8、修复后8/8、并发负载48/48均忠实完成；仅两个历史检查目标的重复执行，不计3万条或项目Strict。默认服务补上已验证的空GC快速返回，保留8506条历史State；同并发2的两任务平均136.26→13.30秒（10.24倍，工程修复收益）。8任务两遍并发2约47秒、4约44秒、8仍约44秒，同类短任务先显式用4。128/128生成重建通过，零协议/State错误，1870回归全绿。默认GPU0服务及本地模型别名已切到`rwkv7-g1j-13.3b-zero-state-capability-ctx16384-gc-r7`，完整源码manifest核验，旧启动脚本和日志保留。全局请求/生成锁仍限制真实GPU并行，下一轮先请求上下文、State同步和缓存压力回归，再验证安全批处理；SFT环境绑定继续，不用重复题凑数。教师/训练0，未push。[R7完整证据](../data/experiments/RWKV_CONCURRENCY_R7_20260915/REPORT.zh-CN.md)。**

**AnyIO R6：完成公开4.6.0固定版本重实例化和真实试采（不是原采样快照恢复）。任务0/1，提交/工具调用/修改均0；12次协议拒绝中断，481.72秒：1额外字段、1重复正则至1800token、9空围栏、1外来function_call及无依据action_executed。12/12输入/State/快照核验，预览相同；两种Python外部检查均5/7，公开TLS均45/45，缺陷仍在。1870回归全绿，教师/训练0，仅GPU0。下一步按同样绑定方式补不同任务采集失败，再测独立任务并发；不把本题失败当复建失败，也不直接扩3万。详见[R6报告](../data/experiments/RWKV_ANYIO_RECONSTRUCTION_R6_20260915/REPORT.zh-CN.md)。**

**SFT 环境 R5：7 分片前缀及原50行合计115来源UUID（未作任务家族去重），正式环境绑定0。发现9条mini-swe-agent把旧提交/bash作答协议藏在user，R4原文保留会冲突；新增保守拒绝，3回归红→绿，目标不自动删改。106条文本目标可提取不代表环境可用；83条含原工具拒绝Git观察。原生执行/训练0，不能拿未知版本仓库凑3万条。详见[R5报告](../data/experiments/RWKV_SFT_ENVIRONMENT_R5_20260915/REPORT.zh-CN.md)与逐题复建缺项清单。**

R5 最终 1870 全回归通过（独立 basetemp），先前并行测试目录冲突原日志保留。首题 AnyIO 声明版本4.6.0固定 commit 的228行与编辑前观察相等，但观察截断、完整测试未绑定；只列为下一轮候选，不计原环境已复建。

**转换 R4：新增来源→初始工作区→当前生产输入的绑定转换、正式入队身份门和真实边界导出。1867 回归全绿。真实修复任务 0/1、0 修改/0 提交，重复读取预算中断；7/7 输入/State/快照通过，预览与首次真实输入逐 token 相同。50 条现存 SFT Code 目标可提取，但环境绑定仍为 0；未启动 3 万题、纠错或训练。下一步完成可证实的 SFT 仓库复建再做试采/并发测量，不能把结构解析当采集完成。详见 [R4报告](../data/experiments/RWKV_CODING_CONVERSION_R4_20260915/REPORT.zh-CN.md)。**

**owner 最新采集方向：为真实 Coding Agent 准备数据，SFT Code-Agent/项目仓库任务优先；以修复、需求实现、真实测试反馈为核心，代码理解和验证说明服务于编程闭环，泛文档问答不凑 3 万条。两道历史公开检查仅工程冒烟。具体见 [Coding Agent 采集范围](CODING_AGENT_COLLECTION_SCOPE.zh-CN.md)。**


**管线 R3：队列身份/冻结、私有材料隔离、逐题收据和中断恢复、生成前纠正快照、故障停发与只读进度入口已修复；最终 1859 回归全绿。复用历史两题真实冒烟 2/2 忠实完成，4 生成输入/State/观察/快照核验，0 mutation；不计新 3 万题或训练收益。磁盘自动管理按 owner 最新要求暂缓，约三小时人工检查；Native 并发上限和 SFT 复建/3 万题冻结仍待完成。详见 [R3报告](../data/experiments/RWKV_COLLECTION_PIPELINE_FIX_R3_20260915/REPORT.zh-CN.md)。**


**长跑审计 R2：NO-GO。实际复现队列预检查后遗留 running、未决正常退出、payload 摘要未核验、结果身份未绑定、跨题私有参考暴露、坏 SFT 行中断及来源去重缺口。还确认新入口未接生成前纠正快照、远端 State 生命周期/容量及全局故障回压。上一轮 1843 回归不代表 36 小时运行就绪；本轮没有启动模型、训练或修复这些问题。详见 [审计报告](../data/experiments/RWKV_COLLECTION_PIPELINE_AUDIT_R2_20260915/REPORT.zh-CN.md)。**


**当前采集管线 R1：owner 最新要求先做 3 万独立任务真实执行，SFT-Agent 优先、项目来源与 RL 补充；不纠错、不调用强模型、不训练。已实现持久队列、冻结摘要核验、跨批路径预检、生产直接执行入口和流式结构审计；现存 SFT 56 记录/54 来源 ID 已审计，尚未复建计数。大批运行尚未启动，Native 全局请求锁和 State 回收/容量仍需验证。清理 experiments 字节码和可重建重复材料累计 38.8 MiB，原始证据保留；完整回归 1843 passed、0 skipped。详见 [采集管线](COLLECTION_PIPELINE.zh-CN.md) 和 [R1记录](../data/experiments/RWKV_COLLECTION_PIPELINE_R1_20260915/REPORT.zh-CN.md)。**


**最新R6：按owner要求完成同300条一轮训练（75更新、37217目标token），固定12题两遍×三组72任务/342生成。zero A16/24、zero B15/24、一轮候选14/24；历史三轮候选14/24。候选首次真实反馈修复1/8，但新建文件0/2（两次修改受保护测试），协议拒绝13次，NO_KEEP。全部输入/State审计通过、0传输中断，1837回归全绿。清理历史State277.05GiB，根盘约368GiB可用；原服务恢复，未push。详见[一轮训练测试报告](../data/experiments/RWKV_UNIFIED_CORRECTION_TRAIN_R6_ONE_EPOCH_20260915/REPORT.zh-CN.md)。以下R5及“当前下一步”为历史状态；下一步以R6报告为准，补其他真实任务的需求→实现/失败反馈/保留测试/忠实收尾纠正，不训练这12题及其衍生内容。**

**当前：统一StateTune R5已完成300条、3 epochs、225更新，候选加载校验通过。完整新12题×两遍×三组重测：zero A/B各15/24，候选14/24，NO_KEEP；未切换生产State。72任务/384生成输入与State谱系审计通过，0服务中断。已有代码修复三组均0/8，新建函数产物均2/2通过，但候选一次循环至预算耗尽无最终说明。首轮磁盘满的46次中断保留，不合并评分。已清理旧State及其他项目备份，详情见[本轮最终报告](../data/experiments/RWKV_UNIFIED_CORRECTION_TRAIN_R5_300_20260915/REPORT.zh-CN.md)。**

**已完成数据阶段：统一StateTune v6正式300条（新增150，旧150逐字节保持）；新28写入/修复、24命令、30回答、68读取。78真实任务/183生成：公开检查25/25，代码解释质量分层，自主修复0/3；28离线教师纠正写入均真实验证，其中1条在失败测试观察之后。1833回归通过、0跳过；训练0、仅GPU0、原服务恢复、owner修改保留、未push。详见[300条阶段报告](../data/experiments/RWKV_UNIFIED_300_EXPANSION_R1_20260915/REPORT.zh-CN.md)。**

## 当前下一步

R5不保留为生产默认，训练候选与失败轨迹留作诊断。优先从其他新的生产任务补“修复实现/失败反馈补全/检查通过后诚实收尾”的统一纠正，当前12道固定测试及衍生纠正继续不入训。下一轮训练需先按已获授权范围核对来源、覆盖和预算，不因单次失败再加角色或立即重训。本轮数据v6仍为300条；1837工程回归全绿。账号旧缓存/备份及结束评测缓存共清理131.79 GiB逻辑量，根盘约89 GiB可用，原服务已恢复。以下是历史记录，旧数量和进行中描述不代表当前状态。

## owner授权Codex纠错与扩量（历史数据阶段）

53个新任务全部完成，原始轨迹逐运行分类；25题纠正写入正式纳入统一v4，3份命令纠正仍待原审核门。5个不支持exact判题的来源隔离，26新题待教师纠正，队列位于RWKV_ULTRADATA_COLLECTION_R3_20260915/CONTINUATION_QUEUE.json。此前“运行中”状态已结束，原服务恢复空闲。

## 09:50续进：强模型恢复与真实接管

小生成2/2正常后，长审核有效1/4（两份引文锚点失败、一次连接重置），候选仍未入训。原UTC偏移任务接管恢复：strong实际测试红→修改→测试绿，隔离原测试/CLI均通过，代码修复1/1；最终说明误列两个原本已拒绝的偏移值，完整忠实交付0/1。4请求、69225输入/747输出token，归属strong_takeover。没有新增数据版本或训练；详见RWKV_POST_COMMAND_ANSWER_REVIEW_R1_20260915和RWKV_BOUNDED_CODE_RECOVERY_R5_20260915。

## 参考范围与持续数据（owner最新）

rwkvrag仅参考总结文档的方法；StateTune重点参考Lightning CUDA、Preen、RWKV-APP/statetuning。此前NeoHorse的学生轨迹教师纠正思路落实到可复核持续队列，最近5运行/12边界登记，新准入0，正式数据仍60。此队列是库存快照，未宣称自动采集调度已上线。见RWKV_CONTINUOUS_CORRECTION_QUEUE_R1_20260915。

## RWKV-PEFT训练项目（owner提醒）

近期训练实际使用LH Native，不是PEFT/train.py；不能混称。PEFT本地工作树9文件修改已保留，当前60条token/label通过binidx往返，61层State导出相等，optimizer0。文本入口追加EOT/截断、L2Wrap及G1J递归/梯度需对齐后再登记正式PEFT训练。详见RWKV_PEFT_TRAINING_CONTRACT_R1_20260915。三个社区项目为参考，持续纠正数据主线不取消。

## 最新审核接口修复

按owner要求已删除训练器比较/选择文档与对应交接结论。审核单层JSON证据解码已修复并保留原始字节定位，红→绿与1806完整回归通过；原始输入/候选不改，不拼接、不递归解码、不引入未来证据。新R3审核1/4有效，混合转义和多加引号仍拒绝，未重算旧分数或新增训练数据。见RWKV_REVIEW_EVIDENCE_BINDING_R1_20260915。

## 外部数据与第一版独立执行（owner最新）

优先利用UltraData-RL Code题目/测试构建真实RWKV采集任务，SFT-Agent作为可复建任务及行为覆盖来源，不直接伪装原生State trace。已重新读取50条Code轨迹、复核6条RL样本；Tool-Use接口500。下一步先20独立任务低成本试采，再扩100，首批强调用预算0，统一State而非按问题拆分。正式数据仍60；详见RWKV_ULTRADATA_EXPANSION_R1_20260915/PLAN.zh-CN.md。

## 产品与当前入口

目标：为RWKV构建专属Harness和Code Agent；同质量下的成本、速度与吞吐是优化指标。当前架构只从[ARCHITECTURE](ARCHITECTURE.zh-CN.md)进入，历史设计不再作为互相竞争的产品入口说明。

当前执行是RWKV直接选择工具/参数→真实Harness→观察及连续State→原始交付→外部验收。默认不调用Planner/Selector/Auditor链。历史多角色构造仍有研究代码及测试依赖，尚未物理删除；不能声称已全部清理。

推荐统一入口：`scripts/run_rwkv_agent.py --jobs /absolute/jobs.json --concurrency 2`。格式见[批量使用说明](AGENT_BATCH.zh-CN.md)。原单任务修改、只读CLI及既有前端共享底层执行；本轮不改页面。

## 正在交付的阶段

独立任务交付与协作阶段已经开始：读取/检查/修改共用批量调度器，全批预算和路径预检查、spawn进程隔离、原结果返回、普通任务启动错误单列。修改任务复制源目录，不自动集成共享文件。任务独立性由目标和依赖决定，不由程序替用户拆分。

前轮并发小批2/2满足事前登记任务要求、2提交、mutation0：读健康检查脚本准确说明范围；递归扫描测试真实运行并如实报告通过。共4真实生成、11936逻辑输入/396输出token，输入和State父链核验。这是集成smoke，不是项目Strict、并发收益或通用修改能力。

工程红→绿及完整验证见[本轮报告](../data/experiments/RWKV_AGENT_ARCHITECTURE_BATCH_R1_20260914/REPORT.zh-CN.md)。已有owner五处修改必须继续保留：controller.py、model.py、supervisor_openai.py、test_hybrid_supervisor.py、test_supervisor_openai.py。未混入本轮代码提交。

前轮真实失败恢复：同一查询问题的两个失败父运行，建议后RWKV 0/2，强模型显式接管2/2；后者均真实修改并测试，外部原测试通过。建议续跑仅1/2次生成即再次触发历史重复保护，不能宣称建议无效或RWKV独立能力提升。完整记录见下方恢复阶段。

本轮完整目标入口：显式on_stall=takeover后RWKV先执行，停滞时按剩余预算最多接管一次。固定三任务3/3交付：RWKV独立2、接管1。查询RWKV用12次后重复保护中断，strong用3次修改并测试；不是RWKV独立修复已稳定。完整1650测试通过。

最新单处修改验证0/2：RWKV分别7/11次生成后重复读取中断，未修改、未回答。任务仍包含自行判断修法，不能据此否定真正单步执行；下一步分离诊断与明确操作执行。已清理101个有核验存档的temp/data重复文件，生产架构未改。

最新明确方案执行0/2：两遍write_file成功但内容未变，一遍无回答、一遍虚称改好且正确说未运行测试。已补M10/M11缺陷记录；下一步统一审核纠正来源，不再扩架构。temp约1.5GB→285MB，删除2参考副本、68重复脚本、458旧一次性脚本及11字节码，清理后1650测试全绿。

最新离线来源阶段：编码 trace 重放误用只读 Harness 已定位并最小修复；新增真实失败轨迹回归，原答案不改。1万条仍仅计划，未训练或新建数据版本。[缺陷归并与下一阶段](DEFECT_GROUPING_AND_NEXT_STAGE.zh-CN.md)明确模型、工程、评分与假设的边界。

工程优先整改：停止继续检查真实trace或调用RWKV。已复现并整改Goal强制Final、生成配对审计、准备预算、进程池结果丢失及旧只读建议顺序；补协助进程组清理、只读快照减负和显式coding依赖/保守集成。[工程报告](../data/experiments/RWKV_ENGINEERING_FIXES_R1_20260914/REPORT.zh-CN.md)保存红绿和完整回归结果。1万条仍仅计划。

工作区与恢复补查已完成本轮实现：复制前后身份核对、目录/权限变化记录、目录移动集成、缺树身份与不支持变化拒绝、旧只读恢复父trace校验。新增7项回归，显式GPU 0完整测试1678 passed（327.08s），未运行新Agent验收。[本轮报告](../data/experiments/RWKV_WORKSPACE_RECOVERY_R1_20260914/REPORT.zh-CN.md)列出证据和剩余边界；下一步是编码纠正候选准入与资源计账，工程问题未全部关闭。

最新完成离线原子编码纠正候选验证与用量账本：[调用说明](EVIDENCE_AUDIT.zh-CN.md)。真实原无效写入仍被拒绝；修复replay_run重复生成请求被覆盖的问题。供应商重试、未知usage、逻辑token与费用分开；原生GPU总成本仍未知。训练freeze未增加编码标签、未建数据版本或训练，不能把候选验证算已准入样本。[本轮记录](../data/experiments/RWKV_CORRECTION_USAGE_R1_20260914/REPORT.zh-CN.md)。

本轮GPU 0完整回归1700 passed、0 skipped（327.49s），新增22项；原owner五处修改保留，未计入本轮提交。没有新模型验收成绩。

Owner补充StateTune社区证据：约3000条数据的G1J 7B Three.js展示改善，当前只作外部复现线索。明确zero低分不是训练禁令；训练门槛是来源/纠正可信、协议State身份、隔离回归及授权预算，不等所有工程增强完成。下一步盘点获准真实来源与可验证纠正、覆盖缺口，推进统一多缺陷训练准备。

已查看Lightning CUDA、Preen及RWKV-APP State-Tuning Studio的文档/源码，[参考核对与下一阶段](../data/experiments/RWKV_STATETUNE_REFERENCES_R1_20260914/REPORT.zh-CN.md)。Lightning作为候选训练/推理后端，Preen借鉴mask/导出验证，Studio借鉴run管理。外部训练text格式、截断和State轴语义不可直接混入当前链路；先做有界兼容验证，数据准备主线继续，不等待换后端才训练。未构建或启动外部训练/UI。

最新完成真实失败纠正试点：[记录](../data/experiments/RWKV_VERIFIED_CORRECTIONS_R1_20260914/REPORT.zh-CN.md)。初始强接管目标1/3（提交1），关闭thinking的独立恢复目标1/2（提交2、修改1）；均不算RWKV独立或Strict。数字纠正1条复核通过，API无依据细节被人工拒绝，编码原样修改独立红→绿但审核分歧/家族切分待解，正式准入0。双API审核也出现漏错/误拒，旧票原样保留，不通过反复审核凑通过。GPU 0完整回归1700 passed、0 skipped（329.55s）。共19次供应商请求、121514/10905输入/输出token，成本未知；未训练/建版本/push。下一步先补审核证据规则回归和来源切分，再扩优质真实来源；1万条不再作为首批最低门槛。

最新审核与来源阶段：[R2记录](../data/experiments/RWKV_CORRECTION_REVIEW_R2_20260914/REPORT.zh-CN.md)。旧审核3/6、新审核4/6，API仍被语义漏判，新6/6门未达；不宣称E13解决。已增加离线原样候选/引用绑定回归，不接入逐步执行审核。编码来源确认RP-MAINT-02→MAINT/train，14条相关已知运行不是独立来源；原样补丁经既有验证器红→绿。现有正式库存128条（28读取/100回答、28来源ID/52生成边界、CLI/FULL/MAINT/RAG四家族），协议/SHA核验通过但未完成新语义审核。下一步优先复核这128条而非重复造样本，再补编码freeze及有来源的覆盖缺口。新增正式准入0，GPU0完整回归1710 passed、0 skipped（319.50s），未训练/建版本/push。

## 能力和限制

- 固定单步读取、部分文档总结及明确测试执行已有成功证据。
- 自主多步修复尚未稳定：会重复读取、读不存在路径、不选择修改/测试、无回答终止。不能由此推断不会简单总结。
- 改恢复句及精简菜单未改善固定修复任务，候选不保留；局部定位实验到此收束，不再继续无方向微调。
- State传递和真实观察已多轮核验，未发现可解释上述停滞的遗漏；不等于证明数值State及长上下文利用没有问题。
- 强模型建议/显式接管已接入统一任务入口，归属分开；不增加逐步审核关卡；可显式开启无交付预算停滞的有界接管，尚无语义自动求助。当前轮工程和真实验证结果见协助阶段报告。
- 已增加显式coding依赖与同基线不冲突文件集成；冲突、不同基线和纯权限/空目录变化不自动合并。语义冲突解决与前端续跑仍未完成。

## 后续顺序

1. 优先验证owner提出的原子任务与“RWKV完成当前小任务后提出下一步”：先测局部交付和建议，再测依赖衔接；不预设强模型规划所有小任务。当前整目标基线和新对照分别冻结，建议与已执行事实分开。
2. 增加有依赖任务的结果集成与最终验收，再测同质量下端到端成本/延迟/吞吐，不提前宣称并发优势成立。
3. Owner已提出之后统一约10000条多缺陷StateTune数据目标。按[缺陷台账](DEFECT_REGISTER.zh-CN.md)与[1万条计划](STATETUNE_10000_PLAN.zh-CN.md)先审核来源/纠正与覆盖，再分批生成；当前未建数据版本或训练，不把强模型成果算RWKV独立能力。

## 必须保留的约束

Owner最新要求：只使用物理GPU 0。后续本地测试及模型进程显式设置`CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0`；远端启动同样限定目标主机GPU 0，不改动无关进程。

遵守AGENTS。所有命令在WSL；服务器禁止Git；不读最终holdout/acceptance目录。不改前端或可视化；本轮不push、不训练、不新建dataset版本。以后授权按具体范围判断。模型输入只走现有唯一构造函数，程序不代选业务动作、补参数或改答案。

预算耗尽/中断不是合格完成，final_answer不是通过隐藏评分；外部验收按目标和真实交付、不限定实现路径。完整逻辑token不是实际费用。生产变更需先失败后通过回归、完整测试后本地一轮一提交。

## 最近证据索引

|记录|作用|
|---|---|
|[明确操作与统一缺陷](../data/experiments/RWKV_EXPLICIT_EDIT_R1_20260914/REPORT.zh-CN.md)|0/2、无效写入及错误修改声明；temp大幅清理、18项台账和1万条计划|
|[单处修改与清理](../data/experiments/RWKV_ATOMIC_CHANGE_R1_20260914/REPORT.zh-CN.md)|0/2，保留失败；清理46脚本与55验证副本|
|[完整目标阶段](../data/experiments/RWKV_GOAL_DELIVERY_R1_20260914/REPORT.zh-CN.md)|固定3/3：RWKV独立2、接管1；RWKV24/总32额度，实际停滞如实保留|
|[失败恢复阶段](../data/experiments/RWKV_ASSISTED_RECOVERY_R1_20260914/REPORT.zh-CN.md)|建议0/2、接管2/2；一个固定问题，未改变生产源码|
|[显式协助阶段](../data/experiments/RWKV_ASSISTED_AGENT_R1_20260914/REPORT.zh-CN.md)|清理旧入口、建议续State与接管新文本根、回归及真实验证|
|[架构与批量阶段](../data/experiments/RWKV_AGENT_ARCHITECTURE_BATCH_R1_20260914/REPORT.zh-CN.md)|当前代码与入口、回归及并发smoke|
|[菜单定位](../data/experiments/RWKV_MENU_LOCALIZATION_R1_20260914/REPORT.zh-CN.md)|19→5菜单两组均0/2，不保留候选|
|[恢复说明对照](../data/experiments/RWKV_REJECTION_RECOVERY_AB_R1_20260914/REPORT.zh-CN.md)|同父State两组均0/2|
|[自主修复验证](../data/experiments/RWKV_QUERY_REPAIR_FEEDBACK_R1_20260914/REPORT.zh-CN.md)|未推进至修改与测试反馈|
|[诊断材料](../data/experiments/RWKV_EVIDENCE_BUG_DIAGNOSIS_R1_20260914/REPORT.zh-CN.md)|根因定位2/2、修复建议0/2，不能合并归因|
|[前端演示](../data/experiments/RWKV_FRONTEND_DIRECT_R1_20260914/REPORT.zh-CN.md)|固定串行演示4/4，非通用能力|
|[飞行轮](../data/experiments/RWKV_FLIGHT_CAMPAIGN_R1_20260913/REPORT.zh-CN.md)|strong归属、续跑、历史失败与限制|

更早结果以各实验原报告及Git历史为准，不把旧分数重算成新收益。StateTune管线见[现状](STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md)，本交接不新增训练授权。


最新R3已完成128条结构复核和100条回答人工语义审核：98回答保留、2歧义隔离；28读取+24回答代表形成52行引用建议，未改旧数据/评分。历史同批已训练384步并因验收退化NO_KEEP，不盲目重训。GPU0完整回归1710 passed（321.23s）。[完整记录](../data/experiments/RWKV_EXISTING_DATA_AUDIT_R3_20260914/REPORT.zh-CN.md)。Owner随后明确授权离线期间继续推进，按[下一轮范围与预算](../data/experiments/RWKV_EXISTING_DATA_AUDIT_R3_20260914/NEXT_AUTHORIZATION.zh-CN.md)先补编码freeze及训练一致性验证，再有条件冻结新数据/训练；此前“本轮不训练”只描述已完成审计轮。


编码freeze增量已实现：verified_coding原子编辑经封存报告绑定与fresh红绿验证后进入统一freeze，训练加载校验编码证明SHA；真实旧候选原样复验证exit 1→0，非RWKV新成绩。正式数据版本/新训练仍0。下一步补多来源修改与测试反馈，再按已获授权冻结一个GPU0训练候选；旧GPU1训练脚本不可直接复用。[本轮记录](../data/experiments/RWKV_CODING_FREEZE_R1_20260914/REPORT.zh-CN.md)。

编码freeze最终回归：GPU0 1725 passed、0 skipped（318.89s），新增15项；原样真实候选在补全源快照逐文件清单后再次红→绿。两次中间测试干扰/源码变化拒绝日志保留，未放宽回归。owner五处修改SHA不变。当前仍无新Agent能力分数、新训练步数或新正式数据版本；授权已记录，下一步针对“读过但不选择修改/测试”的真实边界补纠正和反馈覆盖，然后统一冻结训练与验收，不能直接复用旧GPU1启动身份。


PROGRESS_CORRECTIONS R1：两个真实停滞边界的强模型原样下一步均为实际测试，复现ValueError（exit1），不是修复完成。新增verified_command按源request/action/快照绑定、fresh执行及固定退出/输出准入，失败测试可监督有效诊断。完整GPU0 1735 passed（323.77s）。Owner再次要求持续做到训练和真实Code Agent，不再按小阶段停下。54条统一数据已冻结，最长20551tokens；下一轮GPU0长输入训练验证、一个候选和固定验收正在推进。详情见data/experiments/RWKV_PROGRESS_CORRECTIONS_R1_20260914/REPORT.zh-CN.md。

统一纠正训练 R1 已启动（2026-09-14 20:09 CST，尚未验收）：获准新数据 `rwkv_direct_unified_corrections_v1` 共54行，manifest SHA `9ae25e11095dbe869ac54b8bdffdda8b7141b5a964c4c5f8b350494745b2a696`。28读取、24回答代表、1有效修改、1实际失败测试；两条编码相关边界同属一个见过的MAINT问题。原128行及旧NO_KEEP不变。16K工件拒绝32K、32K反向超过80GiB预算，均0 optimizer steps；改为完整容纳20551-token样本的24576窗口后，数值/梯度/State/隔离全部通过，峰值75.691GiB，未截断或放宽门槛。模型/权重未改。GPU0运行 `direct-unified-r1-20260914`，zero初始化、lr1e-4、3epochs计划162步、上限400步/4小时；注册SHA `3669ca64f4b54571ac80d418c6f625113ce173c0b5c25719683ab0b7329a293c`。完整证据位于 `data/experiments/RWKV_UNIFIED_CORRECTION_TRAIN_R1_20260914/`。任务评分在训练前冻结，固定zero/candidate摘要、诊断、读取与编码两遍比较；不因loss下降保留State。原GPU0项目服务已在确认空闲后临时暂停，独占训练/评测结束必须恢复 `rwkv-lh-native-current.service`；其他服务不动，服务器不使用Git。Owner五处修改SHA仍不变，生产源码冻结于650800e1加这些原有修改，完整测试1735 passed。


统一纠正训练 R1 已完成并判 NO_KEEP：162实际训练步、54完整样本、24.2分钟；同源固定两遍摘要 zero7/8、candidate8/8，诊断均0/6，coding均4/6（查询修复均0/2），原读取均24/24。候选协议拒绝12次，不替换默认State，不运行confirmation/holdout。原GPU0服务已恢复并健康核验。报告见 `data/experiments/RWKV_UNIFIED_CORRECTION_TRAIN_R1_20260914/REPORT.zh-CN.md`。下一轮先修四个产品入口覆盖显式State的问题（4红/4默认通过已复现），再补独立训练来源的真实纠正；不将开发题参考答案训练化。


State入口整改已完成：四产品入口统一保留显式profile，缺省仍zero，非法身份拒绝。红4/默认通过4，完整GPU0回归1747 passed、0 skipped（329.02s）。训练R1候选仍NO_KEEP。下一轮已冻结并采集两个获准MAINT来源的事实/局部修复任务，目标是获取真实失败纠正，不读API dev答案或confirmation入训。报告 `data/experiments/RWKV_PROFILE_ENTRYPOINT_FIX_R1_20260914/REPORT.zh-CN.md`。


生成边界纠正证据已补齐（RWKV_GENERATION_CORRECTION_SNAPSHOT_R1_20260914）：显式采集在真实generation_started前封存工作区并绑定父State/request，可验证非法原调用对应的编辑/测试纠正。默认生产不加快照，不代选动作；历史缺失快照不补造。GPU0完整1756 passed（325.23s），新增9项。R2四个局部coding任务正在独立State/副本下以并发2采集，尚无新增正式样本。计时另发现非生成State RPC的高耗时，下一步有界核对GC空队列扫描历史State路径，未归因为模型推理。


GC 空队列性能根因已修复：旧服务8409历史State时每次空GC仍全表解码核验，实测8–9秒；新逻辑无待回收键直接返回，非空安全检查保留。红→绿及GPU0全套1758 passed。独立新服务真实CLI脚本任务1/1、2生成、零非法调用、无修改、8.54秒；不是项目Strict/训练收益。原服务不动，新服务29621只用GPU0/zero。详见 data/experiments/RWKV_NATIVE_GC_EMPTY_QUEUE_R1_20260914/REPORT.zh-CN.md。四个已有局部修复目标正以24 calls/600s和24K窗口重新采集，条件不同不直接称对照收益。


优质纠正采集已封存：GC修复后四局部修复0/4，完整51生成仍重复读取，无修改；两个强修复后的工作区验证任务也未独立验证完成。2条强模型原样编辑红→绿，加1条实际失败测试命令，经两审核及fresh执行后在新v2冻结，共57行，最长24455/24576tokens。文本歧义及错审候选未准入，人工误称sqlite_io.py不存在的错误已留痕纠正。详情 RWKV_FOCUSED_CORRECTION_CAMPAIGN_R1_20260914。训练R2从zero计划342步（6epochs，上限400步/4h/80GiB）正在GPU0执行，结果未知；原门槛不变。复用字节相同数值训练源码及24K兼容证明，生产评测用GC修复源码，唯一model_io相同。训练退出自动恢复原服务，GC侧服务暂停待评测后按原launch重建；不要对已停止的transient unit直接start。启动SSH引号错误0步已保留。所有固定评测两臂重新运行，尚不读confirmation/holdout、不push。详见 RWKV_UNIFIED_CORRECTION_TRAIN_R2_20260914/PREPARATION_SHA256.json。


E12已在训练R2失败、未进入对比后统一修复：status只表示本次终止交付，durable State另存state_status；异常不再显示running。RWKV/strong两种异常红→绿，45项针对性、GPU0完整1763 passed（329.47s），不改模型输入/最终回答/State。数值复现仍在GPU0运行，最多84额外实际步，原服务退出自动恢复。

## 训练失败观测 R1（2026-09-14）

梯度门新增具体参数、当组样本/loss记录；失败保存原精度State诊断快照，不发布profile、不含optimizer恢复状态。[证据](../data/experiments/RWKV_TRAINING_FAILURE_OBSERVABILITY_R1_20260914/REPORT.zh-CN.md)。三个新增回归红→绿，完整1766 passed、0 skipped。数值异常未标解决；首个诊断重放在83步保存目录缺失失败，原结果保留；修正目录后第二个独立诊断仍用原冻结远端数值源码，最多84步。全部实际更新分别计账。

## CLI创建与输出预算（2026-09-15）

已有两个CLI任务采集0/2、0提交、0修改，28次生成均完整可重放；备份4次/时间记录11次长度截断，各12次协议拒绝后中断。模型已选择write_file，不能统称不会修改。原结果位于RWKV_CLI_ATOMIC_CREATION_R1_20260914。动作输出预算现可显式配置，默认仍1800，[工程证据](../data/experiments/RWKV_ACTION_OUTPUT_BUDGET_CONFIG_R1_20260915/REPORT.zh-CN.md)，完整1769 passed、0 skipped。1800/8192同任务两遍对照脚本已准备，尚未运行。统一训练R3的数值兼容验证仍使用此前冻结的b3702451源码，预算配置变化不混入该轮训练。
