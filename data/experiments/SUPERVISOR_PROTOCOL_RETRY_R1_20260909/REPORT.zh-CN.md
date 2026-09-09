# Supervisor 协议错误重试归属修复

Agent 级：当前版本首次 12 题观察在首题发现通用缺陷后中止，不能报告完整 12 题成绩。RP-API-01 自然结束为 Planner length 协议失败，0 动作；RP-API-02 被主动中断，0 动作；RP-MAINT-01 已启动但未取得结果。已记录部分 Strict 0、completed 0、mutation 0，不能把主动中断当作自然模型失败。原始数据保留在 `CURRENT_ROLE_CHAIN_OBSERVATION_R1_20260909`。

角色级：两个已导出案例 Selector、Executor 和两类 Auditor 均未到达，没有角色训练样本或 optimizer steps。RP-API-01 一个逻辑 Planner 请求实际发出了两次同体 HTTP 请求，两次均以 length 截断；原始输出出现超出需求范围的扩展与重复义务，截断计划保持拒绝。

根因在 `rwkv_lh/supervisor_openai.py` 的共享 `_request_json`：`SupervisorProtocolError` 与传输错误一样进入重试循环，尽管最终上报 `retryable=false`。这影响 Planner、Stage Checker 和共用传输入口的其他 Supervisor 调用；更换任务、增加工具目录或训练 Selector 均不能纠正这层控制行为。

修复后，HTTP 已成功但输出协议无效时立即回到原调用边界，保留原错误与原始响应，不再由网络层重新采样。真正网络故障继续服从既有传输策略；合法解析后的语义反馈修复仍由角色/Controller 的既有合同负责。未加入步骤/阶段数量上限、任务特判、外置 Head 或模型替代。

验证：21 个非自然结束/畸形边界及通用 HTTP-200 协议用例在修复前失败；修复后 Supervisor 定向 107 项通过，包括合法请求和网络故障重试。完整回归 **1074 passed、0 skipped，189.30 秒**；源码、日志 SHA 见 `MANIFEST.json`。中止观察的源码在停止前未改变，后续必须重新冻结整套 12 题；不重评分或拼接旧结果。

本修复消除的是错误的额外生成。Planner 本身的过度扩展、错误合同与未自然结束尚未证明解决；新运行会据实记录这些能力问题，缺少 Selector 边界不能包装为已收集到合格工具选择数据。
