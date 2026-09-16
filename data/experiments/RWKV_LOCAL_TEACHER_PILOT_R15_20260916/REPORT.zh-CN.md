# R15 本地教师纠错试验：部署与固定组

## 任务级状态

R13新增512条采集结束，15提交、5产物通过、56任务有修改、4078生成；512条trace完整、512条State退休成功。R10＋R13累计1024条RL、24提交、8产物通过；SFT 5条另计。全部任务原始结果保留，不称为项目Strict或1024条合格训练数据。两个采集服务已停止，结束后的两个新blobs目录文件数0。

20个真实失败任务按来源ID确定选择，8协议失败、8重复读取、4失败提交。20/20原始产物失败已用原私有检查复现。协议组完整trace可见unknown read_text及孤立围栏；重复读取组已完整得到TASK但未推进实现。两份失败提交将空输出且无stdin的命令误称样例验证成功；其余失败提交不自动归为虚构完成。详见TASK_SELECTION.json、sources/*/SOURCE_AUDIT.json、SOURCE_BASELINES.json。

## 本轮执行与判定

第一份纠正从原错误发生前的输入/工作区快照分支。调用已有replay_run生产输入重建与validate_generation_snapshot；无未来工具观察或私有验收注入。首次StrongCompletion收到的内容必须逐字匹配原重建input_text；已有Probe验证通过。Qwen采用自己的chat模板和tokenizer，无RWKV State张量移植。首次输出是局部纠正候选，后续通过原Controller/Harness实际执行，归属strong_takeover；历史文本保存但不伪造完整旧控制状态或旧工具是教师所执行。

原StrongCompletion/监督传输使用JSON mode，因此本轮协议合法率是受约束解码条件下的指标，不拿它与RWKV无约束输出做能力等价比较。不规定工具顺序，不替模型写参数、代码或最终答案。真实prompt_token_ids、输出token_ids与服务usage逐调用核对，缺失或不一致停发。原生成的数字token ID不得用于Qwen。

固定20题、每题12生成/1200秒、每次输出8192token、上下文32768，并发1；原私有stdio验收保持，完成后另做事实和最终声明人工核对。扩大试采门为至少16/20合格且零关键无依据事实/虚构测试。JSON合法和产物通过分别统计。无答案提交/预算耗尽如实报告；原错误与失败候选保留。所有training_admitted仍false，未训练，不新建datasets版本。

## 部署身份与后台入口

模型Qwen/Qwen3-Coder-Next-FP8，revision da6e2ed27304dd39abadd9c82ef50e8de67bdd4c；官方文件列表约80.4GB，40权重分片。来源官方API固定，mirror仅作传输，LFS逐文件SHA核验。独立vLLM0.29.0、Torch2.13.0+cu130，已检查CUDA可用；源码4904文件清单在本地生成后上传，启动校验，不在服务器调用Git。模型不重复放入另一缓存目录。

GPU0＋3，TP2、eager、max_num_seqs4；调度首轮并发1。无NVLink，不能预设四卡并发收益。GPU1/2任务此前已自行结束，本轮未停止entropy。启动服务等待模型完整manifest，再全文件校验并启动。启动脚本/下载脚本位于本地temp及远端独立runtime，未改生产推理代码。

远端：rwkv-lh-teacher-download-r15.service、rwkv-lh-teacher-r15.service；本地：rwkv-lh-teacher-tunnel-r15.service、rwkv-lh-teacher-pilot-r15.service。唯一最新状态看STATUS.json：waiting_for_verified_model_service不是纠错已执行，correcting才开始真实任务，execution_complete_pending_semantic_review也不等于已验收合格。模型就绪等待上限2小时，工程异常停止，禁止静默重试改答案。

本轮无生产代码修复；复用R12相同生产源码的1887全回归记录，另有本轮真实失败复现及首输入交接Probe。不覆盖owner五处修改，不push。正式冻结前补齐转换item/私有acceptance的SHA绑定，保留先前登记REGISTRATION_PRE_ACCEPTANCE_PIN.json；补充时尚无教师调用。

## 实际启动补充

权重40分片及启动前完整SHA核验完成。首次默认custom all-reduce在加载/DeepGEMM预热后持续占满两卡而API未就绪；保留DEPLOYMENT_ATTEMPT1.txt，并停止无任务的挂起服务。第二次仅增加--disable-custom-all-reduce，模型/源码/题目/精度/采样/预算不变，API与真实生成均成功。这是本机可用的配置规避，未宣称通信根因已完全证明或所有拓扑已修复。调整发生在第一次教师调用前，旧登记保留。

20:09已进入真实纠错，首题先合法读取，再真实写入solution.py，并继续检查。token ID与服务usage核验已通过，尚待任务结束和语义验收。当前仍无正式训练数据准入。具体后续进度以STATUS.json与runs/*/DELIVERY.json为准。

早期快照：前2题产物0/2，一题12调用预算耗尽且未最终提交，另一题2调用后仅承诺将实现而未交付。结果不回写原RWKV评分，固定组继续。现有StrongCompletion以system承载生产输入、user为{}，可能影响本地模型执行意图；这是待对照的输入封装假设，不凭前2题认定模型无能力或立即改输入。原组完成后才讨论新对照，当前不改评分/解析/停止边界。
