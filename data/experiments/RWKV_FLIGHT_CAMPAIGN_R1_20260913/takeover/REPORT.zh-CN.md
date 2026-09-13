# 显式强模型接管固定诊断

任务级：有效接管 0/1 合格、1 部分满足。completed 0；一次命令修改两个文件；终止为 transition_budget_exhausted，无最终回答、虚假完成 0。不是项目 Strict，也不是 RWKV 独立完成。另一次实验初始化错误（未注册因果事件）在生成前失败，0 HTTP，保留为 invalid；修正为既有 action_session_started 事件后按相同冻结条件重跑。

strong 自主选 run_command、参数及补丁，修复了 CLI 参数定义/调用连接，并选择 cwd='.'，真正运行已有测试。但默认查询改成 fetchmany(-1)，真实运行环境报 ValueError，固定外部验收也失败。外层 Python 命令返回 0，只表示包裹脚本正常结束；内层 unittest 明确 FAILED、RC=1。该工具 success=true 不能当测试通过。

第一次 strong 返回 length，1800 个 completion token 全部为 provider reasoning，可见内容为空；生产 parser 如实拒绝。第二次返回真实工具调用，随后耗尽两次调用预算。最后测试结果持久化但没有第三次生成消费，不能说 strong 看见失败后仍不修复。没有自动补写答案或追加调用追分。此小预算接管不能证明强模型普遍不能修复，也不支持同预算能力比较。

沿用相同用户目标、文件、真实父历史与行为/验证/如实说明标准；不进入隐藏测试或参考实现。strong 从可重建的原生产文本建立新 prompt_replay 根，明确标记接管，不移植 RWKV 数值 State。两次实际 wire input、原始 output、模型身份、新根父子关系核验通过。工具参数/最终文件都是模型原样产物，没有程序纠正。

新增共享入口显式 execution_authority，默认 RWKV；接管可记录 strong_takeover 与 execution_model，未知值在运行前拒绝。先失败 2 项，相关 30 passed，全量 1607 passed/零跳过。生产工具协议/输入构造函数未改变。strong chat 传输适配暂留实验编排，不宣称公共 CLI 已有通用接管接口；Controller 某些历史 output_source 标签仍固定 RWKV，后续须补齐最终提交路径身份回归，不能仅凭入口字段宣布归属整链完成。

新 strong HTTP 2 次：31883 prompt / 3217 completion = 35100 provider token，其中 reasoning 2720；含首次 length 的实际消耗。精确 strong token ID 和权重 SHA 未由提供方披露，原样记录未知，不能拿本地 RWKV tokenizer 代理计数冒充。新 RWKV 生成 0；历史父任务和旧建议另列一次。没有合格任务成本或吞吐收益结论，费用/GPU峰值未测。两请求额度用尽，未扩预算。

后续方向：先补最终提交链路身份一致性及统一审核器对 vendor usage 的支持；保留本次失败与原评分。工程适配中的 reasoning/output 预算差异在下一轮运行前设计，不改本轮结果。强建议/接管仍按需，RWKV 默认执行，继续从真实交付失败集中归因，不逐阶段训练。

owner 原修改保留，本轮仅本地提交；无 GitHub、训练、新 datasets。原始 pytest 红灯日志尾空格保留。
