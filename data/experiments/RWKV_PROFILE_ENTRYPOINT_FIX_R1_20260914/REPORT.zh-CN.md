# R1：产品入口保留显式初始 State

本轮是工程整改，没有新的 Agent 通过率；统一训练候选仍 NO_KEEP，不改默认 State。

根因：批量、编码、只读 CLI 和 web_worker 的 direct_settings 各自硬编码 zero，覆盖已经从环境读取的 State ID/SHA。此前对照直接传 settings，所以不受影响；实际产品调用配置训练 State 会被覆盖。

四入口回归运行实际 main 的参数解析及 dispatch（仅替换推理执行），修复前显式配置4失败、默认zero4通过。现在共享 direct_agent_settings：保留完整显式身份及 delivery；仅无配置时设置zero，缺失配对或非法SHA拒绝。保留原base_url/model覆盖、native_required、full工具菜单和精确token记录。未修改协议/模型输出，也不自动选择或部署被拒绝候选。

部署显式配置使用 RWKV_STATE_PROFILE_ID、RWKV_STATE_PROFILE_SHA256、RWKV_STATE_PROFILE_DELIVERY，既有角色环境变量优先规则不变。服务端仍须实际注册匹配State并验证身份；本修复不绕过服务校验。连续State沿原观察child延续，独立任务从所选初始profile各建新根。

回归覆盖四入口默认/显式配置、缺失/非法身份、process_attested与模型身份保持；完整测试结果见FULL_TESTS.log。owner五处修改完整保留，无push，无服务器Git。

GPU0完整回归：1747 passed、0 skipped，329.02s；新增12项。
