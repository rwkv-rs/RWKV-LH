# ULTRADATA_COLLECTION_R1_20260909

Owner 于 2026-09-09 提供完成的 UltraData 试点报告并要求“开始吧”，本轮恢复固定三题的真实生产采集。旧报告的暂停说明是历史状态。本轮沿用既有逐角色 StateTune 授权，当前目标为 Selector；正式优化器执行前另登记实际准入数据、固定回归、训练器和训练预算。

使用试点已经冻结的 `ULTRA-Code_00001`、`ULTRA-Code_00002`、`ULTRA-Code_00003`，由原 `run_case()` 执行当前 Stateful Goal Controller，保留全部原始失败。Planner / Stage Checker 为当前配置的 `gpt-5.6-sol`、SSE、8192 / 2400 tokens，未配置模型回退。Selector 为已部署的 2.9B，其余四个 RWKV 角色为当前 13.3B，五个角色均明确绑定独立 zero State。

每题从空 workspace 开始，Agent 自行创建程序和公开自检。原数据 ground_truth 仅由原隔离 verifier 消费；参考实现、语义 mutant 和私有验收反馈不进入模型输入。运行结果先报告 Strict、completed、mutation 和终止原因，再报告角色样本。

运行前固定参数与证据要求在 `REGISTRATION.json`：顺序执行，单题最多 200 个 Controller transition / 1200 秒，总计 3600 秒；保持既有传输重试与一次语义修复，不启用额外 pending 恢复或逐题重跑。步骤和阶段数量由 Planner 决定，没有另设数量限制。预算耗尽保留中断，不算完成。运行中不得修改生产源码、题目、判分或 coverage。

公开来源审查固定扫描登记的七个可见目录，仅比较公开题目文本；使用既有 UTF-8 byte 5-gram cosine、0.95 门槛，不读取 Holdout。429 对比较无越界，最大值约 0.175720；上游原始行及 revision 由试点清单固定，不能据此证明模型预训练时未见原题。

Selector scope 在运行前绑定到源协议：Python 程序创建及公开自检中的 py_root、mutate、execute、missing_target。九类 coverage 全部报告，这一范围不能代表 Web / 全栈。至少 30 条合格菜单行、10 个独立选择边界，并满足原有标签、完整 token、切分和相似度门后，才可进入本阶段正式训练登记；Agent 低分或后续角色未出现不构成训练禁令。

Project family 按原题身份固定，不按切分结果改名。既有 80/10/10 算法将三题分为 train / dev / train，目前没有 confirmation family。三题采集可以发现链路和角色问题，但不能单独提供完整固定回归；后续需同范围的独立真实任务来源补齐，不把训练行挪作回归。

临时运行与远程身份检查脚本位于根目录 `temp/`，其绝对路径和 SHA 登记于实验材料。服务器只核验上传源码 manifest、实际文件和模型 SHA，不使用 Git。原始外部题目和含其全文的生产工件仅留本地；提交保存清单、摘要和验证记录。
