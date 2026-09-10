# NATIVE_BOUNDARY_REPAIR_R2_20260910

最新已封存 Agent 结果仍为 REALPROJECT R1：**Strict 0/12、completed 0/12、mutation 0、动作 0**，10 题强模型网关 HTTP 500，2 题 Native State 边界错误。本轮是工程与数值验证，没有新 Agent 成绩，optimizer steps **0**。

真实根因：服务把前端收到终止输出时捕获的 worker 当前 State 当成返回 token 对应的 State。两道失败题首次输出后的 processed_token_count + 1 比完整历史多 2，append 再传播偏差。R2 真实 GPU 再次观察到采样行分别为 2672 / 1849，而准确输出边界为 2670 / 1847；不能靠修改计数或放宽校验修复张量。

统一改造：采样 State 仅作私有工作区，候选由核验后的父 State 加实际返回 token 通过同一精确物化操作构造，导出、持久化后才发布。角色语义保持一次采样，缓存额外工作单独记录 token 数、prefill 请求数和耗时；首次两个真实输出为 105 / 96 tokens，缓存物化各一次，约 0.116 / 0.115 秒。原始返回内容和 receipt 重放不改写，物化失败不发布候选，也不重新采样结果未知的请求。读取与导出统一校验已有 token 证据。删除 Native worker 的重复 State profile loader 与参数解析，实际导入 Selector / 训练共用模块；加载规则和便携 State 转置只保留一处。缺少生成 finish_reason 不再伪造 stop。

Supervisor 保留解析前实际消费的 SSE 行，逐行 base64 和长度编码 SHA，绑定 call / run / attempt；包含未知事件、错误 JSON、无效 UTF-8 与未结束事件。此格式精确保留 iter_lines 返回字节，不宣称包含 HTTP 线缆原始换行。协议接纳标准未放宽；旧 UltraData R4 缺少原始 SSE 的原因仍未知。历史 500 没有生成计划证据，不归因于 Planner 的语义能力。

回归先失败后通过：生成边界初测 9 failed / 2 passed；Native profile 类型与显式请求检查拒绝旧实现；SSE 留证 4 failed；缺失/无效 finish_reason 3 failed。profile 第一版夹具缺少 max_num_reqs，修正夹具后的失败证明旧入口越过应有的显式 profile 检查，原始日志均保留。专项 108 passed，最终完整 **1341 passed、0 skipped、231.41 秒**。完整日志 SHA `fa8b3ab63808a3930247e81a851f757bb731029ceb6f3f3ec1d4cc326c7d1f73`。

真实 GPU 使用两道原始生产失败输入，未合成角色训练场景：停止符生成→提交→追加原拒绝反馈→再次生成→回滚，服务完全重启后导入并再次生成，完整输入 token 与输出 token 都核对。候选的 shift_state / wkv_state 与同父 State 精确 token 物化结果逐值相同，最大绝对差 **0**；重启前后贪心输出 token 相同，重复 request 返回同一 receipt。数值工程重放不能作为 Agent 成绩或角色标签。

部署上传 127 个项目文件和 6393 个 engine 文件的完整清单，启动前核验实际文件。项目 manifest SHA `bad4c15874aa4996aa61b0556de9a4e45b864cf97071d30dead5f838ef77bcd3`；engine manifest SHA `0861deb143507dbd77c123829be6502af9ca93f5f85c280443f08e946d9e3d96`。当前服务根为 `/home/chase/GitHub/RWKV-LH-native-boundary-r2-20260910`，使用新缓存目录，2.9B / 13.3B 权重路径未替换。旧部署 State 不跨身份导入，服务器未调用 Git。

剩余工作：owner 已选择 DeepSeek 官方服务并提供本地密钥，后续单独登记该路由的真实请求和新采集；接通正式 StateTune 数据消费、优化器登记和固定回归，满足当前 Selector 证据条件后训练。完整交接/Agent 闭环及训练尚未完成。本轮结果封存，不修改旧集合、不读取 Holdout。
