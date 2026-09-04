# B01-B14 运行后量化协议

脚本：`temp/analyze_g1j_zero_public_case_v1.py`  
SHA-256：`6943d3f4eef37d0e93eacf6ea6df84f11623203570f47f8e9ae82316500a0bb8`

身份更正记录：清单初稿在 2026-09-03 02:43:24+08:00 记录了分析器预定稿哈希；最终确定性分析器于 04:34:55+08:00 落盘，早于首个有效 case metrics（04:35:17+08:00）。全部正式 metrics 均由上述最终哈希版本生成，评分口径、case acceptance 和模型运行参数没有在运行后修改。

该脚本只处理已确认进入能力分母的有效运行；Strong Planner/服务 transport 失败先移动到 `infrastructure_invalid/`，不得由脚本误记为能力失败。

每个有效运行固定输出：

- terminal 状态、Finalizer/Final Auditor 到达情况和 transition budget；
- Strong/RWKV 请求数；
- Selector operation 分布、parent WKV 连续绑定率、GoalFrontierStateV1/action/audit 投影计数；
- Executor action/状态/协议拒绝；
- Step Auditor parse/verdict/拒绝；
- plan frontier、完成 step/stage；
- schema、role boundary、scope、hidden retry、premature completion 硬门禁；
- 唯一 `**Tool Call:**` JSON anchor 与旧 `Assistant: ```json` 计数；
- 隔离外部检查明细；
- case workspace 的全部常规文件 SHA-256 和符号链接目标；
- audit、ledger、trace、event log、timeline 的 SHA-256。

指标脚本不改变 runner 的 `full_task_success`。题目特有的语义硬门禁继续按用户冻结 acceptance 判定；例如 B04 必须使用结构化 JSON 工具，B11 必须通过注入恢复，B12 不得伪造完成，B13 还需单独核验 Planner 的两个并行调查步骤。
