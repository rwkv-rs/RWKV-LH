# 最新源码 Flash 官方采集 R3

Owner更新官方凭据并明确指定deepseek-flash，Planner和Stage Checker共同使用该模型。官方模型列表HTTP200确认可用，余额门通过。密钥仅写入canonical .env.local，未写入实验或提交。保持thinking enabled、reasoning_effort low、streaming和原预算。

Agent启动时实际完成0/117，首题E2E-B01已启动，尚无新Strict/completed/mutation分数。optimizer steps=0。源码与部署保持de029c88，213项本地源码身份、132项目文件及6393engine清单，1502项既有工程回归对应源码；RWKV模型和全zero State不变。新协议trace在本R3目录单独采集。

新密钥生效后R2旧deepseek-v4-pro曾启动首题，收到owner切换Flash指令后立即停止父调度器和该题进程组，OWNER_MODEL_SWITCH_INTERRUPTION.json保留事实，不计完整Agent评测，不覆盖旧trace。本R3重新从首题运行全部117题。此次同时相较历史R1改变了生产源码/协议和Strong模型，不能将成绩差异单独归因于信息流修复。

运行器具备启动前余额核验、题目返回402即暂停剩余队列。STARTED.json为真实启动收据，PROGRESS.json逐题更新。原任务、验收、顺序不变，无新训练/数据集版本、未读取Holdout。
