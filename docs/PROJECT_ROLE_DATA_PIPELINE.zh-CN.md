# 当前 Project StateTune 数据入口

Decision 与 Executor 使用独立数据、State 和固定回归。当前优先补 Decision 的方向选择、重复后的纠错和证据判断，Executor 保持 zero；可准入候选和正式训练行均为 **0**。这表示来源、独立审查、覆盖与隔离回归尚未齐备，不是角色工程入口缺失。最新 Agent 结果只见[当前交接](HANDOFF.zh-CN.md)。

## 当前合同与来源

生产、trace 提取和角色评测调用同一协议模块的 `build_input`：Planner v14、Decision v17、Executor v13；Ledger v10、prompt 布局 v7、输入传输 v2。运行时身份引用模块常量。原始目标与可选计划分离，直接原目标和计划任务使用同一 Executor 输入；检查编写与独立审查由 Planner 的 mode 区分。

完整用户请求、计划义务、工具 schema、已知事实与原始回执保留。模型可见 renderer 与宿主语义快照分开核验；相同文字的共享引用必须逐字可逆，不能用宿主 JSON 冒充实际模型输入。拒绝历史只从已确认回执和实际相邻输入重建，不是成功执行证据或纠正目标。

所有新 RWKV 模型运行必须开启约束，Agent 和正式角色评测共用当前生产 decoder。强 Planner 使用官方 DeepSeek beta strict tools；保存原始 SSE、tool_calls 和规范化记录，strict 请求不能作为服务必然强制 schema 的证明。旧协议、prompt 或不兼容 State 的来源不能重新渲染后进入当前训练。

角色来源必须是已登记的真实生产任务；登记原始 owner 请求、任务/仓库族、完整源码清单、模型与 State、协议、用途和预算。开发题、参考实现、接口探针与机制测试不转为角色训练来源。G1j 原生训练工具及完整输入/输出模板还需取得真实定义核对；本项目工具清单仅说明当前接口，不能当作官方训练规范。

## 提取与独立纠错

1. 使用 `project_source_snapshot.snapshot_project_source` 建立隔离源码，核验入口与逐文件 SHA，拒绝链接与私密文件。快照包含受控源码、通用命令和必要配置；本地测试存在时完整复制，公开仓库允许不含私有测试。不复制根目录 data、验收题或凭据，缺少夹具不能记为回归通过。
2. 结束运行后执行 `python -m scripts.run_project_role_data --source <execution目录> --registration <运行登记.json> --output <新目录>`。`project_training_sources` 重验账本事件链、当前 builder、完整 Native token/父 State 和生成前 workspace，封存来源清单。原始输出、checkpoint、lane、事件身份和拒绝反馈保留；候选默认 `training_eligible=false`。
3. `project_training_labels` 只接受实际边界上的明确纠正目标，重建完整审查包并核对独立 Strong 审查的原 wire、模型、预算、call ID、输入/目标摘要和完整返回。可开始调查与已完成验证分别判断，手写 accept 和作者声明不能替代独立证据。同一边界多次审查只算一个来源。
4. 读取统一使用 `ProjectLedger.read_snapshot`：先共享锁，再 immutable 只读 SQLite；活动写者、缺失锁、未 checkpoint WAL 均拒绝。`validate_snapshots` 在同一租约中内部重验完整事件链和每份快照，不接受调用者事件缓存；登记字节和 SHA 一起固定。

## Native 输入与 State 核验

`project_token_data.replay_native_rows` 必须逐字节核对服务返回的完整 prompt token、BOS 和原始生成 token。首次输入与后续 append 都使用当前生产 renderer；根据实际父 checkpoint 重建，不能按时间顺序把所有失败 child 串起来。Decision 持续 lane 仍逐项校验 boundary 身份；Executor 在兼容委派内持续，合同不兼容时新建 State。

当前输入快照、delta 与干净 anchor 同 checkpoint 绑定。新证据进入 anchor 后才能推进已读游标；原始采样 token 完整留证，State 消费序列仅排除合法末尾 EOS。下一 User 前按当前 framing 关闭 Assistant JSON 围栏。生产、客户端、服务与 trace 使用同一规则；本地重新分词、末次 delta 或不完整 replay 不能替代真实服务输入。

账本预留、实际 generation_started、提供方请求和返回分别核对。本地预留后未发送的失败没有模型输出，不能生成训练标签；已发送 UNKNOWN 保留，不重发。

## 冻结与训练准入

`project_statetune_data` 和 `project_executor_statetune_data` 提供两角色单行结构校验，核对当前输入、目标工具 schema、Native 模型身份和 target-only mask；单行合法不授予数据资格。

正式冻结由 `project_training_freeze` 经 `run_state_tune.py freeze`、`freeze_dataset` / `admit_dataset` 执行。重新核对真实来源、独立标签、任务族隔离、不同边界及函数覆盖。每角色固定回归仅存于 `data/statetune_regressions/<role>/`，首次有效来源才创建；后续只能加入 train 并绑定原 regression fingerprint，dev/confirmation 字节不变。

跨切分近重复使用固定 UTF-8 byte 5-gram 计数 cosine、0.95 阈值和整数比较。训练准入重验 train 的原来源与审查，评测文件核对 SHA，并通过固定索引的 SHA 化 gram 键/计数查泄漏。实际 optimizer 只接收重新取证的 train token 和目标 mask；重试、重复 epoch、换版本不扩大独立来源或抹去运行历史。

训练和正式 datasets 版本须在 owner 书面授权、预注册指标与资源预算内执行。每次登记模型/数据/训练器 SHA、初始化和输出 State、实际 optimizer steps、资源消耗、失败与验收结果；没有固定三轮上限。开发评测集仅供开发评测，最终 Holdout 不参与迭代。覆盖要求见[训练准入](PROJECT_STATETUNE_COVERAGE.zh-CN.md)。

## 固定角色评测与 Agent 保留门

`project_role_evaluation` 经 `run_state_tune.py evaluate` 使用固定 dev/confirmation 原来源和已审查标签，不重切分。plan/run v2 登记当前 decoder SHA、角色协议、回归 fingerprint、采样、上下文/输出/时间预算、失败上限与 Agent 保留规则；zero/candidate 两臂约束均开启，仅 State 不同。

完整原 prompt_token_ids 经 Native exact-token-input 进入 create/generate，不先解码再编码、不额外加 BOS。核对实际模型/State/profile、源码/权重清单、原 prefix、decoder、父 State、原始及消费 token 和 EOS。已知生成先落盘，再 rollback 未提交候选，携完整父 State 三字段身份 release 并核对真实回执；unknown rollback 保留父 State，不提交为 Agent 后续状态。

输出由生产 parser、normalizer 和角色 validator 校验。`reference_match` 只比较审查标签（Decision 忽略 reason，Executor 比较完整参数），不证明代码或目标语义。预算、传输失败和未运行样本保留原分母，对照不完整不晋级。角色指标合格仍须当前 Native Agent 与独立功能验收，Web 必须真实 Playwright；评测入口不直接决定保留 State。
