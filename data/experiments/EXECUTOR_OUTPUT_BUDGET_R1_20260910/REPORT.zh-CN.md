# Executor输出预算单变量轮 R1

| 臂 | Strict | completed | mutation | 动作 | Executor返回 | length | 时间秒 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline1800 | 0/2 | 0/2 | 0 | 4 | 4 | 0 | 432.46 |
| candidate3600 | 0/2 | 0/2 | 0 | 2 | 14 | 10 | 1100.54 |

两臂完整保留同两道题的原始结果，生产文件manifest、实验driver、模型/zero State与采样一致；两臂之间只改变next_command的max_output_tokens，未修改生产代码、题目、parser、评分或停止边界。记录提交使Git HEAD不同，不改变冻结源码文件身份。两题小样本不能推导超越Agent噪声带的改善。

结论 **NO_KEEP**。预注册要求baseline length>0、candidate length次数至少减半且比例下降、Strict不劣化、运行完整无不可用服务；本次baseline length=0，candidate=10，不满足必要条件。逐项判定见COMPARISON.json；不能据此证明加倍预算有效，也不把不同计划/模型随机轨迹下的变化单独归因为预算。生产默认Executor仍1800。

基线WEB-02在Planner阶段失败：HTTP200、finish_reason=stop、最终content为空，输出8496token全部计入reasoning；未进入RWKV。这是服务响应合同失败，不是余额402或Native传输死链。COMPARISON中的no_infrastructure_failures是涵盖Supervisor不可用的保守可比性检查，本次具体类型以原始SupervisorProtocolError为准，不将其误称网络故障。基线没有Executor截断本身已足以令KEEP失败。没有为改善结论补跑失败题。

候选WEB-02的自然stop后无效JSON与length分别保留，不混为同一种错误；每次生成含retry均计数。raw output token计量见TOKEN_EVIDENCE.json，Native未提供usage对象，因此COMPARISON空usage字典不是零资源消耗。实际耗时记录在各臂COMPLETION.json。采集轮新发现的WEB-01截断未被事后加入本轮题集。

默认预算未改，optimizer steps=0；这不是StateTune。相关工程源码已在WSL完整tests/1455 passed、0failed/0skipped，之后未变。未读Real Agent Holdout V2，也没有把私有开发验收内容送入Agent。
