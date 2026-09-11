# Selector 冻结源码重放与首训数据门 R3

轮次 A 的 Agent 结果：Strict 0/4、completed 0/4、mutation 0、动作 6；两题无进展、两题协议拒绝。 本轮成功命令是 NEW-DIAG-02 的三次 check_command：绑定 execute，实际和预期退出码均为 1，取得真实“1 failed, 3 passed”诊断；不代表测试修复成功。RWKV 仍重复动作，未完成项目。A 的预注册 execute 覆盖 KEEP 已达到；B 不启动，Executor 保持 1800。

162e60ee 和 c6b46d01 已按明确授权 push。A 任务与证据提交 67f1edd4；冻结入口补充修复提交 5edcccde，最终完整回归 1479 passed、0 failed、0 skipped。新修复仅在采集封存后实施，不改变 A 两臂/任务执行源码。

两名独立 AI reviewer 对 HISTORICAL14、COMMAND4、ROUND_A4 分别接受精确来源、Selector 角色和当前 wrapper SHA。旧来源 waiver 与 A 来源 waiver 分开记录不同 frozen SHA，不扩大旧十项历史运行语义例外，不改五角色协议或 State。接受文档及六份范围签名均由原提案精确 pin，draft 保留。

已用生产提取器真实重放 22 来源：162、48、46 条，合计 256 条；各组候选字节与先前已复核候选完全一致。组合重放期间共享工作区出现新的 harness.py / supervisor_openai.py 修改，源码 SHA 门正确拒绝，REAL_REPLAY.log 保留此失败。随后在逐文件核对等于已测试和双签的 5edcccde 隔离源码上，由新入口再次完整重放各组，比较完整 manifest 及全部原始成员字节，再按密封 selection 过滤并重新审计。最终候选 status=valid，24 条（19/3/2），execute=3，原五个评测 anchor 不变，候选字节与预注册政策应用结果一致。全部 24 条经生产 normalize_row 通过完整 token、BOS、模型、tokenizer、协议和 16384 上下文校验。源状态保持 zero。本结论仅绑定冻结 5edcccde，不覆盖并发的新修改；未回退或提交他人的工作区改动。

训练前置门未全部通过：预注册要求至少 30 条 verified menu rows 和 10 个独立选择边界；当前有效成员只有 24 条、9 边界（train 7）。本轮不得用过滤前 256 条冒充有效训练数量。未创建 data/datasets 版本，未执行 freeze、optimizer smoke 或训练，optimizer steps=0；没有把单测 freeze 成功冒充真实数据 freeze。

下一步是预注册额外独立生产采集，沿用固定数据政策、评测 anchor、角色覆盖及 1800 预算。有效成员至少还需净增 6 条、1 个边界；原始采集数量不保证去重后净增。补齐后重放、密封 selection、freeze，再按既有授权登记 smoke 和首训。首次 freeze 不虚构 prior；将来复用已冻结 regression 才要求原三重 pin。Agent 低分不是阻塞理由，真实数据门才是。

本次没有新的 Executor 预算轮、Planner B 或协议 C。部署仍是轮次 A 冻结的 c6b46d01 核心源码：服务器根 /home/chase/GitHub/RWKV-LH-execute-coverage-a-20260911；本地数据冻结工程不冒充已部署推理源码。未读取最终保留集。

精确证据见 FINAL_GATE.json、RAW_REPLAY_RESULTS.json、ROW_SELECTION.json、SELECTED_SOURCE_REGISTRATION.json、NORMALIZATION.json、FROZEN_REPLAY_IDENTITY.json、REAL_REPLAY.log 与 FROZEN_REAL_REPLAY.log。目录清单 EVIDENCE_SHA256.json 逐文件密封。
