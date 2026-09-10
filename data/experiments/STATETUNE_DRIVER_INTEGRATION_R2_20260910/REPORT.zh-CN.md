# STATETUNE_DRIVER_INTEGRATION_R2_20260910

最新完整 Agent 结果仍为 REALPROJECT R1：Strict 0/12、completed 0/12、mutation 0、动作 0；10 题旧 Planner 网关 HTTP 500，2 题旧 Native 生成 State 边界错误。UltraData R4 为 Strict 0/3、completed 0/3、mutation 0、动作 1。本轮是工程和训练后端验证，没有新增 Agent 成绩，没有正式角色数据冻结，没有实际角色训练，optimizer steps 为 0。单测中的微型优化器只验证机制，不是 RWKV 训练记录。

## 根因与整改

当前生产分支缺少正式数据消费及优化器入口；独立工作树留下的 driver WIP 没有集成，且训练源码校验仍使用另一种旧清单格式。逐文件审阅后引入唯一 data/training/CLI 入口，按当前 Selector v6 更新测试，来源及 SHA 保存在 IMPORT_TESTS / IMPORT_PRODUCTION。原工作树未改动。训练源码身份改为现有 uploaded_sources 的完整 PROJECT_SCHEMA 校验，不保留第二个旧 schema 入口。

freeze 从原始生产 trace 用同一抽取器复算完整候选审计，再原子发布 train 与固定 regression；训练只解析 train，regression 只验 SHA。训练前绑定模型、词表、协议、完整源码、数值后端、数据、初始化 State、指标、预算和 GPU；仅 time_state 参与 AdamW，按目标 token 加权积累，底模冻结，边界不截断。step intent/完成、未知进行中、中断和异常均持久化，导出 portable BF16 后使用同一服务 State loader 核验一次转置。

新增当前阶段 Selector 固定回归评测：从原 trace 的 source/run/boundary 重建唯一生产输入，调用 NativeNetworkSelectorClient 与 LongHorizonModel 的同一三菜单投票。dev/confirmation 身份固定，两臂只更换初始 State；错误和未运行保留原分母，不完整菜单组单独报告。逐菜单与聚合决策均检查 zero 已对而候选变错，不能用相等平均分掩盖退化；zero 达标且候选无改善时优先 zero。角色合格不等于 Agent 正式保留，结果明确 retained=false。当前语义评分只实现 Selector，后序角色不能套用其分类评分。

## 验证

先失败后通过的日志均保留：缺失 driver 导入失败、旧源码 schema 拒绝当前上传清单、固定评测缺失 13 failed，以及三菜单退化漏检 1 failed / 14 passed。最终专项 50 passed；完整 **1390 passed、0 skipped、225.13 秒**。完整日志 SHA `32eb6b0603d8406783ad5882ddb41175e336167c05ae1f9059ac0c0c3175578d`。

冻结上传项目 131 文件、engine 6393 文件；完整文件集、逐文件 SHA 与 manifest SHA 均由当前服务核验，服务器未执行 Git。当前唯一服务根为 `/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910`，两服务健康，采用新的独立 StateStore。项目 manifest SHA `d8952c5dab4248a93db339720f37dd4e7657fa175882e8fc23b5a1613b8241e6`，engine manifest SHA `4327197e8305f2a79ed750128df4ec689df16e2bd234b438d634bbd9d7fa395d`。

真实 2.9B 兼容首验在模型加载前拒绝旧依赖 SHA。完整核对发现 12 个系统共享库变化；dpkg 日志证明今天发生了 libc/OpenSSL/压缩库/SQLite 等发行版包升级，dpkg -V 对相关安装包全部通过。本任务没有修改系统包。旧结果、旧依赖及新登记全部保留；原数学扩展、模型、源码和数值阈值未改，重新完整执行全部检查。

复验 **passed**：zero/非对称非零 State × 1/17/128/16384 tokens 的 8 项全词表比较最大绝对差均为 0；1/17/128/16384 反向的全部 32 层 State 梯度有限且非零，底模及输入 State 不变，prompt 直接损失梯度为零，独立样本无 State 泄漏。峰值分配 30441612288 bytes，耗时 140.39 秒。runtime SHA `bc163c40955b028df5036b7b0b2fdd4e7dccd65ff56c3f5e30a8652439e350a9`，结果 SHA `a081809453d440c3fd6165ea19558a6fbe555301216a3e0438956cafb7d6510b`。数值验证不更新优化器。

## 下一步与边界

新官方 DeepSeek 采集 driver 已单独准备，保留旧 3+12 题身份、固定 family 切分、覆盖和 30 菜单/10 边界门槛。依据官方思考计划探针的 200.37 秒成本，新轮每题注册 1800 秒墙钟预算，不设阶段或步骤数量上限；新轮未开始生成时本报告封存。合格来源到位才冻结正式数据并按已有授权训练。不能把旧 source 版本的样本重新贴为当前版本，不能读取保留题集或合成角色数据。
