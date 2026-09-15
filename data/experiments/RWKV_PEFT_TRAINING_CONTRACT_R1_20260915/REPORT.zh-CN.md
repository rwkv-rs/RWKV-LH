# RWKV-PEFT训练接口核对 R1

本轮没有Agent任务/角色能力结果，optimizer steps=0。Owner提醒RWKV-PEFT为训练项目，因此先明确事实：最近统一R1–R4实际调用RWKV-LH Native训练器，并非RWKV-PEFT/train.py；PEFT格式兼容不等于PEFT后端已经运行。训练项目应纳入正式接入核对，三个社区项目继续提供参考，不增加三套在线架构。

本地RWKV-PEFT HEAD 5704c39f8ab1d2ac63936ab392aadb6ba526e1a5，存在9个未提交文件修改；逐文件身份与diff统计见REGISTRATION，全部只读保留，没有覆盖或提交其修改。

CPU实际验证：当前60行冻结数据经唯一collate_samples产生输入/监督label，转换为PEFT原生binidx后由其MMapIndexedDataset读回，60/60逐token及label相等，共13943监督token。没有重新分词、额外EOT或截断，不是新数据版本。已有R4候选61层BF16 [64,64,64] State经PEFT校验及vllm_state_dict导出，每层torch.equal，原文件SHA不变。这仅验证文件容器/数据传输，尚未验证PEFT全Dataset/collator、G1J前向、梯度、optimizer或服务端logits。

需要处理的差异：

1. PEFT文本AgentSFTDataset会追加换行/EOT，并进行目标或prompt截断；不能直接喂当前精确协议文本。优先核对已有agent_sft_binidx入口，保留原token/监督边界与停止符。
2. PEFT训练代码包含L2Wrap路径；当前Native只对目标token做交叉熵，无prompt/pad直接正则梯度。下一步冻结具体训练分支并检查其真实loss/gradient，而不是默认等价或未经测量直接关闭。
3. State轴语义由当前训练和服务实现决定。容器相等不证明递归计算等价；需要非对称State、相同token的zero/非zero前向、续接和梯度验证。
4. 只训练time_state、底模冻结、独立样本State重置与连续任务State关系必须真实检查。旧默认脚本模型为其他版本，不能拿旧G1i配置启动当前G1J。

下一步：以该工作树内容生成完整源码manifest，明确当前G1J模型/词表、算子与mask合同；按必要差异做最小适配，每个修复先红后绿。先有界数值验证，再登记正式统一State训练预算。后端接入与新纠正数据覆盖分别记录，不把更换训练器和数据收益混在同一次不受控对照里。训练仍仅GPU0，不push，不引入前端。

持续数据主线不取消：实际RWKV边界→教师纠正→真实执行与语义审核→来源去重/冻结→统一State训练。当前正式60行、待审材料未自动准入；不要求RWKV先独立完成所有目标才能训练。
